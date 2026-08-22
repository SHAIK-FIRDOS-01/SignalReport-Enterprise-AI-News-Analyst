import uuid
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from apps.accounts.models import CustomUser
from apps.accounts.utils import decode_jwt, extract_token_from_request


class JWTCookieAuthenticationMiddleware:
    """
    Middleware that seamlessly authenticates requests using HttpOnly JWT cookies
    or fallback Authorization Bearer tokens, populating request.user with CustomUser.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = extract_token_from_request(request)
        if token:
            payload = decode_jwt(token)
            if payload and 'user_id' in payload:
                user_list = list(CustomUser.objects.filter(id=payload['user_id']))
                if user_list:
                    request.user = user_list[0]
        
        if not hasattr(request, 'user'):
            request.user = AnonymousUser()

        return self.get_response(request)


class SecurityMiddleware:
    """
    Custom SecurityMiddleware to enforce Zero-Trust principles,
    inject strict Content Security Policy (CSP), and mitigate XSS.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a nonce for inline scripts/styles if needed in the future
        request.csp_nonce = str(uuid.uuid4())

        response = self.get_response(request)

        # 1. Strict Content Security Policy (CSP)
        csp_directives = {
            "default-src": ["'self'"],
            "script-src": ["'self'", f"'nonce-{request.csp_nonce}'", "https://cdn.jsdelivr.net"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:", "https:"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "form-action": ["'self'"],
            "base-uri": ["'self'"],
            "object-src": ["'none'"],
        }
        csp_header = "; ".join(f"{key} {' '.join(value)}" for key, value in csp_directives.items())
        response['Content-Security-Policy'] = csp_header

        # 2. X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'

        # 3. Cache-Control (Zero-Trust: Prevent caching of sensitive data by default)
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'

        # 4. Referrer-Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # 5. Permissions-Policy
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response
