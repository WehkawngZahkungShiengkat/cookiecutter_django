from django.contrib import admin
from .models import TelethonSession, TelegramEntity, TelegramEntityContentData, TelegramUserEntity

# Register your models here.


admin.site.register(TelethonSession)
admin.site.register(TelegramEntity)
admin.site.register(TelegramEntityContentData)
admin.site.register(TelegramUserEntity)