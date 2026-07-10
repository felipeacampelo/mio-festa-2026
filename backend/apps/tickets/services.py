import base64
from io import BytesIO

import qrcode
from django.conf import settings
from django.core import signing
from django.utils import timezone

from .models import Ticket, TicketAuditLog


SIGNING_SALT = "festa-junina-ticket"


def build_ticket_token(ticket: Ticket) -> str:
    return signing.dumps({"ticket_id": ticket.id, "code": str(ticket.ticket_code)}, salt=SIGNING_SALT)


def resolve_ticket_token(token: str) -> Ticket:
    payload = signing.loads(token, max_age=None, salt=SIGNING_SALT)
    return Ticket.objects.select_related("order", "checked_in_by", "superseded_by_ticket").get(
        id=payload["ticket_id"],
        ticket_code=payload["code"],
    )


def build_ticket_qr_data_url(ticket: Ticket) -> str:
    token = build_ticket_token(ticket)
    image = qrcode.make(token, box_size=8, border=4)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def append_audit(ticket: Ticket, action: str, note: str = "", actor=None) -> None:
    TicketAuditLog.objects.create(ticket=ticket, action=action, note=note, actor=actor)


def activate_ticket(ticket: Ticket) -> Ticket:
    ticket.status = Ticket.Status.ACTIVE
    ticket.save(update_fields=["status", "updated_at"])
    append_audit(ticket, TicketAuditLog.Action.ACTIVATED, note="Ticket ativado apos confirmacao do pagamento.")
    return ticket


def reissue_ticket(ticket: Ticket, *, participant_name: str, participant_email: str, actor, action: str) -> Ticket:
    replacement = Ticket.objects.create(
        order=ticket.order,
        participant_name=participant_name,
        participant_email=participant_email,
        status=Ticket.Status.ACTIVE,
    )
    ticket.status = Ticket.Status.REISSUED
    ticket.superseded_by_ticket = replacement
    ticket.save(update_fields=["status", "superseded_by_ticket", "updated_at"])
    append_audit(ticket, TicketAuditLog.Action.REISSUED, note=f"Substituido pelo ticket {replacement.ticket_code}.", actor=actor)
    append_audit(replacement, action, note=f"Gerado a partir do ticket {ticket.ticket_code}.", actor=actor)
    return replacement


def check_in_ticket(ticket: Ticket, actor):
    if ticket.status == Ticket.Status.USED:
        return "already_checked_in"
    if ticket.status != Ticket.Status.ACTIVE:
        return "blocked"
    ticket.status = Ticket.Status.USED
    ticket.checked_in_at = timezone.now()
    ticket.checked_in_by = actor
    ticket.save(update_fields=["status", "checked_in_at", "checked_in_by", "updated_at"])
    append_audit(ticket, TicketAuditLog.Action.CHECKED_IN, note="Entrada confirmada.", actor=actor)
    return "confirmed"
