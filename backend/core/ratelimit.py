import logging
from functools import wraps
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Middleware intercepting Ratelimited exceptions across all views
    and returning structured HTTP 429 Too Many Requests JSON responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Ratelimited:
            return self.process_ratelimited(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            return self.process_ratelimited(request)
        return None

    def process_ratelimited(self, request):
        logger.warning(f"Rate limit exceeded for path {request.path} from IP {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({
            'status': 'error',
            'code': 'RATE_LIMIT_EXCEEDED',
            'message': 'Rate limit exceeded. Please wait before submitting more requests.'
        }, status=429)


def rate_limit_ip_or_user(rate_anon: str = "30/m", rate_user: str = "60/m", block: bool = True):
    """
    Decorator that dynamically applies rate limiting:
    - Authenticated users: limited by User ID at rate_user.
    - Anonymous users: limited by client IP at rate_anon.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            is_auth = user and getattr(user, 'is_authenticated', False)
            
            if is_auth:
                rate = rate_user
                key = lambda g, r: f"user:{r.user.id}"
            else:
                rate = rate_anon
                key = 'ip'
            
            # Apply django-ratelimit programmatically
            limited_func = ratelimit(key=key, rate=rate, block=block)(view_func)
            try:
                response = limited_func(request, *args, **kwargs)
                if getattr(request, 'limited', False) and not block:
                    return JsonResponse({
                        'status': 'error',
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Rate limit exceeded. Please slow down.'
                    }, status=429)
                return response
            except Ratelimited:
                return JsonResponse({
                    'status': 'error',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Rate limit exceeded. Please slow down.'
                }, status=429)

        return _wrapped_view
    return decorator
