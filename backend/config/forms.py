from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django.contrib.auth.forms import SetPasswordForm

class CustomUserCreationForm(UserCreationForm):
    USER_TYPES = [
        ('student', 'Student'),
        ('researcher', 'Researcher'),
    ]

    user_type = forms.ChoiceField(choices=USER_TYPES)
    organization = forms.CharField(required=False, max_length=100)
    consent_to_share = forms.BooleanField(required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'user_type', 'organization', 'consent_to_share', 'password1', 'password2']

class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Completely remove the default help text
        self.fields['new_password2'].help_text = "Re-enter your new password for confirmation."
