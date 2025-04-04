# Generated by Django 5.0.12 on 2025-03-18 14:00

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_scrapper', '0016_telegramentitycontentdata_telegramuserentity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='telegramentitycontentdata',
            constraint=models.UniqueConstraint(fields=('content_id', 'telegram_entity'), name='unique_content_entity'),
        ),
    ]
