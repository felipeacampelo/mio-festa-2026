import base64
from pathlib import Path
from typing import Iterable
import requests

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.tickets.services import build_tickets_pdf_bytes

NAVY = "#1C1A3E"
NAVY_LIGHT = "#2D2856"
GOLD = "#F5B83D"
CREAM = "#FFF1CC"
TEXT_MUTED = "#7A7898"
TEXT_WARM = "#3A3660"

_LOGO_PATH = Path(__file__).resolve().parent.parent / "core" / "assets" / "logo_mio_festa.png"
_LOGO_DATA_URL = "data:image/png;base64," + base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")


def _send_email(subject: str, html: str, recipients: Iterable[str], attachments=()) -> None:
    emails = [email for email in recipients if email]
    if not emails:
        return
    if settings.RESEND_API_KEY:
        payload = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": emails,
            "subject": subject,
            "html": html,
        }
        if attachments:
            payload["attachments"] = [
                {"filename": filename, "content": base64.b64encode(content).decode("ascii")}
                for filename, content, _mimetype in attachments
            ]
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        ).raise_for_status()
        return

    message = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, emails)
    message.attach_alternative(html, "text/html")
    for filename, content, mimetype in attachments:
        message.attach(filename, content, mimetype)
    message.send(fail_silently=False)


def _email_shell(title: str, body_html: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:{CREAM};font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background:{NAVY};border-radius:16px 16px 0 0;padding:24px 32px;text-align:center;">
        <img src="{_LOGO_DATA_URL}" alt="MIÓ Festa do Mundo 2026" width="220" style="width:220px;max-width:70%;display:block;margin:0 auto;" />
      </div>
      <div style="background:#ffffff;border-radius:0 0 16px 16px;padding:32px;box-shadow:0 4px 16px rgba(28,26,62,0.08);">
        <h1 style="font-size:21px;color:{NAVY_LIGHT};margin:0 0 20px;">{title}</h1>
        {body_html}
      </div>
      <p style="text-align:center;font-size:11px;color:#B8B4D0;margin-top:20px;">
        Igreja Batista Capital · e-mail automático, não responda
      </p>
    </div>
  </body>
</html>"""


def _event_details_html(order) -> str:
    event = order.event if hasattr(order, "event") else None
    if not event:
        from apps.events.models import EventSettings

        event = EventSettings.get_solo()
    event_date = timezone.localtime(event.event_date).strftime("%d/%m/%Y às %H:%M")
    rows = [
        ("Evento", event.name),
        ("Data", event_date),
        ("Local", event.location),
        ("Pedido", order.order_code),
    ]
    row_count = len(rows)
    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:{'16px' if i == 0 else '6px'} 8px {'16px' if i == row_count - 1 else '6px'} 20px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:{TEXT_MUTED};white-space:nowrap;">{label}</td>
          <td style="padding:{'16px' if i == 0 else '6px'} 20px {'16px' if i == row_count - 1 else '6px'} 16px;font-size:14px;font-weight:600;color:{TEXT_WARM};">{value}</td>
        </tr>"""
        for i, (label, value) in enumerate(rows)
    )
    return f"""
    <table role="presentation" width="100%" style="background:{CREAM};border-radius:12px;margin-bottom:20px;border-collapse:collapse;">
      {rows_html}
    </table>
    <p style="font-size:12px;color:{TEXT_MUTED};line-height:1.6;margin:0 0 24px;">{event.no_refund_policy}</p>"""


def _ticket_card_html(ticket) -> str:
    email_line = (
        f'<p style="font-size:12px;color:rgba(255,230,133,0.75);margin:2px 0 0;">{ticket.participant_email}</p>'
        if ticket.participant_email
        else ""
    )
    return f"""
    <table role="presentation" width="100%" style="border-collapse:collapse;border-radius:14px;overflow:hidden;border:1px solid rgba(45,40,86,0.12);margin-bottom:12px;">
      <tr>
        <td style="background:{NAVY};padding:16px 20px;">
          <p style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,230,133,0.7);margin:0 0 4px;">
            Ingresso {ticket.ticket_code}
          </p>
          <p style="font-size:17px;font-weight:700;color:{GOLD};margin:0;">{ticket.participant_name}</p>
          {email_line}
        </td>
      </tr>
    </table>"""


def _qr_in_pdf_notice_html() -> str:
    return f"""
    <p style="font-size:13px;color:{TEXT_MUTED};background:{CREAM};border-radius:10px;padding:12px 16px;margin:0 0 20px;">
      Os QR Codes de entrada estão disponíveis no PDF em anexo — um por participante.
    </p>"""


def send_order_paid_emails(order) -> None:
    tickets = list(order.tickets.all())
    tickets_html = "".join(_ticket_card_html(ticket) for ticket in tickets)

    order_html = _email_shell(
        "Ingressos confirmados",
        f"""
        {_event_details_html(order)}
        <p style="font-size:14px;color:{TEXT_WARM};margin:0 0 4px;">Comprador: <strong>{order.buyer_name}</strong></p>
        {_qr_in_pdf_notice_html()}
        {tickets_html}""",
    )
    _send_email(
        "Ingressos confirmados",
        order_html,
        [order.buyer_email],
        attachments=[("ingressos.pdf", build_tickets_pdf_bytes(tickets), "application/pdf")],
    )

    for ticket in tickets:
        if not ticket.participant_email:
            continue
        html = _email_shell(
            "Seu ingresso da Festa Junina",
            f"""
            {_event_details_html(order)}
            {_qr_in_pdf_notice_html()}
            {_ticket_card_html(ticket)}""",
        )
        _send_email(
            "Seu ingresso da Festa Junina",
            html,
            [ticket.participant_email],
            attachments=[("ingresso.pdf", build_tickets_pdf_bytes([ticket]), "application/pdf")],
        )


def send_ticket_reissued_email(ticket, buyer_email: str) -> None:
    html = _email_shell(
        "Ingresso atualizado",
        f"""
        {_event_details_html(ticket.order)}
        <p style="font-size:14px;color:{TEXT_WARM};line-height:1.6;margin:0 0 4px;">
          O QR Code anterior foi invalidado. Use apenas o novo, disponível no PDF em anexo.
        </p>
        {_qr_in_pdf_notice_html()}
        {_ticket_card_html(ticket)}""",
    )
    _send_email(
        "Ingresso atualizado",
        html,
        [buyer_email, ticket.participant_email],
        attachments=[("ingresso.pdf", build_tickets_pdf_bytes([ticket]), "application/pdf")],
    )
