# Generated by Django 4.2.3 on 2023-07-26 12:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_meterrate_electricity_duty"),
    ]

    operations = [
        migrations.AlterField(
            model_name="meterrate",
            name="electricity_duty",
            field=models.IntegerField(),
        ),
    ]
