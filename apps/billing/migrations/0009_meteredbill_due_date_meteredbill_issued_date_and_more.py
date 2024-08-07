# Generated by Django 4.2.3 on 2023-07-30 05:43

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0008_rename_total_bii_unmeteredbill_total_bill'),
    ]

    operations = [
        migrations.AddField(
            model_name='meteredbill',
            name='due_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AddField(
            model_name='meteredbill',
            name='issued_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AddField(
            model_name='unmeteredbill',
            name='due_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AddField(
            model_name='unmeteredbill',
            name='issued_date',
            field=models.DateField(default=datetime.date.today),
        ),
    ]