from rest_framework import permissions, response, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import AuthenticationFailed

from django.contrib.auth import authenticate

from apps.core.throttling import LoginRateThrottle


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([LoginRateThrottle])
def admin_login(request):
    user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
    if not user or not user.is_staff:
        raise AuthenticationFailed("Credenciais invalidas.")
    token, _ = Token.objects.get_or_create(user=user)
    return response.Response(
        {
            "token": token.key,
            "user": {"id": user.id, "username": user.username, "is_staff": user.is_staff},
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def me(request):
    return response.Response({"id": request.user.id, "username": request.user.username, "is_staff": request.user.is_staff})
