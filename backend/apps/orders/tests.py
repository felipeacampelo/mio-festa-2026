from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import EventSettings
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import AsaasService, PaymentService
from apps.tickets.models import Ticket


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        event = EventSettings.get_solo()
        event.price = Decimal("25.00")
        event.location = "Patio da igreja"
        event.sales_end_at = timezone.now() + timedelta(days=2)
        event.capacity_total = 100
        event.save()

    def test_checkout_creates_order_and_tickets(self):
        response = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Maria",
                "buyer_email": "maria@example.com",
                "buyer_phone": "11999999999",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [
                    {"participant_name": "Joao", "participant_email": "joao@example.com"},
                    {"participant_name": "Ana", "participant_email": "ana@example.com"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.total_amount, Decimal("50.00"))
        self.assertEqual(Ticket.objects.count(), 2)
        self.assertEqual(Payment.objects.count(), 1)

    def test_checkout_blocks_when_sales_closed(self):
        event = EventSettings.get_solo()
        event.sales_end_at = timezone.now() - timedelta(hours=1)
        event.save()
        response = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Maria",
                "buyer_email": "maria@example.com",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [{"participant_name": "Joao"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_lookup_requires_matching_email(self):
        order = Order.objects.create(
            buyer_name="Maria",
            buyer_email="maria@example.com",
            quantity=1,
            unit_price=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            accepted_no_refund=True,
            payment_method=Order.PaymentMethod.PIX,
        )
        response = self.client.post("/api/orders/lookup/", {"public_id": str(order.public_id), "buyer_email": "maria@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_checkout_does_not_create_order_without_payment(self):
        with patch("apps.orders.serializers.PaymentService.ensure_payment", side_effect=Exception("asaas unavailable")):
            response = self.client.post(
                "/api/orders/checkout/",
                {
                    "buyer_name": "Maria",
                    "buyer_email": "maria@example.com",
                    "buyer_phone": "11999999999",
                    "payment_method": "pix",
                    "accepted_no_refund": True,
                    "participants": [
                        {"participant_name": "Joao", "participant_email": "joao@example.com"},
                    ],
                },
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)


class PaymentAndCheckinTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        event = EventSettings.get_solo()
        event.price = Decimal("25.00")
        event.sales_end_at = timezone.now() + timedelta(days=2)
        event.save()
        self.order = Order.objects.create(
            buyer_name="Paulo",
            buyer_email="paulo@example.com",
            quantity=1,
            unit_price=Decimal("25.00"),
            total_amount=Decimal("25.00"),
            accepted_no_refund=True,
            payment_method=Order.PaymentMethod.PIX,
        )
        self.ticket = Ticket.objects.create(order=self.order, participant_name="Paulo", participant_email="paulo@example.com")
        self.payment = PaymentService().ensure_payment(self.order)
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "123456")

    def test_confirm_payment_activates_ticket(self):
        PaymentService().confirm_payment(self.payment, {"manual": True})
        self.ticket.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ACTIVE)
        self.assertEqual(self.order.status, Order.Status.PAID)

    def test_checkin_is_idempotent(self):
        PaymentService().confirm_payment(self.payment, {"manual": True})
        from apps.tickets.services import build_ticket_token

        token = build_ticket_token(self.ticket)
        self.client.force_authenticate(self.admin)
        first = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        second = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        self.assertEqual(first.data["result"], "confirmed")
        self.assertEqual(second.data["result"], "already_checked_in")

    @patch.object(AsaasService, "get_payment", return_value={"id": "pay_test", "status": "OVERDUE"})
    def test_sync_payment_marks_order_and_payment_as_expired(self, _mock_get_payment):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/payments/admin/orders/{self.order.id}/sync/", format="json")
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.EXPIRED)
        self.assertEqual(self.order.status, Order.Status.EXPIRED)
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING)

    @patch.object(AsaasService, "get_payment", return_value={"id": "pay_test", "status": "RECEIVED"})
    def test_sync_payment_marks_order_as_paid_when_asaas_reports_received(self, _mock_get_payment):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/payments/admin/orders/{self.order.id}/sync/", format="json")
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.CONFIRMED)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.ticket.status, Ticket.Status.ACTIVE)
