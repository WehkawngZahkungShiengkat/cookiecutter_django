from django import forms

class TelegramAuthenticationForm(forms.Form):
    code = forms.CharField(label="OTP Code",widget=forms.TextInput(
            attrs={"placeholder": "Enter OTP Code", "autocomplete": "off", "class": "w-50 text-center form-control"}
        ),)