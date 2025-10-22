from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

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
