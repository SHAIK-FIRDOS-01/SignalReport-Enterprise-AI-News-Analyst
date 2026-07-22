import jwt
import datetime
from django.conf import settings
from functools import wraps
from django.http import JsonResponse
from apps.accounts.models import CustomUser

def generate_jwt(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def decode_jwt(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_jwt(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Allow preflight OPTIONS requests to pass through
        if request.method == 'OPTIONS':
            return view_func(request, *args, **kwargs)
            
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
        
        token = auth_header.split(' ')[1]
        payload = decode_jwt(token)
        
        if not payload:
            return JsonResponse({'status': 'error', 'message': 'Token expired or invalid'}, status=401)
            
        try:
            request.user = CustomUser.objects.get(id=payload['user_id'])
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=401)
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method == 'OPTIONS':
                return view_func(request, *args, **kwargs)
            
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
                
            if request.user.role not in allowed_roles:
                return JsonResponse({'status': 'error', 'message': f'Forbidden. Required roles: {allowed_roles}'}, status=403)
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
