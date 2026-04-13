from django import template
from django_otp import devices_for_user

register = template.Library()

@register.filter
def has_2fa(user):
    return any(
        d.confirmed for d in devices_for_user(user)
        if hasattr(d, 'confirmed')
    )