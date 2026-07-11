import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Creates a superuser from DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD env vars "
        "if no superuser exists yet. Idempotent, safe to run on every deploy start."
    )

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD nao definidos, pulando bootstrap do admin.")
            return

        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Ja existe um superuser, pulando bootstrap do admin.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' criado."))
