import logging
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

FREE_AI_CALLS_LIMIT = 2
DEFAULT_AI_GATED_PREFIXES = (
    '/summarize',
    '/glossary',
    '/ask',
    '/briefings',
    '/api/ai',
)


class MonetizationMiddleware:
    """
    Middleware enforcing monetization gating:
    - Grants new users a hard quota of exactly 2 free AI calls (ai_calls_used < 2).
    - Hard stops quota-exceeded requests with HTTP 402 Payment Required.
    - Seamlessly bypasses quota limits for premium users (payment_method_active=True).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.gated_prefixes = getattr(settings, 'AI_GATED_PREFIXES', DEFAULT_AI_GATED_PREFIXES)

    def is_ai_gated_path(self, path: str) -> bool:
        """Check if request path corresponds to a compute-intensive AI endpoint."""
        clean_path = path.rstrip('/')
        for prefix in self.gated_prefixes:
            if clean_path == prefix.rstrip('/') or path.startswith(prefix):
                return True
        return False

    def __call__(self, request):
        if not self.is_ai_gated_path(request.path):
            return self.get_response(request)

        # Gated AI endpoint check
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'code': 'UNAUTHORIZED',
                'message': 'Authentication required to access AI intelligence services'
            }, status=401)

        # 1. Premium bypass
        if getattr(user, 'payment_method_active', False):
            return self.get_response(request)

        # 2. Freemium quota check
        ai_calls_used = getattr(user, 'ai_calls_used', 0)
        if ai_calls_used >= FREE_AI_CALLS_LIMIT:
            logger.info(f"User {user.email} exceeded free AI quota ({ai_calls_used}/{FREE_AI_CALLS_LIMIT}). Returning 402.")
            return JsonResponse({
                'status': 'error',
                'code': 'PAYMENT_REQUIRED',
                'message': f'Free trial limit reached ({FREE_AI_CALLS_LIMIT}/{FREE_AI_CALLS_LIMIT} AI calls used). Please add a payment method to unlock unlimited AI access.',
                'ai_calls_used': ai_calls_used,
                'payment_method_active': False,
                'upgrade_url': '/api/billing/checkout/'
            }, status=402)

        # 3. Increment quota and allow call
        user.ai_calls_used = ai_calls_used + 1
        try:
            user.save(update_fields=['ai_calls_used'])
        except Exception as e:
            logger.warning(f"Failed to update ai_calls_used for {user.email}: {e}")

        return self.get_response(request)
