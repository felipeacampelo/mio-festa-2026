import secrets
import string

from django.db import migrations, models


def generate_order_code(existing_codes):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "MIO-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if code not in existing_codes:
            existing_codes.add(code)
            return code


def backfill_order_codes(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    existing_codes = set(Order.objects.exclude(order_code="").values_list("order_code", flat=True))
    for order in Order.objects.filter(order_code=""):
        order.order_code = generate_order_code(existing_codes)
        order.save(update_fields=["order_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_code",
            field=models.CharField(blank=True, editable=False, max_length=10),
        ),
        migrations.RunPython(backfill_order_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_code",
            field=models.CharField(editable=False, max_length=10, unique=True),
        ),
    ]
