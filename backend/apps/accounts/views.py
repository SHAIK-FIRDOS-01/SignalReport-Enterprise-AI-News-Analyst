import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser
from apps.accounts.utils import generate_jwt, require_jwt, set_jwt_cookie, clear_jwt_cookie


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            first_name = data.get('first_name', '')
            
            if not email or not password:
                return JsonResponse({'status': 'error', 'message': 'Email and password required'}, status=400)
                
            if CustomUser.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
                
            user = CustomUser.objects.create_user(email=email, password=password, first_name=first_name)
            token = generate_jwt(user)
            
            response = JsonResponse({
                'status': 'success', 
                'token': token, 
                'user': {'email': user.email, 'first_name': user.first_name, 'role': user.role}
            }, status=201)
            return set_jwt_cookie(response, token)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            user = authenticate(email=email, password=password)
            if user:
                token = generate_jwt(user)
                response = JsonResponse({
                    'status': 'success', 
                    'token': token, 
                    'user': {
                        'email': user.email,
                        'first_name': user.first_name,
                        'role': user.role,
                        'ai_calls_used': getattr(user, 'ai_calls_used', 0),
                        'payment_method_active': getattr(user, 'payment_method_active', False),
                    }
                })
                return set_jwt_cookie(response, token)
            return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(View):
    def post(self, request):
        response = JsonResponse({'status': 'success', 'message': 'Logged out successfully'})
        return clear_jwt_cookie(response)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_jwt, name='dispatch')
class MeView(View):
    def get(self, request):
        return JsonResponse({
            'status': 'success',
            'user': {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'role': request.user.role,
                'ai_calls_used': getattr(request.user, 'ai_calls_used', 0),
                'payment_method_active': getattr(request.user, 'payment_method_active', False),
            }
        })
