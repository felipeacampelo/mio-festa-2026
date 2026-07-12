import base64
from io import BytesIO

import qrcode
from django.conf import settings
from django.core import signing
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas

from .models import Ticket, TicketAuditLog


SIGNING_SALT = "festa-junina-ticket"

_PDF_NAVY = colors.HexColor("#1C1A3E")
_PDF_GOLD = colors.HexColor("#F5B83D")
_PDF_TEXT_WARM = colors.HexColor("#3A3660")
_PDF_TEXT_MUTED = colors.HexColor("#7A7898")
_PDF_TICKET_WIDTH = 190 * mm
_PDF_TICKET_HEIGHT = 95 * mm


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


def _draw_ticket_page(c: pdf_canvas.Canvas, ticket: Ticket, event) -> None:
    width, height = _PDF_TICKET_WIDTH, _PDF_TICKET_HEIGHT
    header_height = 22 * mm
    qr_size = 55 * mm
    text_x = 10 * mm

    c.setFillColor(_PDF_NAVY)
    c.rect(0, height - header_height, width, header_height, fill=1, stroke=0)
    c.setFillColor(_PDF_GOLD)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(text_x, height - 14 * mm, "MIÓ")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(text_x, height - 19 * mm, "FESTA DO MUNDO 2026  ·  INGRESSO")

    event_date = timezone.localtime(event.event_date).strftime("%d/%m/%Y às %H:%M")

    y = height - header_height - 12 * mm
    c.setFillColor(_PDF_TEXT_WARM)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(text_x, y, ticket.participant_name)
    y -= 9 * mm

    for label, value in (
        ("Evento", event.name),
        ("Data", event_date),
        ("Local", event.location),
        ("Código", str(ticket.ticket_code)),
    ):
        c.setFont("Helvetica", 8)
        c.setFillColor(_PDF_TEXT_MUTED)
        c.drawString(text_x, y, f"{label.upper()}")
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_PDF_TEXT_WARM)
        c.drawString(text_x, y - 4 * mm, value)
        y -= 11 * mm

    qr_image = qrcode.make(build_ticket_token(ticket), box_size=8, border=2)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_x = width - qr_size - 12 * mm
    qr_y = (height - header_height - qr_size) / 2 + 2 * mm
    c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size)

    c.setDash([2, 2])
    c.setStrokeColor(colors.HexColor("#D9D4C6"))
    divider_x = qr_x - 8 * mm
    c.line(divider_x, 4 * mm, divider_x, height - header_height - 4 * mm)
    c.setDash([])

    c.setFont("Helvetica", 6.5)
    c.setFillColor(_PDF_TEXT_MUTED)
    c.drawString(text_x, 6 * mm, "Apresente este QR Code na entrada. Uso individual e único.")


def build_tickets_pdf_bytes(tickets) -> bytes:
    from apps.events.models import EventSettings

    event = EventSettings.get_solo()
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(_PDF_TICKET_WIDTH, _PDF_TICKET_HEIGHT))
    for ticket in tickets:
        _draw_ticket_page(c, ticket, event)
        c.showPage()
    c.save()
    return buffer.getvalue()


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
