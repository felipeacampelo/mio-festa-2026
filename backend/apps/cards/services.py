from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.tickets.models import Ticket

from .models import Card, CardTransaction

INITIAL_BALANCE_ADULT = Decimal("35.00")
INITIAL_BALANCE_CHILD = Decimal("0.00")


def initial_balance_for_ticket(ticket: Ticket) -> Decimal:
    return INITIAL_BALANCE_CHILD if ticket.is_child else INITIAL_BALANCE_ADULT


def normalize_uid(uid: str) -> str:
    return (uid or "").strip().upper()


def get_or_create_card(uid: str) -> Card:
    uid = normalize_uid(uid)
    card, _ = Card.objects.get_or_create(uid=uid)
    return card


def _result_for_status(card: Card) -> str:
    if card.status == Card.Status.BLOCKED:
        return "card_blocked"
    if card.status == Card.Status.RETURNED:
        return "card_returned"
    return "ok"


def _replay(idempotency_key: str | None):
    if not idempotency_key:
        return None
    return CardTransaction.objects.filter(idempotency_key=idempotency_key).select_related("card").first()


def link_card(uid: str, ticket_id: int):
    uid = normalize_uid(uid)
    with transaction.atomic():
        try:
            card = Card.objects.select_for_update().get(uid=uid)
        except Card.DoesNotExist:
            return "card_not_found", None

        if card.is_linked:
            return "already_linked", card

        try:
            ticket = Ticket.objects.select_related("order").get(id=ticket_id)
        except Ticket.DoesNotExist:
            return "ticket_not_found", card

        if Card.objects.filter(ticket=ticket).exclude(pk=card.pk).exists():
            return "ticket_already_has_card", card

        card.ticket = ticket
        card.balance = initial_balance_for_ticket(ticket)
        card.linked_at = timezone.now()
        card.save(update_fields=["ticket", "balance", "linked_at", "updated_at"])
        CardTransaction.objects.create(
            card=card,
            type=CardTransaction.Type.LINK,
            amount=card.balance,
            balance_after=card.balance,
            note=f"Vinculado ao ticket {ticket.ticket_code}.",
        )
    return "ok", card


def debit_card(uid: str, amount: Decimal, vendor, idempotency_key: str | None, note: str = ""):
    uid = normalize_uid(uid)
    if amount is None or amount <= 0:
        return "invalid_amount", None

    with transaction.atomic():
        existing = _replay(idempotency_key)
        if existing is not None:
            return _result_for_transaction(existing), existing.card

        try:
            card = Card.objects.select_for_update().get(uid=uid)
        except Card.DoesNotExist:
            return "card_not_found", None

        if card.status != Card.Status.ACTIVE:
            return _result_for_status(card), card
        if not card.is_linked:
            return "not_linked", card
        if card.balance < amount:
            CardTransaction.objects.create(
                card=card,
                type=CardTransaction.Type.DEBIT_FAILED,
                amount=amount,
                balance_after=card.balance,
                vendor=vendor,
                note=note,
                idempotency_key=idempotency_key,
            )
            return "insufficient_balance", card

        card.balance -= amount
        card.save(update_fields=["balance", "updated_at"])
        CardTransaction.objects.create(
            card=card,
            type=CardTransaction.Type.DEBIT,
            amount=amount,
            balance_after=card.balance,
            vendor=vendor,
            note=note,
            idempotency_key=idempotency_key,
        )
    return "ok", card


def credit_card(uid: str, amount: Decimal, vendor, idempotency_key: str | None, note: str = ""):
    uid = normalize_uid(uid)
    if amount is None or amount <= 0:
        return "invalid_amount", None

    with transaction.atomic():
        existing = _replay(idempotency_key)
        if existing is not None:
            return _result_for_transaction(existing), existing.card

        try:
            card = Card.objects.select_for_update().get(uid=uid)
        except Card.DoesNotExist:
            return "card_not_found", None

        if card.status != Card.Status.ACTIVE:
            return _result_for_status(card), card
        if not card.is_linked:
            return "not_linked", card

        card.balance += amount
        card.save(update_fields=["balance", "updated_at"])
        CardTransaction.objects.create(
            card=card,
            type=CardTransaction.Type.CREDIT,
            amount=amount,
            balance_after=card.balance,
            vendor=vendor,
            note=note,
            idempotency_key=idempotency_key,
        )
    return "ok", card


def _result_for_transaction(txn: CardTransaction) -> str:
    if txn.type == CardTransaction.Type.DEBIT_FAILED:
        return "insufficient_balance"
    return "ok"


def block_card(card: Card, note: str = ""):
    card.status = Card.Status.BLOCKED
    card.save(update_fields=["status", "updated_at"])
    CardTransaction.objects.create(
        card=card, type=CardTransaction.Type.BLOCK, balance_after=card.balance, note=note
    )
    return card


def unblock_card(card: Card, note: str = ""):
    card.status = Card.Status.ACTIVE
    card.save(update_fields=["status", "updated_at"])
    CardTransaction.objects.create(
        card=card, type=CardTransaction.Type.UNBLOCK, balance_after=card.balance, note=note
    )
    return card


def return_card(card: Card, note: str = ""):
    card.status = Card.Status.RETURNED
    card.save(update_fields=["status", "updated_at"])
    CardTransaction.objects.create(
        card=card, type=CardTransaction.Type.RETURN, balance_after=card.balance, note=note
    )
    return card
