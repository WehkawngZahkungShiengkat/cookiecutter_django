# Generated by Django 5.0.12 on 2025-02-28 04:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_scrapper', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='telethonsession',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
