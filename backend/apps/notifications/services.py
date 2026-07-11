from typing import Iterable
import requests

from django.conf import settings
from django.core.mail import send_mail

from apps.tickets.services import build_ticket_qr_data_url


def _send_email(subject: str, html: str, recipients: Iterable[str]) -> None:
    emails = [email for email in recipients if email]
    if not emails:
        return
    if settings.RESEND_API_KEY:
        requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": emails,
                "subject": subject,
                "html": html,
            },
            timeout=20,
        ).raise_for_status()
        return

    send_mail(subject, "", settings.DEFAULT_FROM_EMAIL, emails, html_message=html, fail_silently=False)


def send_order_paid_emails(order) -> None:
    ticket_items = []
    for ticket in order.tickets.all():
        ticket_items.append(
            f"<li><strong>{ticket.participant_name}</strong><br/>"
            f"Codigo: {ticket.ticket_code}<br/>"
            f"<img alt='QR Ticket' src='{build_ticket_qr_data_url(ticket)}' style='max-width:220px' /></li>"
        )

    order_html = (
        f"<h1>Ingressos confirmados</h1>"
        f"<p>Pedido {order.order_code}</p>"
        f"<p>Comprador: {order.buyer_name}</p>"
        f"<ul>{''.join(ticket_items)}</ul>"
        f"<p>Politica: sem reembolso.</p>"
    )
    _send_email("Ingressos confirmados", order_html, [order.buyer_email])

    for ticket in order.tickets.all():
        if not ticket.participant_email:
            continue
        html = (
            f"<h1>Seu ingresso da Festa Junina</h1>"
            f"<p>Participante: {ticket.participant_name}</p>"
            f"<p>Codigo: {ticket.ticket_code}</p>"
            f"<img alt='QR Ticket' src='{build_ticket_qr_data_url(ticket)}' style='max-width:220px' />"
            f"<p>Sem reembolso.</p>"
        )
        _send_email("Seu ingresso da Festa Junina", html, [ticket.participant_email])


def send_ticket_reissued_email(ticket, buyer_email: str) -> None:
    html = (
        f"<h1>Ingresso atualizado</h1>"
        f"<p>Participante: {ticket.participant_name}</p>"
        f"<p>Codigo: {ticket.ticket_code}</p>"
        f"<img alt='QR Ticket' src='{build_ticket_qr_data_url(ticket)}' style='max-width:220px' />"
    )
    _send_email("Ingresso atualizado", html, [buyer_email, ticket.participant_email])
