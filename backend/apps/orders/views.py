from rest_framework import generics, permissions, response, status

from .models import Order
from .serializers import CourtesyOrderCreateSerializer, OrderCreateSerializer, OrderSerializer


class OrderCreateView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = serializer.save()
        except Exception:
            return response.Response(
                {"detail": "Nao foi possivel iniciar o pagamento. Nenhum pedido foi criado."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        data = OrderSerializer(order).data
        data["access_token"] = order.access_token
        return response.Response(data, status=status.HTTP_201_CREATED)


class AdminCourtesyOrderCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CourtesyOrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return response.Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderLookupView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        lookup_code = request.data.get("public_id", "").strip()
        buyer_email = request.data.get("buyer_email", "").strip().lower()
        order = generics.get_object_or_404(
            Order,
            Order.lookup_filter(lookup_code),
            buyer_email__iexact=buyer_email,
        )
        data = OrderSerializer(order).data
        data["access_token"] = order.access_token
        return response.Response(data)


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OrderSerializer
    lookup_field = "public_id"
    queryset = Order.objects.prefetch_related("tickets__audit_logs").select_related("payment")

    def get_object(self):
        order = super().get_object()
        access_token = self.request.query_params.get("access_token", "")
        if access_token != order.access_token:
            raise permissions.PermissionDenied("Token de acesso invalido.")
        return order
