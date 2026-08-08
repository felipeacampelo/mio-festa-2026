from django.urls import path

from .admin_views import (
    admin_block_card,
    admin_card_list,
    admin_card_reconciliation,
    admin_return_card,
    admin_seller_list,
    admin_unblock_card,
    admin_vendor_impersonate,
    admin_vendor_list,
)

urlpatterns = [
    path("", admin_card_list, name="admin-cards-list"),
    path("sellers/", admin_seller_list, name="admin-sellers-list"),
    path("vendors/", admin_vendor_list, name="admin-vendors-list"),
    path("vendors/<int:pk>/impersonate/", admin_vendor_impersonate, name="admin-vendors-impersonate"),
    path("reconciliation/", admin_card_reconciliation, name="admin-cards-reconciliation"),
    path("<str:uid>/block/", admin_block_card, name="admin-cards-block"),
    path("<str:uid>/unblock/", admin_unblock_card, name="admin-cards-unblock"),
    path("<str:uid>/return/", admin_return_card, name="admin-cards-return"),
]
