from django.urls import path

from .views import credit_card, debit_card, get_card, link_card, search_tickets, vendor_login, vendor_me

urlpatterns = [
    path("login/", vendor_login, name="vendor-login"),
    path("me/", vendor_me, name="vendor-me"),
    path("search-tickets/", search_tickets, name="cards-search-tickets"),
    path("<str:uid>/", get_card, name="cards-detail"),
    path("<str:uid>/link/", link_card, name="cards-link"),
    path("<str:uid>/debit/", debit_card, name="cards-debit"),
    path("<str:uid>/credit/", credit_card, name="cards-credit"),
]
