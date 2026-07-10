from django.urls import path

from .views import admin_login, me


urlpatterns = [
    path("login/", admin_login, name="admin-login"),
    path("me/", me, name="admin-me"),
]
