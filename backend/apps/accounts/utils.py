import jwt
import datetime
from functools import wraps
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import AnonymousUser
from apps.accounts.models import CustomUser

JWT_COOKIE_NAME = "access_token"
JWT_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


def _get_jwt_secret() -> str:
    return getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)


def _get_jwt_algorithm() -> str:
    return getattr(settings, 'JWT_ALGORITHM', 'HS256')


def generate_jwt(user: CustomUser) -> str:
    """Generate a signed JWT token containing user identity and role claims."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': getattr(user, 'role', 'STANDARD'),
        'exp': now + datetime.timedelta(seconds=JWT_MAX_AGE_SECONDS),
        'iat': now,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_get_jwt_algorithm())


def decode_jwt(token: str) -> dict | None:
    """Decode and cryptographically verify JWT token signature and expiration."""
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[_get_jwt_algorithm()]
        )
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None


def set_jwt_cookie(response: HttpResponse, token: str, max_age: int = JWT_MAX_AGE_SECONDS) -> HttpResponse:
    """Attach HttpOnly, SameSite=Lax JWT authentication cookie to prevent XSS exfiltration."""
    secure_cookie = getattr(settings, 'SESSION_COOKIE_SECURE', False) or (not getattr(settings, 'DEBUG', True))
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookie,
        samesite='Lax',
        path='/'
    )
    return response


def clear_jwt_cookie(response: HttpResponse) -> HttpResponse:
    """Clear and invalidate the JWT authentication cookie."""
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        path='/'
    )
    return response


def extract_token_from_request(request) -> str | None:
    """Extract JWT token from HttpOnly cookie or Authorization Bearer header."""
    token = request.COOKIES.get(JWT_COOKIE_NAME)
    if token:
        return token
    
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1].strip()
    
    return None


def require_jwt(view_func):
    """View decorator ensuring request possesses a valid JWT token via cookie or header."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            return view_func(request, *args, **kwargs)
            
        token = extract_token_from_request(request)
        if not token:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        
        payload = decode_jwt(token)
        if not payload:
            return JsonResponse({'status': 'error', 'message': 'Token expired or invalid'}, status=401)
            
        user_list = list(CustomUser.objects.filter(id=payload['user_id']))
        if not user_list:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=401)
        
        request.user = user_list[0]
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles: list[str]):
    """View decorator restricting access to specified user roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return view_func(request, *args, **kwargs)
            
            if not hasattr(request, 'user') or not getattr(request.user, 'is_authenticated', False):
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
                
            if getattr(request.user, 'role', None) not in allowed_roles:
                return JsonResponse({'status': 'error', 'message': f'Forbidden. Required roles: {allowed_roles}'}, status=403)
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
