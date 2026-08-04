from rest_framework import permissions

from .models import Vendor


class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        vendor = getattr(user, "vendor_profile", None)
        return bool(vendor and vendor.is_active)


class IsSeller(IsVendor):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.vendor_profile.role == Vendor.Role.SELLER


class IsRecharge(IsVendor):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.vendor_profile.role == Vendor.Role.RECHARGE


class IsCheckin(IsVendor):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.vendor_profile.role == Vendor.Role.CHECKIN
