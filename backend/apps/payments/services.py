import uuid
from decimal import Decimal
from typing import Optional
import logging

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from apps.notifications.services import send_order_paid_emails
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.tickets.models import Ticket
from apps.tickets.services import activate_ticket

logger = logging.getLogger("apps.payments")


class AsaasService:
    def __init__(self):
        self.api_key = settings.ASAAS_API_KEY
        self.base_url = settings.ASAAS_BASE_URL.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _ensure_configured_for_production(self):
        if settings.ASAAS_ENV == "production" and not self.configured:
            logger.error("Asaas is not configured for production payments")
            raise ImproperlyConfigured("ASAAS_API_KEY is required when ASAAS_ENV=production.")

    def _request(self, method: str, path: str, payload=None):
        self._ensure_configured_for_production()
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers={"access_token": self.api_key, "Content-Type": "application/json"},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Asaas request succeeded method=%s path=%s status_code=%s",
                method,
                path,
                response.status_code,
            )
            return data
        except requests.RequestException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            response_text = getattr(getattr(exc, "response", None), "text", "")
            logger.exception(
                "Asaas request failed method=%s path=%s status_code=%s payload=%s response=%s",
                method,
                path,
                status_code,
                payload,
                response_text[:1000],
            )
            raise

    def _customer_payload(self, order: Order) -> dict:
        return {
            "name": order.buyer_name,
            "email": order.buyer_email,
            "mobilePhone": order.buyer_phone,
            "cpfCnpj": order.buyer_document,
        }

    def create_pix_payment(self, order: Order) -> dict:
        self._ensure_configured_for_production()
        if not self.configured:
            external_id = f"pix_{uuid.uuid4().hex[:12]}"
            logger.info(
                "Using sandbox PIX payment fallback order_id=%s public_id=%s external_id=%s",
                order.id,
                order.public_id,
                external_id,
            )
            return {
                "id": external_id,
                "invoiceUrl": f"{settings.FRONTEND_URL}/pedido/{order.public_id}?sandbox=pix",
                "pixCode": f"000201010212PIX{external_id}",
                "encodedImage": "",
            }
        logger.info(
            "Creating PIX payment order_id=%s public_id=%s amount=%s",
            order.id,
            order.public_id,
            order.total_amount,
        )
        customer_resp = self._request("POST", "customers", self._customer_payload(order))
        payment_resp = self._request(
            "POST",
            "payments",
            {
                "customer": customer_resp["id"],
                "billingType": "PIX",
                "value": float(order.total_amount),
                "dueDate": timezone.now().date().isoformat(),
                "description": f"Pedido {order.public_id}",
                "externalReference": str(order.public_id),
            },
        )
        pix_resp = self._request("GET", f"payments/{payment_resp['id']}/pixQrCode")
        return {
            "id": payment_resp["id"],
            "invoiceUrl": payment_resp.get("invoiceUrl", ""),
            "pixCode": pix_resp.get("payload", ""),
            "encodedImage": pix_resp.get("encodedImage", ""),
        }

    def create_credit_card_checkout(self, order: Order) -> dict:
        self._ensure_configured_for_production()
        if not self.configured:
            external_id = f"card_{uuid.uuid4().hex[:12]}"
            logger.info(
                "Using sandbox credit checkout fallback order_id=%s public_id=%s external_id=%s",
                order.id,
                order.public_id,
                external_id,
            )
            return {
                "id": external_id,
                "invoiceUrl": f"{settings.FRONTEND_URL}/pedido/{order.public_id}?sandbox=credit",
            }
        logger.info(
            "Creating credit card checkout order_id=%s public_id=%s amount=%s",
            order.id,
            order.public_id,
            order.total_amount,
        )
        customer_resp = self._request("POST", "customers", self._customer_payload(order))
        payment_resp = self._request(
            "POST",
            "payments",
            {
                "customer": customer_resp["id"],
                "billingType": "CREDIT_CARD",
                "value": float(order.total_amount),
                "dueDate": timezone.now().date().isoformat(),
                "description": f"Pedido {order.public_id}",
                "externalReference": str(order.public_id),
            },
        )
        return {"id": payment_resp["id"], "invoiceUrl": payment_resp.get("invoiceUrl", "")}

    def get_payment(self, external_id: str) -> dict:
        self._ensure_configured_for_production()
        if not self.configured:
            logger.info("Using sandbox payment sync fallback external_id=%s", external_id)
            return {"id": external_id, "status": "PENDING"}
        logger.info("Fetching payment status from Asaas external_id=%s", external_id)
        return self._request("GET", f"payments/{external_id}")


class PaymentService:
    def __init__(self):
        self.asaas = AsaasService()

    @transaction.atomic
    def ensure_payment(self, order: Order) -> Optional[Payment]:
        if order.total_amount <= 0:
            self._confirm_free_order(order)
            return None
        logger.info(
            "Ensuring payment order_id=%s public_id=%s method=%s status=%s",
            order.id,
            order.public_id,
            order.payment_method,
            order.status,
        )
        payment, _ = Payment.objects.get_or_create(order=order, defaults={"method": order.payment_method})
        payment.method = order.payment_method
        if order.payment_method == Order.PaymentMethod.PIX:
            payload = self.asaas.create_pix_payment(order)
            payment.external_id = payload["id"]
            payment.checkout_url = payload.get("invoiceUrl", "")
            payment.pix_copy_paste = payload.get("pixCode", "")
            payment.pix_qr_code = payload.get("encodedImage", "")
        else:
            payload = self.asaas.create_credit_card_checkout(order)
            payment.external_id = payload["id"]
            payment.checkout_url = payload.get("invoiceUrl", "")
        payment.raw_payload = payload
        payment.status = Payment.Status.PENDING
        payment.save()
        logger.info(
            "Payment ensured order_id=%s payment_id=%s external_id=%s method=%s",
            order.id,
            payment.id,
            payment.external_id,
            payment.method,
        )
        return payment

    def _confirm_free_order(self, order: Order) -> Order:
        logger.info(
            "Confirming free order without payment order_id=%s public_id=%s total_amount=%s",
            order.id,
            order.public_id,
            order.total_amount,
        )
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at", "updated_at"])
        for ticket in order.tickets.all():
            if ticket.status == Ticket.Status.PENDING:
                activate_ticket(ticket)
        logger.info(
            "Free order confirmed and tickets activated order_id=%s tickets=%s",
            order.id,
            order.tickets.count(),
        )
        send_order_paid_emails(order)
        return order

    def _apply_expired_status(self, payment: Payment, payload: Optional[dict] = None) -> Payment:
        if payment.status == Payment.Status.EXPIRED and payment.order.status == Order.Status.EXPIRED:
            logger.info(
                "Payment already expired payment_id=%s order_id=%s external_id=%s",
                payment.id,
                payment.order_id,
                payment.external_id,
            )
            return payment
        logger.warning(
            "Marking payment as expired payment_id=%s order_id=%s external_id=%s previous_payment_status=%s previous_order_status=%s",
            payment.id,
            payment.order_id,
            payment.external_id,
            payment.status,
            payment.order.status,
        )
        payment.status = Payment.Status.EXPIRED
        if payload:
            payment.raw_payload = payload
        payment.save(update_fields=["status", "raw_payload", "updated_at"])
        order = payment.order
        if order.status != Order.Status.PAID:
            order.status = Order.Status.EXPIRED
            order.save(update_fields=["status", "updated_at"])
        return payment

    @transaction.atomic
    def confirm_payment(self, payment: Payment, payload: Optional[dict] = None) -> Payment:
        if payment.status == Payment.Status.CONFIRMED and payment.order.status == Order.Status.PAID:
            logger.info(
                "Payment confirmation ignored because it is already confirmed payment_id=%s order_id=%s external_id=%s",
                payment.id,
                payment.order_id,
                payment.external_id,
            )
            return payment
        logger.info(
            "Confirming payment payment_id=%s order_id=%s external_id=%s previous_payment_status=%s previous_order_status=%s",
            payment.id,
            payment.order_id,
            payment.external_id,
            payment.status,
            payment.order.status,
        )
        payment.status = Payment.Status.CONFIRMED
        if payload:
            payment.raw_payload = payload
        payment.save(update_fields=["status", "raw_payload", "updated_at"])
        order = payment.order
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at", "updated_at"])
        for ticket in order.tickets.all():
            if ticket.status == Ticket.Status.PENDING:
                activate_ticket(ticket)
        logger.info(
            "Payment confirmed and tickets activated order_id=%s payment_id=%s tickets=%s",
            order.id,
            payment.id,
            order.tickets.count(),
        )
        send_order_paid_emails(order)
        return payment

    @transaction.atomic
    def sync_payment_status(self, payment: Payment) -> Payment:
        logger.info(
            "Synchronizing payment status payment_id=%s order_id=%s external_id=%s current_payment_status=%s current_order_status=%s",
            payment.id,
            payment.order_id,
            payment.external_id,
            payment.status,
            payment.order.status,
        )
        payload = self.asaas.get_payment(payment.external_id)
        status_value = str(payload.get("status", "")).upper()
        logger.info(
            "Asaas synchronization result payment_id=%s external_id=%s asaas_status=%s",
            payment.id,
            payment.external_id,
            status_value,
        )
        if status_value in {"RECEIVED", "CONFIRMED"}:
            return self.confirm_payment(payment, payload)
        if status_value in {"OVERDUE", "DELETED", "REFUNDED", "RECEIVED_IN_CASH_UNDONE"}:
            return self._apply_expired_status(payment, payload)
        payment.raw_payload = payload
        payment.status = Payment.Status.PENDING
        payment.save(update_fields=["raw_payload", "status", "updated_at"])
        if payment.order.status != Order.Status.PAID:
            payment.order.status = Order.Status.PENDING
            payment.order.save(update_fields=["status", "updated_at"])
        logger.info(
            "Payment remains pending after sync payment_id=%s order_id=%s external_id=%s",
            payment.id,
            payment.order_id,
            payment.external_id,
        )
        return payment
