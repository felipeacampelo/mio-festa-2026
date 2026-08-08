import logging

from django.conf import settings
from rest_framework import permissions, response, status
from rest_framework.decorators import api_view, permission_classes

from apps.cards.permissions import IsCheckin
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import PaymentService

logger = logging.getLogger("apps.payments")


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def asaas_webhook(request):
    expected = request.headers.get("asaas-access-token", "").strip()
    configured = (settings.ASAAS_WEBHOOK_TOKEN or "").strip()
    if configured and expected != configured:
        logger.warning(
            "Rejected Asaas webhook because token is invalid configured_length=%s received_length=%s",
            len(configured),
            len(expected),
        )
        return response.Response({"detail": "invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

    payment_payload = request.data.get("payment") or {}
    external_id = payment_payload.get("id")
    if not external_id:
        logger.warning("Rejected Asaas webhook because payment id is missing payload=%s", request.data)
        return response.Response({"detail": "missing payment id"}, status=status.HTTP_400_BAD_REQUEST)
    payment = Payment.objects.filter(external_id=external_id).select_related("order").first()
    if not payment:
        logger.warning("Received Asaas webhook for unknown payment external_id=%s payload=%s", external_id, request.data)
        return response.Response({"detail": "payment not found"}, status=status.HTTP_404_NOT_FOUND)

    event = (request.data.get("event") or "").upper()
    logger.info(
        "Received Asaas webhook event=%s payment_id=%s order_id=%s external_id=%s raw_status=%s",
        event,
        payment.id,
        payment.order_id,
        payment.external_id,
        payment_payload.get("status"),
    )
    if event in {"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED", "PAYMENT_UPDATED"}:
        status_value = (payment_payload.get("status") or "").upper()
        if status_value in {"CONFIRMED", "RECEIVED"} or event != "PAYMENT_UPDATED":
            PaymentService().confirm_payment(payment, request.data)
        elif status_value in {"OVERDUE", "DELETED", "REFUNDED", "RECEIVED_IN_CASH_UNDONE"}:
            PaymentService().sync_payment_status(payment)
    elif event in {"PAYMENT_OVERDUE", "PAYMENT_DELETED"}:
        PaymentService().sync_payment_status(payment)
    else:
        logger.info(
            "Ignoring unsupported Asaas webhook event=%s payment_id=%s external_id=%s",
            event,
            payment.id,
            payment.external_id,
        )
    return response.Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_force_confirm(request, order_id: int):
    if not settings.ALLOW_MANUAL_PAYMENT_CONFIRMATION:
        logger.warning(
            "Admin force confirmation rejected because ALLOW_MANUAL_PAYMENT_CONFIRMATION is disabled actor=%s order_id=%s",
            request.user.username,
            order_id,
        )
        return response.Response(
            {"detail": "Confirmacao manual de pagamento esta desabilitada."},
            status=status.HTTP_403_FORBIDDEN,
        )
    order = Order.objects.get(pk=order_id)
    payment = order.payment
    logger.warning(
        "Admin force confirmation requested order_id=%s payment_id=%s external_id=%s actor=%s",
        order.id,
        payment.id,
        payment.external_id,
        request.user.username,
    )
    PaymentService().confirm_payment(payment, {"manual": True})
    return response.Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_sync_payment(request, order_id: int):
    order = Order.objects.get(pk=order_id)
    payment = order.payment
    logger.info(
        "Admin sync payment requested order_id=%s payment_id=%s external_id=%s actor=%s",
        order.id,
        payment.id,
        payment.external_id,
        request.user.username,
    )
    updated_payment = PaymentService().sync_payment_status(payment)
    return response.Response(
        {
            "ok": True,
            "payment_status": updated_payment.status,
            "order_status": updated_payment.order.status,
        }
    )


@api_view(["POST"])
@permission_classes([IsCheckin])
def vendor_sync_pending_payments(request):
    logger.info("Checkin bulk payment sync requested actor=%s", request.user.username)
    result = PaymentService().sync_pending_payments()
    return response.Response({"ok": True, **result})
