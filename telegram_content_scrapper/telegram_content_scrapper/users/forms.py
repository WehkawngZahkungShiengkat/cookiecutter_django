from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import User
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """
    def only_int(value):
        value = value.replace(" ", "")
        if value[0] == "+":
            if value[1:].isdigit()==False:
                raise ValidationError('Invalid Phone Number Format')
        else:
            if value.isdigit()==False:
                raise ValidationError('Invalid Phone Number Format')
            
    # email = forms.EmailField()
    # telegram_phone_number = forms.CharField(
    #     validators=[only_int],
    #     label=_("Telegram account phone number"),
    #     min_length=5,
    #     max_length=16,
    #     help_text="You can get it from Telegram>My Profile",
    #     widget=forms.TextInput(
    #         attrs={"placeholder": _("+66 8 0123 4567"), "autocomplete": "off"}
    #     ),
    # )
    telegram_phone_number = PhoneNumberField(
        label=_("Telegram account phone number"),
        help_text="You can get it from Telegram>My Profile",
        widget=forms.TextInput(
            attrs={"placeholder": _("+66801234567"), "autocomplete": "off"}
        ),
    )
    # telegram_phone_number = forms.CharField(max_length=16, label="label telegram account phone number")
    # password = forms.PasswordInput()
    # comfirm_password = forms.PasswordInput()

    class Meta:
        model = User
        fields = ("email", "username", "telegram_phone_no", "password")
        # fields = ("telegram_phone_no")

    
    def save(self, request):
        user = super(UserSignupForm, self).save(request)
        user.telegram_phone_number = self.cleaned_data['telegram_phone_number']
        user.save()
        return user


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
