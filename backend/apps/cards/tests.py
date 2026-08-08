import threading
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import Card, CardTransaction, CardTransactionItem, Product, Vendor
from apps.events.models import EventSettings
from apps.orders.models import Order
from apps.tickets.models import Ticket


def make_order_and_ticket(
    *,
    is_child=False,
    participant_name="Joao",
    participant_document="",
    status=Ticket.Status.ACTIVE,
    order_created_at=None,
):
    order = Order.objects.create(
        buyer_name="Maria",
        buyer_email="maria@example.com",
        buyer_document="12345678909",
        quantity=1,
        unit_price=Decimal("25.00"),
        total_amount=Decimal("25.00"),
        accepted_no_refund=True,
        payment_method=Order.PaymentMethod.PIX,
        status=Order.Status.PAID,
    )
    if order_created_at is not None:
        # created_at usa auto_now_add, entao so da pra ajustar via update().
        Order.objects.filter(pk=order.pk).update(created_at=order_created_at)
        order.refresh_from_db()
    ticket = Ticket.objects.create(
        order=order,
        participant_name=participant_name,
        participant_document=participant_document,
        is_child=is_child,
        status=status,
    )
    return order, ticket


def make_vendor(username, role, is_active=True):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="senha123", is_staff=False)
    return Vendor.objects.create(user=user, role=role, display_name=username, is_active=is_active)


def make_product(vendor, name="Agua", price=Decimal("5.00"), is_active=True):
    return Product.objects.create(vendor=vendor, name=name, price=price, is_active=is_active)


class CardsApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = make_vendor("vendedor1", Vendor.Role.SELLER)
        self.recharge = make_vendor("caixa1", Vendor.Role.RECHARGE)
        self.checkin = make_vendor("checkin1", Vendor.Role.CHECKIN)
        event = EventSettings.get_solo()
        event.event_date = timezone.now() + timedelta(days=10)
        event.save()

    def login(self, username):
        response = self.client.post(
            "/api/cards/login/", {"username": username, "password": "senha123"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return token


class VendorLoginTests(CardsApiTestCase):
    def test_login_success_returns_role(self):
        response = self.client.post(
            "/api/cards/login/", {"username": "vendedor1", "password": "senha123"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["vendor"]["role"], "seller")

    def test_login_wrong_password_rejected(self):
        response = self.client.post(
            "/api/cards/login/", {"username": "vendedor1", "password": "errada"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_login_inactive_vendor_rejected(self):
        make_vendor("inativo", Vendor.Role.SELLER, is_active=False)
        response = self.client.post(
            "/api/cards/login/", {"username": "inativo", "password": "senha123"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_admin_user_cannot_login_as_vendor(self):
        User = get_user_model()
        User.objects.create_user(username="staffer", password="senha123", is_staff=True)
        response = self.client.post(
            "/api/cards/login/", {"username": "staffer", "password": "senha123"}, format="json"
        )
        self.assertEqual(response.status_code, 401)


class CardLinkingTests(CardsApiTestCase):
    def test_get_unknown_uid_auto_creates_unlinked_card(self):
        self.login("vendedor1")
        response = self.client.get("/api/cards/AABBCC/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "active")
        self.assertIsNone(response.data["participant_name"])
        self.assertTrue(Card.objects.filter(uid="AABBCC").exists())

    def test_uid_is_normalized_to_uppercase(self):
        self.login("vendedor1")
        self.client.get("/api/cards/aabbcc/")
        self.assertTrue(Card.objects.filter(uid="AABBCC").exists())
        self.assertFalse(Card.objects.filter(uid="aabbcc").exists())

    def test_search_tickets_by_partial_name(self):
        _, ticket = make_order_and_ticket(participant_name="Joao Pereira", participant_document="11122233344")
        self.login("checkin1")
        response = self.client.get("/api/cards/search-tickets/?q=Joao")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], ticket.id)

    def test_search_tickets_by_cpf_digits(self):
        _, ticket = make_order_and_ticket(participant_name="Joao Pereira", participant_document="11122233344")
        self.login("checkin1")
        response = self.client.get("/api/cards/search-tickets/?q=111.222.333-44")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], ticket.id)

    def test_seller_cannot_search_tickets(self):
        make_order_and_ticket(participant_name="Joao Pereira")
        self.login("vendedor1")
        response = self.client.get("/api/cards/search-tickets/?q=Joao")
        self.assertEqual(response.status_code, 403)

    def test_link_sets_initial_balance_for_adult(self):
        _, ticket = make_order_and_ticket(is_child=False)
        self.login("checkin1")
        self.client.get("/api/cards/UID1/")
        response = self.client.post("/api/cards/UID1/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"], "ok")
        card = Card.objects.get(uid="UID1")
        self.assertEqual(card.balance, Decimal("35.00"))
        self.assertTrue(CardTransaction.objects.filter(card=card, type=CardTransaction.Type.LINK).exists())

    def test_link_sets_zero_balance_for_adult_purchased_on_event_day(self):
        event = EventSettings.get_solo()
        _, ticket = make_order_and_ticket(is_child=False, order_created_at=event.event_date)
        self.login("checkin1")
        self.client.get("/api/cards/UID1B/")
        response = self.client.post("/api/cards/UID1B/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.data["result"], "ok")
        card = Card.objects.get(uid="UID1B")
        self.assertEqual(card.balance, Decimal("0.00"))
        txn = CardTransaction.objects.filter(card=card, type=CardTransaction.Type.LINK).first()
        self.assertIn("dia do evento", txn.note)

    def test_link_keeps_35_for_adult_purchased_days_before_event(self):
        event = EventSettings.get_solo()
        _, ticket = make_order_and_ticket(
            is_child=False, order_created_at=event.event_date - timedelta(days=5)
        )
        self.login("checkin1")
        self.client.get("/api/cards/UID1C/")
        response = self.client.post("/api/cards/UID1C/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.data["result"], "ok")
        card = Card.objects.get(uid="UID1C")
        self.assertEqual(card.balance, Decimal("35.00"))

    def test_search_flags_tickets_purchased_on_event_day(self):
        event = EventSettings.get_solo()
        make_order_and_ticket(participant_name="Compra Antecipada")
        make_order_and_ticket(participant_name="Compra No Dia", order_created_at=event.event_date)
        self.login("checkin1")
        response = self.client.get("/api/cards/search-tickets/?q=Compra")
        self.assertEqual(response.status_code, 200)
        by_name = {r["participant_name"]: r["purchased_on_event_day"] for r in response.data}
        self.assertFalse(by_name["Compra Antecipada"])
        self.assertTrue(by_name["Compra No Dia"])

    def test_link_sets_zero_balance_for_child(self):
        _, ticket = make_order_and_ticket(is_child=True, participant_document="11122233344")
        self.login("checkin1")
        self.client.get("/api/cards/UID2/")
        response = self.client.post("/api/cards/UID2/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.status_code, 200)
        card = Card.objects.get(uid="UID2")
        self.assertEqual(card.balance, Decimal("0.00"))

    def test_relinking_already_linked_card_is_rejected(self):
        _, ticket = make_order_and_ticket()
        _, ticket2 = make_order_and_ticket(participant_name="Outra Pessoa")
        self.login("checkin1")
        self.client.get("/api/cards/UID3/")
        self.client.post("/api/cards/UID3/link/", {"ticket_id": ticket.id}, format="json")
        response = self.client.post("/api/cards/UID3/link/", {"ticket_id": ticket2.id}, format="json")
        self.assertEqual(response.data["result"], "already_linked")
        card = Card.objects.get(uid="UID3")
        self.assertEqual(card.ticket_id, ticket.id)

    def test_linking_ticket_that_already_has_a_card_is_rejected(self):
        _, ticket = make_order_and_ticket()
        self.login("checkin1")
        self.client.get("/api/cards/UID4/")
        self.client.post("/api/cards/UID4/link/", {"ticket_id": ticket.id}, format="json")
        self.client.get("/api/cards/UID5/")
        response = self.client.post("/api/cards/UID5/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.data["result"], "ticket_already_has_card")

    def test_linking_nonexistent_ticket_returns_error(self):
        self.login("checkin1")
        self.client.get("/api/cards/UID6/")
        response = self.client.post("/api/cards/UID6/link/", {"ticket_id": 999999}, format="json")
        self.assertEqual(response.data["result"], "ticket_not_found")

    def test_linking_pending_ticket_is_rejected(self):
        _, ticket = make_order_and_ticket(status=Ticket.Status.PENDING)
        self.login("checkin1")
        self.client.get("/api/cards/UID6B/")
        response = self.client.post("/api/cards/UID6B/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.data["result"], "ticket_not_eligible")
        self.assertFalse(Card.objects.get(uid="UID6B").is_linked)

    def test_linking_cancelled_ticket_is_rejected(self):
        _, ticket = make_order_and_ticket(status=Ticket.Status.CANCELLED)
        self.login("checkin1")
        self.client.get("/api/cards/UID6C/")
        response = self.client.post("/api/cards/UID6C/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.data["result"], "ticket_not_eligible")

    def test_seller_cannot_link_cards(self):
        _, ticket = make_order_and_ticket()
        self.login("vendedor1")
        self.client.get("/api/cards/UID7/")
        response = self.client.post("/api/cards/UID7/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_recharge_cannot_link_cards(self):
        _, ticket = make_order_and_ticket()
        self.login("caixa1")
        self.client.get("/api/cards/UID8/")
        response = self.client.post("/api/cards/UID8/link/", {"ticket_id": ticket.id}, format="json")
        self.assertEqual(response.status_code, 403)


class CardDebitTests(CardsApiTestCase):
    def _linked_card(self, uid="DEB1", balance=Decimal("35.00")):
        _, ticket = make_order_and_ticket()
        card = Card.objects.create(uid=uid, ticket=ticket, balance=balance)
        return card

    def test_debit_success_decrements_balance(self):
        self._linked_card(balance=Decimal("35.00"))
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-1"}, format="json"
        )
        self.assertEqual(response.data["result"], "ok")
        self.assertEqual(Decimal(response.data["card"]["balance"]), Decimal("25.00"))
        txn = CardTransaction.objects.get(idempotency_key="key-1")
        self.assertEqual(txn.type, CardTransaction.Type.DEBIT)
        self.assertEqual(txn.vendor, self.seller)

    def test_debit_insufficient_balance_is_blocked(self):
        self._linked_card(balance=Decimal("5.00"))
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-2"}, format="json"
        )
        self.assertEqual(response.data["result"], "insufficient_balance")
        card = Card.objects.get(uid="DEB1")
        self.assertEqual(card.balance, Decimal("5.00"))
        self.assertTrue(
            CardTransaction.objects.filter(card=card, type=CardTransaction.Type.DEBIT_FAILED).exists()
        )

    def test_debit_on_blocked_card_rejected(self):
        card = self._linked_card()
        card.status = Card.Status.BLOCKED
        card.save(update_fields=["status"])
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-3"}, format="json"
        )
        self.assertEqual(response.data["result"], "card_blocked")
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("35.00"))

    def test_debit_on_returned_card_rejected(self):
        card = self._linked_card()
        card.status = Card.Status.RETURNED
        card.save(update_fields=["status"])
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-4"}, format="json"
        )
        self.assertEqual(response.data["result"], "card_returned")

    def test_debit_on_unlinked_card_rejected(self):
        Card.objects.create(uid="UNLINKED")
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/UNLINKED/debit/", {"amount": "10.00", "idempotency_key": "key-5"}, format="json"
        )
        self.assertEqual(response.data["result"], "not_linked")

    def test_debit_non_positive_amount_rejected(self):
        self._linked_card()
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "0", "idempotency_key": "key-6"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_debit_unknown_card_returns_not_found_result(self):
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/GHOST/debit/", {"amount": "10.00", "idempotency_key": "key-7"}, format="json"
        )
        self.assertEqual(response.data["result"], "card_not_found")

    def test_idempotency_key_replay_does_not_double_charge(self):
        self._linked_card(balance=Decimal("35.00"))
        self.login("vendedor1")
        payload = {"amount": "10.00", "idempotency_key": "same-key"}
        first = self.client.post("/api/cards/DEB1/debit/", payload, format="json")
        second = self.client.post("/api/cards/DEB1/debit/", payload, format="json")
        self.assertEqual(first.data["result"], "ok")
        self.assertEqual(second.data["result"], "ok")
        card = Card.objects.get(uid="DEB1")
        self.assertEqual(card.balance, Decimal("25.00"))
        self.assertEqual(CardTransaction.objects.filter(idempotency_key="same-key").count(), 1)

    def test_recharge_vendor_cannot_debit(self):
        self._linked_card()
        self.login("caixa1")
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-8"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_debit_rejected(self):
        self._linked_card()
        response = self.client.post(
            "/api/cards/DEB1/debit/", {"amount": "10.00", "idempotency_key": "key-9"}, format="json"
        )
        self.assertEqual(response.status_code, 401)


class CardCreditTests(CardsApiTestCase):
    def _linked_card(self, uid="CRE1", balance=Decimal("0.00")):
        _, ticket = make_order_and_ticket()
        return Card.objects.create(uid=uid, ticket=ticket, balance=balance)

    def test_credit_success_increments_balance(self):
        self._linked_card()
        self.login("caixa1")
        response = self.client.post(
            "/api/cards/CRE1/credit/", {"amount": "20.00", "idempotency_key": "c-1"}, format="json"
        )
        self.assertEqual(response.data["result"], "ok")
        card = Card.objects.get(uid="CRE1")
        self.assertEqual(card.balance, Decimal("20.00"))
        txn = CardTransaction.objects.get(idempotency_key="c-1")
        self.assertEqual(txn.vendor, self.recharge)

    def test_seller_vendor_cannot_credit(self):
        self._linked_card()
        self.login("vendedor1")
        response = self.client.post(
            "/api/cards/CRE1/credit/", {"amount": "20.00", "idempotency_key": "c-2"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_credit_idempotency_replay_single_effect(self):
        self._linked_card()
        self.login("caixa1")
        payload = {"amount": "20.00", "idempotency_key": "c-3"}
        self.client.post("/api/cards/CRE1/credit/", payload, format="json")
        self.client.post("/api/cards/CRE1/credit/", payload, format="json")
        card = Card.objects.get(uid="CRE1")
        self.assertEqual(card.balance, Decimal("20.00"))

    def test_credit_on_blocked_card_rejected(self):
        card = self._linked_card()
        card.status = Card.Status.BLOCKED
        card.save(update_fields=["status"])
        self.login("caixa1")
        response = self.client.post(
            "/api/cards/CRE1/credit/", {"amount": "20.00", "idempotency_key": "c-4"}, format="json"
        )
        self.assertEqual(response.data["result"], "card_blocked")
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("0.00"))


class AdminCardReportingTests(CardsApiTestCase):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.admin_user = User.objects.create_user(username="admin1", password="senha123", is_staff=True)

    def admin_login(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "admin1", "password": "senha123"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")

    def test_reconciliation_totals_match_transactions(self):
        _, ticket1 = make_order_and_ticket(participant_name="A")
        _, ticket2 = make_order_and_ticket(participant_name="B")
        card1 = Card.objects.create(uid="R1", ticket=ticket1, balance=Decimal("10.00"))
        card2 = Card.objects.create(uid="R2", ticket=ticket2, balance=Decimal("5.00"))
        CardTransaction.objects.create(
            card=card1, type=CardTransaction.Type.CREDIT, amount=Decimal("10.00"),
            balance_after=Decimal("10.00"), vendor=self.recharge,
        )
        CardTransaction.objects.create(
            card=card2, type=CardTransaction.Type.CREDIT, amount=Decimal("5.00"),
            balance_after=Decimal("5.00"), vendor=self.recharge,
        )
        self.admin_login()
        response = self.client.get("/api/admin/cards/reconciliation/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["recharge_by_vendor"][0]["total"]), Decimal("15.00"))
        self.assertEqual(Decimal(response.data["outstanding_balance"]), Decimal("15.00"))

    def test_returned_card_excluded_from_outstanding_balance(self):
        _, ticket = make_order_and_ticket()
        Card.objects.create(uid="RET1", ticket=ticket, balance=Decimal("20.00"), status=Card.Status.RETURNED)
        self.admin_login()
        response = self.client.get("/api/admin/cards/reconciliation/")
        self.assertEqual(Decimal(response.data["outstanding_balance"]), Decimal("0"))

    def test_vendor_token_cannot_access_admin_reconciliation(self):
        self.login("vendedor1")
        response = self.client.get("/api/admin/cards/reconciliation/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_block_and_unblock_card(self):
        _, ticket = make_order_and_ticket()
        Card.objects.create(uid="BLK1", ticket=ticket, balance=Decimal("10.00"))
        self.admin_login()
        response = self.client.post("/api/admin/cards/BLK1/block/", {}, format="json")
        self.assertEqual(response.data["status"], "blocked")
        response = self.client.post("/api/admin/cards/BLK1/unblock/", {}, format="json")
        self.assertEqual(response.data["status"], "active")

    def test_reconciliation_sold_by_vendor_matches_debit_sum_and_excludes_failed(self):
        _, ticket1 = make_order_and_ticket(participant_name="A")
        _, ticket2 = make_order_and_ticket(participant_name="B")
        card1 = Card.objects.create(uid="S1", ticket=ticket1, balance=Decimal("50.00"))
        card2 = Card.objects.create(uid="S2", ticket=ticket2, balance=Decimal("2.00"))
        CardTransaction.objects.create(
            card=card1, type=CardTransaction.Type.DEBIT, amount=Decimal("20.00"),
            balance_after=Decimal("30.00"), vendor=self.seller,
        )
        CardTransaction.objects.create(
            card=card2, type=CardTransaction.Type.DEBIT, amount=Decimal("2.00"),
            balance_after=Decimal("0.00"), vendor=self.seller,
        )
        # Falha de saldo insuficiente nao deve entrar na soma.
        CardTransaction.objects.create(
            card=card2, type=CardTransaction.Type.DEBIT_FAILED, amount=Decimal("100.00"),
            balance_after=Decimal("0.00"), vendor=self.seller,
        )
        self.admin_login()
        response = self.client.get("/api/admin/cards/reconciliation/")
        self.assertEqual(Decimal(response.data["sold_by_vendor"][0]["total"]), Decimal("22.00"))

    def test_admin_can_list_all_vendors_across_roles(self):
        self.admin_login()
        response = self.client.get("/api/admin/cards/vendors/")
        roles = {v["role"] for v in response.data}
        self.assertEqual(roles, {"seller", "recharge", "checkin"})

    def test_admin_can_impersonate_vendor_and_use_returned_token(self):
        self.admin_login()
        response = self.client.post(f"/api/admin/cards/vendors/{self.seller.id}/impersonate/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["vendor"]["role"], "seller")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        me = self.client.get("/api/cards/me/")
        self.assertEqual(me.data["id"], self.seller.id)

    def test_cannot_impersonate_inactive_vendor(self):
        inactive = make_vendor("inativo2", Vendor.Role.SELLER, is_active=False)
        self.admin_login()
        response = self.client.post(f"/api/admin/cards/vendors/{inactive.id}/impersonate/")
        self.assertEqual(response.status_code, 400)

    def test_vendor_token_cannot_impersonate(self):
        self.login("vendedor1")
        response = self.client.post(f"/api/admin/cards/vendors/{self.recharge.id}/impersonate/")
        self.assertEqual(response.status_code, 403)


class ProductAdminTests(CardsApiTestCase):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.admin_user = User.objects.create_user(username="admin1", password="senha123", is_staff=True)

    def admin_login(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "admin1", "password": "senha123"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")

    def test_admin_can_create_product(self):
        self.admin_login()
        response = self.client.post(
            "/api/admin/products/",
            {"name": "Refrigerante", "price": "6.00", "vendor": self.seller.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Product.objects.filter(name="Refrigerante", price=Decimal("6.00")).exists())

    def test_admin_cannot_create_product_for_non_seller_vendor(self):
        self.admin_login()
        response = self.client.post(
            "/api/admin/products/",
            {"name": "Refrigerante", "price": "6.00", "vendor": self.recharge.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_update_product_price(self):
        product = make_product(self.seller, name="Agua", price=Decimal("5.00"))
        self.admin_login()
        response = self.client.patch(f"/api/admin/products/{product.id}/", {"price": "7.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("7.00"))

    def test_admin_can_deactivate_product(self):
        product = make_product(self.seller)
        self.admin_login()
        response = self.client.patch(f"/api/admin/products/{product.id}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertFalse(product.is_active)

    def test_non_admin_cannot_create_product(self):
        self.login("vendedor1")
        response = self.client.post(
            "/api/admin/products/", {"name": "Refrigerante", "price": "6.00"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_unused_product_succeeds(self):
        product = make_product(self.seller)
        self.admin_login()
        response = self.client.delete(f"/api/admin/products/{product.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(id=product.id).exists())

    def test_delete_used_product_is_rejected(self):
        product = make_product(self.seller)
        _, ticket = make_order_and_ticket()
        card = Card.objects.create(uid="USEDP1", ticket=ticket, balance=Decimal("50.00"))
        txn = CardTransaction.objects.create(
            card=card, type=CardTransaction.Type.DEBIT, amount=Decimal("5.00"),
            balance_after=Decimal("45.00"), vendor=self.seller,
        )
        CardTransactionItem.objects.create(
            transaction=txn, product=product, product_name=product.name,
            unit_price=product.price, quantity=1,
        )
        self.admin_login()
        response = self.client.delete(f"/api/admin/products/{product.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Product.objects.filter(id=product.id).exists())

    def test_admin_can_list_sellers_for_product_form(self):
        self.admin_login()
        response = self.client.get("/api/admin/cards/sellers/")
        self.assertEqual(response.status_code, 200)
        names = [v["display_name"] for v in response.data]
        self.assertIn("vendedor1", names)
        self.assertNotIn("caixa1", names)
        self.assertNotIn("checkin1", names)


class ProductListTests(CardsApiTestCase):
    def test_seller_lists_only_active_products(self):
        make_product(self.seller, name="Ativo", is_active=True)
        make_product(self.seller, name="Inativo", is_active=False)
        self.login("vendedor1")
        response = self.client.get("/api/cards/products/")
        self.assertEqual(response.status_code, 200)
        names = [p["name"] for p in response.data]
        self.assertIn("Ativo", names)
        self.assertNotIn("Inativo", names)

    def test_products_endpoint_requires_vendor_auth(self):
        response = self.client.get("/api/cards/products/")
        self.assertEqual(response.status_code, 401)

    def test_seller_does_not_see_other_sellers_products(self):
        other_seller = make_vendor("vendedor2", Vendor.Role.SELLER)
        make_product(self.seller, name="Do Vendedor 1")
        make_product(other_seller, name="Do Vendedor 2")
        self.login("vendedor1")
        response = self.client.get("/api/cards/products/")
        names = [p["name"] for p in response.data]
        self.assertIn("Do Vendedor 1", names)
        self.assertNotIn("Do Vendedor 2", names)


class CartDebitTests(CardsApiTestCase):
    def _linked_card(self, uid="CART1", balance=Decimal("100.00")):
        _, ticket = make_order_and_ticket()
        return Card.objects.create(uid=uid, ticket=ticket, balance=balance)

    def test_cart_debit_computes_total_from_db_prices(self):
        card = self._linked_card()
        agua = make_product(self.seller, name="Agua", price=Decimal("5.00"))
        cerveja = make_product(self.seller, name="Cerveja", price=Decimal("12.00"))
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {
                "items": [
                    {"product_id": agua.id, "quantity": 2},
                    {"product_id": cerveja.id, "quantity": 1},
                ],
                "idempotency_key": "cart-1",
            },
            format="json",
        )
        self.assertEqual(response.data["result"], "ok")
        # 2*5 + 1*12 = 22, ignorando qualquer preco que o cliente pudesse mandar.
        self.assertEqual(Decimal(response.data["card"]["balance"]), Decimal("78.00"))
        txn = CardTransaction.objects.get(idempotency_key="cart-1")
        self.assertEqual(txn.amount, Decimal("22.00"))
        self.assertEqual(txn.items.count(), 2)

    def test_cart_debit_ignores_client_supplied_price(self):
        card = self._linked_card()
        product = make_product(self.seller, name="Agua", price=Decimal("5.00"))
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {
                "items": [{"product_id": product.id, "quantity": 1, "price": "0.01", "unit_price": "0.01"}],
                "idempotency_key": "cart-2",
            },
            format="json",
        )
        self.assertEqual(response.data["result"], "ok")
        self.assertEqual(Decimal(response.data["card"]["balance"]), Decimal("95.00"))

    def test_cart_debit_creates_item_rows_with_snapshot(self):
        card = self._linked_card()
        product = make_product(self.seller, name="Espetinho", price=Decimal("15.00"))
        self.login("vendedor1")
        self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 3}], "idempotency_key": "cart-3"},
            format="json",
        )
        item = CardTransactionItem.objects.get(transaction__idempotency_key="cart-3")
        self.assertEqual(item.product_name, "Espetinho")
        self.assertEqual(item.unit_price, Decimal("15.00"))
        self.assertEqual(item.quantity, 3)

    def test_cart_debit_after_price_change_keeps_old_snapshot(self):
        card = self._linked_card()
        product = make_product(self.seller, name="Agua", price=Decimal("5.00"))
        self.login("vendedor1")
        self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 1}], "idempotency_key": "cart-4"},
            format="json",
        )
        product.price = Decimal("9.00")
        product.save()
        item = CardTransactionItem.objects.get(transaction__idempotency_key="cart-4")
        self.assertEqual(item.unit_price, Decimal("5.00"))

    def test_cart_debit_rejects_empty_items(self):
        card = self._linked_card()
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [], "idempotency_key": "cart-5"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cart_debit_rejects_zero_quantity(self):
        card = self._linked_card()
        product = make_product(self.seller)
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 0}], "idempotency_key": "cart-6"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cart_debit_rejects_inactive_product(self):
        card = self._linked_card()
        product = make_product(self.seller, is_active=False)
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 1}], "idempotency_key": "cart-7"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cart_debit_rejects_nonexistent_product(self):
        card = self._linked_card()
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": 999999, "quantity": 1}], "idempotency_key": "cart-8"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cart_debit_rejects_other_vendors_product(self):
        card = self._linked_card()
        other_seller = make_vendor("vendedor2", Vendor.Role.SELLER)
        product = make_product(other_seller, name="Do Vendedor 2", price=Decimal("10.00"))
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 1}], "idempotency_key": "cart-8b"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cart_debit_insufficient_balance_creates_no_items(self):
        card = self._linked_card(balance=Decimal("2.00"))
        product = make_product(self.seller, name="Espetinho", price=Decimal("15.00"))
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"items": [{"product_id": product.id, "quantity": 1}], "idempotency_key": "cart-9"},
            format="json",
        )
        self.assertEqual(response.data["result"], "insufficient_balance")
        self.assertEqual(CardTransactionItem.objects.count(), 0)
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("2.00"))

    def test_cart_debit_idempotency_replay_does_not_duplicate_items(self):
        card = self._linked_card()
        product = make_product(self.seller, name="Agua", price=Decimal("5.00"))
        self.login("vendedor1")
        payload = {"items": [{"product_id": product.id, "quantity": 2}], "idempotency_key": "cart-10"}
        self.client.post(f"/api/cards/{card.uid}/debit/", payload, format="json")
        self.client.post(f"/api/cards/{card.uid}/debit/", payload, format="json")
        card.refresh_from_db()
        self.assertEqual(card.balance, Decimal("90.00"))
        self.assertEqual(CardTransaction.objects.filter(idempotency_key="cart-10").count(), 1)
        self.assertEqual(CardTransactionItem.objects.filter(transaction__idempotency_key="cart-10").count(), 1)

    def test_manual_amount_debit_still_works_without_items(self):
        card = self._linked_card()
        self.login("vendedor1")
        response = self.client.post(
            f"/api/cards/{card.uid}/debit/",
            {"amount": "9.90", "idempotency_key": "cart-11"},
            format="json",
        )
        self.assertEqual(response.data["result"], "ok")
        self.assertEqual(Decimal(response.data["card"]["balance"]), Decimal("90.10"))
        self.assertNotIn("items", response.data)


class CardDebitConcurrencyTests(TransactionTestCase):
    """Uses TransactionTestCase (real commits, real locking) instead of TestCase
    (which wraps each test in a rolled-back transaction and would hide the
    select_for_update() row lock behaviour under threads).

    select_for_update() only takes a real row lock on Postgres. On sqlite
    (the default local/test DB here) concurrent writers hit sqlite's
    whole-database lock instead and raise "database is locked" - not a
    meaningful pass/fail signal for THIS test's purpose. Skip there instead
    of reporting a false negative; run against Postgres (set DATABASE_URL)
    to actually exercise the row-locking guarantee.
    """

    def setUp(self):
        if connections["default"].vendor != "postgresql":
            self.skipTest(
                "Concurrency/row-locking test requires Postgres (set DATABASE_URL) - "
                "sqlite does not enforce select_for_update() row locks."
            )
        User = get_user_model()
        user = User.objects.create_user(username="vendedor_conc", password="senha123")
        self.vendor = Vendor.objects.create(user=user, role=Vendor.Role.SELLER, display_name="V")
        order = Order.objects.create(
            buyer_name="Maria", buyer_email="maria@example.com", buyer_document="12345678909",
            quantity=1, unit_price=Decimal("25.00"), total_amount=Decimal("25.00"),
            accepted_no_refund=True, payment_method=Order.PaymentMethod.PIX, status=Order.Status.PAID,
        )
        ticket = Ticket.objects.create(order=order, participant_name="Joao", status=Ticket.Status.ACTIVE)
        self.card = Card.objects.create(uid="RACE1", ticket=ticket, balance=Decimal("10.00"))

    def test_two_concurrent_debits_only_one_succeeds(self):
        from apps.cards import services

        results = []

        def run(key):
            try:
                result, _ = services.debit_card("RACE1", Decimal("10.00"), self.vendor, key)
                results.append(result)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=run, args=("race-a",))
        t2 = threading.Thread(target=run, args=("race-b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.card.refresh_from_db()
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("insufficient_balance"), 1)
        self.assertEqual(self.card.balance, Decimal("0.00"))


class CardLinkConcurrencyTests(TransactionTestCase):
    """Two different physical cards racing to link the SAME ticket.

    select_for_update() in link_card() locks the CARD row being written, not
    the ticket - so this race isn't covered by that lock. The ticket-level
    OneToOneField uniqueness at the DB layer is the actual guard here; this
    test exists to prove the IntegrityError it raises is caught and turned
    into a typed "ticket_already_has_card" result instead of leaking as a 500.

    Same sqlite caveat as CardDebitConcurrencyTests: skip outside Postgres.
    """

    def setUp(self):
        if connections["default"].vendor != "postgresql":
            self.skipTest(
                "Concurrency test requires Postgres (set DATABASE_URL) - "
                "sqlite does not enforce select_for_update() row locks."
            )
        User = get_user_model()
        user = User.objects.create_user(username="checkin_conc", password="senha123")
        self.vendor = Vendor.objects.create(user=user, role=Vendor.Role.CHECKIN, display_name="C")
        order = Order.objects.create(
            buyer_name="Maria", buyer_email="maria@example.com", buyer_document="12345678909",
            quantity=1, unit_price=Decimal("25.00"), total_amount=Decimal("25.00"),
            accepted_no_refund=True, payment_method=Order.PaymentMethod.PIX, status=Order.Status.PAID,
        )
        self.ticket = Ticket.objects.create(order=order, participant_name="Joao", status=Ticket.Status.ACTIVE)
        self.card_a = Card.objects.create(uid="RACEA")
        self.card_b = Card.objects.create(uid="RACEB")

    def test_two_cards_racing_same_ticket_only_one_links(self):
        from apps.cards import services

        results = []

        def run(uid):
            try:
                result, _ = services.link_card(uid, self.ticket.id)
                results.append(result)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=run, args=("RACEA",))
        t2 = threading.Thread(target=run, args=("RACEB",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("ticket_already_has_card"), 1)
        self.assertEqual(Card.objects.filter(ticket=self.ticket).count(), 1)
