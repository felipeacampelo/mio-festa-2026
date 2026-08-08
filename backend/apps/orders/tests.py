from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import Vendor
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
                "buyer_document": "12345678909",
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
        self.assertRegex(order.order_code, r"^MIO-[A-Z0-9]{6}$")
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
                "buyer_document": "12345678909",
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

    def test_lookup_accepts_order_code(self):
        order = Order.objects.create(
            buyer_name="Maria",
            buyer_email="maria@example.com",
            quantity=1,
            unit_price=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            accepted_no_refund=True,
            payment_method=Order.PaymentMethod.PIX,
        )
        response = self.client.post(
            "/api/orders/lookup/",
            {"public_id": order.order_code.lower(), "buyer_email": "maria@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["order_code"], order.order_code)

    def test_checkout_does_not_create_order_without_payment(self):
        with patch("apps.orders.serializers.PaymentService.ensure_payment", side_effect=Exception("asaas unavailable")):
            response = self.client.post(
                "/api/orders/checkout/",
                {
                    "buyer_name": "Maria",
                    "buyer_email": "maria@example.com",
                    "buyer_phone": "11999999999",
                    "buyer_document": "12345678909",
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

    def test_pending_orders_do_not_consume_capacity(self):
        event = EventSettings.get_solo()
        event.capacity_total = 1
        event.save()

        first = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Maria",
                "buyer_email": "maria@example.com",
                "buyer_document": "12345678909",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [{"participant_name": "Joao"}],
            },
            format="json",
        )
        second = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Ana",
                "buyer_email": "ana@example.com",
                "buyer_document": "98765432100",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [{"participant_name": "Ana"}],
            },
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Ticket.objects.filter(status=Ticket.Status.PENDING).count(), 2)

    def test_checkout_blocks_when_paid_capacity_is_full(self):
        event = EventSettings.get_solo()
        event.capacity_total = 1
        event.save()
        paid_order = Order.objects.create(
            buyer_name="Pago",
            buyer_email="pago@example.com",
            quantity=1,
            unit_price=Decimal("25.00"),
            total_amount=Decimal("25.00"),
            accepted_no_refund=True,
            payment_method=Order.PaymentMethod.PIX,
            status=Order.Status.PAID,
            paid_at=timezone.now(),
        )
        Ticket.objects.create(order=paid_order, participant_name="Pago", status=Ticket.Status.ACTIVE)

        response = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Maria",
                "buyer_email": "maria@example.com",
                "buyer_document": "12345678909",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [{"participant_name": "Joao"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(ASAAS_ENV="production", ASAAS_API_KEY="")
    def test_production_checkout_fails_without_asaas_api_key(self):
        response = self.client.post(
            "/api/orders/checkout/",
            {
                "buyer_name": "Maria",
                "buyer_email": "maria@example.com",
                "buyer_document": "12345678909",
                "payment_method": "pix",
                "accepted_no_refund": True,
                "participants": [{"participant_name": "Joao"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(Order.objects.count(), 0)
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
        checkin_user = User.objects.create_user("checkin_staff", password="123456")
        self.checkin_vendor = Vendor.objects.create(
            user=checkin_user, role=Vendor.Role.CHECKIN, display_name="Checkin", is_active=True
        )

    def test_confirm_payment_activates_ticket(self):
        PaymentService().confirm_payment(self.payment, {"manual": True})
        self.ticket.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ACTIVE)
        self.assertEqual(self.order.status, Order.Status.PAID)

    def test_confirm_payment_does_not_send_duplicate_emails(self):
        with patch("apps.payments.services.send_order_paid_emails") as mock_send:
            PaymentService().confirm_payment(self.payment, {"manual": True})
            PaymentService().confirm_payment(self.payment, {"manual": True})

        self.assertEqual(mock_send.call_count, 1)

    def test_confirm_payment_persists_even_if_email_sending_fails(self):
        # O Resend caindo/dando timeout nao pode desfazer uma confirmacao de
        # pagamento que ja aconteceu de verdade no Asaas.
        with patch("apps.payments.services.send_order_paid_emails", side_effect=Exception("resend indisponivel")):
            PaymentService().confirm_payment(self.payment, {"manual": True})

        self.ticket.refresh_from_db()
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ACTIVE)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.payment.status, Payment.Status.CONFIRMED)

    def test_checkin_is_idempotent(self):
        PaymentService().confirm_payment(self.payment, {"manual": True})
        from apps.tickets.services import build_ticket_token

        token = build_ticket_token(self.ticket)
        self.client.force_authenticate(self.checkin_vendor.user)
        first = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        second = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        self.assertEqual(first.data["result"], "confirmed")
        self.assertEqual(second.data["result"], "already_checked_in")

    def test_admin_without_checkin_role_cannot_scan(self):
        from apps.tickets.services import build_ticket_token

        token = build_ticket_token(self.ticket)
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_scan(self):
        from apps.tickets.services import build_ticket_token

        token = build_ticket_token(self.ticket)
        response = self.client.post("/api/checkin/scan/", {"qr_token": token}, format="json")
        self.assertEqual(response.status_code, 401)

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

    def test_admin_ticket_list_hides_pending_tickets_until_payment_confirmation(self):
        self.client.force_authenticate(self.admin)

        pending_response = self.client.get("/api/admin/tickets/")
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.data["results"], [])

        PaymentService().confirm_payment(self.payment, {"manual": True})
        active_response = self.client.get("/api/admin/tickets/")

        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(len(active_response.data["results"]), 1)
        self.assertEqual(active_response.data["results"][0]["status"], Ticket.Status.ACTIVE)

    def test_admin_cannot_resend_tickets_before_payment_confirmation(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/admin/orders/{self.order.id}/resend-tickets/", format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Ingressos so podem ser reenviados apos pagamento confirmado.")

    def test_admin_force_confirm_is_disabled_by_default(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/payments/admin/orders/{self.order.id}/confirm/", format="json")

        self.assertEqual(response.status_code, 403)
