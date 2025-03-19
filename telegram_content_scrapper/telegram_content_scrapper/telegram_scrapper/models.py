from django.db import models

# Create your models here.
from telethon.sessions.memory import MemorySession
from telethon.crypto import AuthKey
from telethon.tl.types import InputPhoto, InputDocument
import datetime
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import UniqueConstraint

User = settings.AUTH_USER_MODEL


class TelethonSession(models.Model):
    # session_name = models.CharField(max_length=255, unique=True)  # Unique identifier for the session
    phone_number = PhoneNumberField(blank=False)
    phone_number_hash = models.CharField(max_length=24)
    session_data = models.BinaryField(null=True, blank=True)  # Stores session as binary data
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.created_at}"

class TelegramEntity(models.Model):
    entity_id = models.BigIntegerField(db_index=True)
    entity_type = models.CharField(max_length=16)
    entity_name = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.entity_type} ({self.entity_name})"


class TelegramEntityContentData(models.Model):
    content_id = models.BigIntegerField(db_index=True)
    entity_text_content = models.TextField(blank=True)
    entity_media_data_content = models.BinaryField(null=True, blank=True)
    entity_media_data_type = models.CharField(blank=True)
    entity_content_url = models.TextField(blank=True)
    entity_post_timestamp = models.DateTimeField()
    processed_text_content = models.TextField(blank=True)
    text_content_hashtags = models.TextField(blank=True)
    date_in_text_content = models.CharField(max_length=16, null=True, blank=True)
    time_in_text_content = models.CharField(max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    telegram_entity = models.ForeignKey(TelegramEntity, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.telegram_entity.entity_type} ({self.telegram_entity.entity_name}) - content id - {self.content_id}"

    class Meta:
        constraints = [
            UniqueConstraint(fields=['content_id', 'telegram_entity'], name='unique_content_entity')
        ]


class TelegramUserEntity(models.Model):
    is_still_linked = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    telegram_entity = models.ForeignKey(TelegramEntity, on_delete=models.CASCADE)
    latest_downloaded_content = models.ForeignKey(TelegramEntityContentData, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} connection to {self.telegram_entity.entity_name} is {self.is_still_linked}"

