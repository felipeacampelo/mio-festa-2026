from django.shortcuts import get_object_or_404
from rest_framework import permissions, response
from rest_framework.decorators import api_view, permission_classes

from apps.tickets.models import Ticket
from apps.tickets.services import check_in_ticket, resolve_ticket_token


def _payload(ticket: Ticket, result: str):
    return {
        "result": result,
        "participant": {
            "ticket_id": ticket.id,
            "ticket_code": str(ticket.ticket_code),
            "name": ticket.participant_name,
            "email": ticket.participant_email,
            "status": ticket.status,
            "checked_in_at": ticket.checked_in_at,
        },
    }


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def scan_checkin(request):
    ticket = resolve_ticket_token(request.data.get("qr_token", ""))
    result = check_in_ticket(ticket, request.user)
    ticket.refresh_from_db()
    return response.Response(_payload(ticket, result))


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def manual_checkin(request):
    ticket = get_object_or_404(Ticket, ticket_code=request.data.get("ticket_code"))
    result = check_in_ticket(ticket, request.user)
    ticket.refresh_from_db()
    return response.Response(_payload(ticket, result))
