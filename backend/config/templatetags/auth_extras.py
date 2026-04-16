from django import template
from django_otp import devices_for_user

register = template.Library()

@register.filter
def has_2fa(user):
    if not user or not user.is_authenticated:
        return False

    return any(
        getattr(d, 'confirmed', False)
        for d in devices_for_user(user)
    )