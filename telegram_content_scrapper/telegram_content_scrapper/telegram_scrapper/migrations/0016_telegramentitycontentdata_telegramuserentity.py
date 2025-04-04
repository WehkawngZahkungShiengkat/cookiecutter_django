# Generated by Django 5.0.12 on 2025-03-10 06:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_scrapper', '0015_remove_telegramuserentity_latest_downloaded_content_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramEntityContentData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_id', models.BigIntegerField(db_index=True)),
                ('entity_text_content', models.TextField(blank=True)),
                ('entity_media_data_content', models.BinaryField(blank=True, null=True)),
                ('entity_media_data_type', models.CharField(blank=True)),
                ('entity_content_url', models.TextField(blank=True)),
                ('entity_post_timestamp', models.DateTimeField()),
                ('processed_text_content', models.TextField(blank=True)),
                ('text_content_hashtags', models.TextField(blank=True)),
                ('date_in_text_content', models.CharField(blank=True, max_length=16, null=True)),
                ('time_in_text_content', models.CharField(blank=True, max_length=16, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('telegram_entity', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='telegram_scrapper.telegramentity')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TelegramUserEntity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_still_linked', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('latest_downloaded_content', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='telegram_scrapper.telegramentitycontentdata')),
                ('telegram_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='telegram_scrapper.telegramentity')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
