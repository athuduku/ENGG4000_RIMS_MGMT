from django.utils.deprecation import MiddlewareMixin

class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

from django.shortcuts import redirect

class ForcePasswordChangeMiddleware:
    EXEMPT = ['/set-password/', '/login/', '/logout/', '/static/', '/admin/', '/api/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'force_password_change', False)
            and not any(request.path.startswith(p) for p in self.EXEMPT)
        ):
            return redirect('set_password')
        return self.get_response(request)