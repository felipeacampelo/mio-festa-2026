from django.urls import path

from .admin_views import (
    admin_block_card,
    admin_card_list,
    admin_card_reconciliation,
    admin_return_card,
    admin_unblock_card,
)

urlpatterns = [
    path("", admin_card_list, name="admin-cards-list"),
    path("reconciliation/", admin_card_reconciliation, name="admin-cards-reconciliation"),
    path("<str:uid>/block/", admin_block_card, name="admin-cards-block"),
    path("<str:uid>/unblock/", admin_unblock_card, name="admin-cards-unblock"),
    path("<str:uid>/return/", admin_return_card, name="admin-cards-return"),
]
