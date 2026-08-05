from django.urls import path

from .admin_views import admin_product_detail, admin_product_list

urlpatterns = [
    path("", admin_product_list, name="admin-products-list"),
    path("<int:pk>/", admin_product_detail, name="admin-products-detail"),
]
