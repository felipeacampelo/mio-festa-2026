from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="is_child",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="ticket",
            name="participant_document",
            field=models.CharField(blank=True, max_length=14),
        ),
        migrations.AddField(
            model_name="ticket",
            name="participant_birth_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
