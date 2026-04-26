from functools import wraps
from django.shortcuts import redirect


def admin_required(view_func):
    """Restrict view to users with user_type='admin'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not getattr(request.user, 'user_type', None) == 'admin':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def researcher_required(view_func):
    """Restrict view to users with user_type='researcher' or 'admin'."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if getattr(request.user, 'user_type', None) not in ('researcher', 'admin'):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper