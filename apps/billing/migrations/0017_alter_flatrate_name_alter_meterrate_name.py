# Generated by Django 4.2.3 on 2023-08-05 02:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0016_alter_flatrateadditional_rate_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flatrate',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='meterrate',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
