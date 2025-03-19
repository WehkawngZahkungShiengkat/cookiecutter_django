import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "telegram_content_scrapper.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import telegram_content_scrapper.users.signals  # noqa: F401
