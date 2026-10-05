"""
JWT Authentication with Dual Header and HttpOnly Cookie resolution.
Replaces: backend/app/api/deps.py JWT parsing
Ponytail: Extends simplejwt's JWTAuthentication in ~30 lines, reusing its validated token decoder.
Security-audit: Enforces token expiration, cryptographic signature checks, and global revocation via tokens_valid_after.
"""

from datetime import datetime, timezone, timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    Extends SimpleJWT to inspect both Authorization Bearer headers
    and HttpOnly 'access_token' cookies.
    """

    def authenticate(self, request):
        # 1. Try standard Authorization header (Bearer <token>)
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self._authenticate_token(validated_token)

        # 2. Fallback to HttpOnly cookie
        cookie_token = request.COOKIES.get("access_token")
        if cookie_token:
            validated_token = self.get_validated_token(cookie_token)
            return self._authenticate_token(validated_token)

        return None

    def _authenticate_token(self, validated_token):
        user = self.get_user(validated_token)
        if not user or not user.is_active:
            raise AuthenticationFailed("User is inactive or deleted.", code="user_inactive")

        # Verify against revocation checkpoint
        iat = validated_token.get("iat")
        if iat is not None and getattr(user, "tokens_valid_after", None):
            token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
            # Add 2-second grace period for clock skew between integer iat and microsecond DB timestamp
            if token_issued_at + timedelta(seconds=2) < user.tokens_valid_after:
                raise AuthenticationFailed("Session has been revoked. Please log in again.", code="token_revoked")

        return (user, validated_token)
