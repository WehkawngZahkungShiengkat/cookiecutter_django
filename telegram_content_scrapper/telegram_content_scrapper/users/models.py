from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    """
    Default custom user model for telegram_content_scrapper.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    # telegram_phone_number = CharField(max_length=16, unique=True, blank=True)
    telegram_phone_number = PhoneNumberField(blank=True)

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    # def save(self, *args, **kwargs):
    #     if self.phone_number:
    #         self.phone_number = format_phone_number(self.phone_number)
    #     super().save(*args, **kwargs)
