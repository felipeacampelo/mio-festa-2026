import csv

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.cards.models import Vendor


class Command(BaseCommand):
    help = (
        "Creates or updates vendor login accounts (sellers and recharge cashiers). "
        "Use --file with a CSV (username,password,display_name,role) for bulk setup, "
        "or the individual flags for a single vendor. Idempotent by username."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", help="CSV path with columns: username,password,display_name,role")
        parser.add_argument("--username")
        parser.add_argument("--password")
        parser.add_argument("--display-name")
        parser.add_argument("--role", choices=[Vendor.Role.SELLER, Vendor.Role.RECHARGE, Vendor.Role.CHECKIN])

    def handle(self, *args, **options):
        if options["file"]:
            with open(options["file"], newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            for row in rows:
                self._upsert_vendor(row["username"], row["password"], row["display_name"], row["role"])
            self.stdout.write(self.style.SUCCESS(f"{len(rows)} vendedor(es) processado(s)."))
            return

        required = ["username", "password", "display_name", "role"]
        missing = [f"--{name.replace('_', '-')}" for name in required if not options.get(name)]
        if missing:
            raise CommandError(f"Informe --file OU todos estes campos: {', '.join(missing)}")

        self._upsert_vendor(options["username"], options["password"], options["display_name"], options["role"])
        self.stdout.write(self.style.SUCCESS(f"Vendedor '{options['username']}' pronto."))

    def _upsert_vendor(self, username: str, password: str, display_name: str, role: str) -> None:
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"is_staff": False})
        user.is_staff = False
        user.set_password(password)
        user.save()
        Vendor.objects.update_or_create(
            user=user, defaults={"display_name": display_name, "role": role, "is_active": True}
        )
