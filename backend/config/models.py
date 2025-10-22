from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    USER_TYPES = [
        ('admin', 'Admin'),
        ('researcher', 'Researcher'),
        ('student', 'Student'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    organization = models.CharField(max_length=100, blank=True, null=True)
    consent_to_share = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, default='pending')

    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username'] 

    def __str__(self):
        return f"{self.username} ({self.user_type})"
