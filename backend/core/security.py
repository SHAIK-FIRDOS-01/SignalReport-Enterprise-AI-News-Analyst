"""
Security middleware, IP resolution, rate limiters, and response headers for SignalReport Django project.
Replaces: backend/app/core/security_headers.py, backend/app/core/security_proxy.py, backend/app/core/security/rate_limiter.py
Ponytail: Standard library ipaddress, time, and uuid data structures without external Redis dependency.
Security-audit: Enforces Cloudflare edge verification, HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and brute-force lockouts.
"""

import ipaddress
import time
import uuid
from typing import Dict, List, Optional
from django.http import JsonResponse, HttpRequest, HttpResponse

# Official Cloudflare Edge IPv4 CIDR blocks
CLOUDFLARE_IPV4_CIDRS: List[ipaddress.IPv4Network] = [
    ipaddress.ip_network("173.245.48.0/20"),
    ipaddress.ip_network("103.21.244.0/22"),
    ipaddress.ip_network("103.22.200.0/22"),
    ipaddress.ip_network("103.31.4.0/22"),
    ipaddress.ip_network("141.101.64.0/18"),
    ipaddress.ip_network("108.162.192.0/18"),
    ipaddress.ip_network("190.93.240.0/20"),
    ipaddress.ip_network("188.114.96.0/20"),
    ipaddress.ip_network("197.234.240.0/22"),
    ipaddress.ip_network("198.41.128.0/17"),
    ipaddress.ip_network("162.158.0.0/15"),
    ipaddress.ip_network("104.16.0.0/13"),
    ipaddress.ip_network("104.24.0.0/14"),
    ipaddress.ip_network("172.64.0.0/13"),
    ipaddress.ip_network("131.0.72.0/22"),
]

# Official Cloudflare Edge IPv6 CIDR blocks
CLOUDFLARE_IPV6_CIDRS: List[ipaddress.IPv6Network] = [
    ipaddress.ip_network("2400:cb00::/32"),
    ipaddress.ip_network("2606:4700::/32"),
    ipaddress.ip_network("2803:f800::/32"),
    ipaddress.ip_network("2405:b500::/32"),
    ipaddress.ip_network("2405:8100::/32"),
    ipaddress.ip_network("2a06:98c0::/29"),
    ipaddress.ip_network("2c0f:f248::/32"),
]

# Local and test networks permitted for internal proxying in dev/test
LOCAL_TRUSTED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]

ALL_TRUSTED_NETWORKS = CLOUDFLARE_IPV4_CIDRS + CLOUDFLARE_IPV6_CIDRS + LOCAL_TRUSTED_NETWORKS


def is_trusted_peer(host: str) -> bool:
    """Checks whether the immediate socket connection peer originates from trusted edge CIDRs."""
    if host in ("testclient", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in net for net in ALL_TRUSTED_NETWORKS)
    except ValueError:
        return False


def resolve_client_ip(request: HttpRequest) -> str:
    """
    Extracts real client IP respecting Cloudflare edge trust boundaries.
    Prevents header spoofing: only evaluates CF-Connecting-IP / X-Forwarded-For
    if immediate peer IP is within trusted CIDRs.
    """
    peer_host = request.META.get("REMOTE_ADDR", "127.0.0.1")

    if is_trusted_peer(peer_host):
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip:
            cleaned = cf_ip.strip()
            try:
                ipaddress.ip_address(cleaned)
                return cleaned
            except ValueError:
                pass

        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            first_ip = xff.split(",")[0].strip()
            try:
                ipaddress.ip_address(first_ip)
                return first_ip
            except ValueError:
                pass

    return peer_host


class CloudflareProxyMiddleware:
    """
    Middleware validating reverse-proxy edge headers from Cloudflare.
    Populates request.client_ip, request.cf_ray, and request.request_id.
    Injects tracing headers (X-Request-ID, CF-Ray) into all outgoing HTTP responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        client_ip = resolve_client_ip(request)
        request.client_ip = client_ip
        cf_ray = request.META.get("HTTP_CF_RAY")
        request.cf_ray = cf_ray

        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)

        response["X-Request-ID"] = request_id
        if cf_ray:
            response["CF-Ray"] = cf_ray

        return response


DEFAULT_SECURITY_HEADERS: Dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    ),
    "X-XSS-Protection": "0",
}


class SecurityHeadersMiddleware:
    """
    Middleware enforcing strict HTTP security headers across all responses.
    Provides MitM defense (HSTS), clickjacking mitigation (X-Frame-Options), MIME-sniffing
    prevention (X-Content-Type-Options), referrer information protection, and CSP enforcement.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.headers = dict(DEFAULT_SECURITY_HEADERS)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        for header_name, header_value in self.headers.items():
            response[header_name] = header_value
        return response


class InMemoryRateLimiter:
    """
    In-memory rate limiter tracking consecutive failure attempts.
    Conforms to Ponytail Ultra: leverages Python standard library data structures
    without requiring Redis or external caching infrastructure.
    """

    def __init__(self, max_failures: int = 5, block_duration_seconds: int = 900) -> None:
        self.max_failures = max_failures
        self.block_duration_seconds = block_duration_seconds
        self._failures: Dict[str, List[float]] = {}
        self._blocked: Dict[str, float] = {}

    def is_blocked(self, key: str) -> bool:
        """Determines whether the client key is currently blocked."""
        now = time.time()
        blocked_until = self._blocked.get(key)
        if blocked_until is not None:
            if now < blocked_until:
                return True
            else:
                del self._blocked[key]
                self._failures.pop(key, None)
                return False
        return False

    def record_failure(self, key: str) -> None:
        """Records a failed attempt. If failures reach max_failures, blocks the key."""
        now = time.time()
        window_start = now - self.block_duration_seconds
        failures = [t for t in self._failures.get(key, []) if t >= window_start]
        failures.append(now)
        self._failures[key] = failures

        if len(failures) >= self.max_failures:
            self._blocked[key] = now + self.block_duration_seconds

    def reset(self, key: str) -> None:
        """Clears failure counts and unblocks the key (called upon successful authentication)."""
        self._failures.pop(key, None)
        self._blocked.pop(key, None)

    def clear(self) -> None:
        """Clears all rate limit state across all keys (for test suite hygiene)."""
        self._failures.clear()
        self._blocked.clear()


login_rate_limiter = InMemoryRateLimiter(max_failures=5, block_duration_seconds=900)


class LoginRateLimitMiddleware:
    """
    Middleware intercepting /auth/login POST requests to guard against credential brute-forcing.
    Enforces a hard block of HTTP 429 after 5 consecutive failed login attempts.
    """

    def __init__(self, get_response, limiter: InMemoryRateLimiter = login_rate_limiter):
        self.get_response = get_response
        self.limiter = limiter

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path_info.rstrip("/")
        if path in ("/auth/login", "/api/v1/auth/login") and request.method == "POST":
            client_ip = getattr(request, "client_ip", None) or resolve_client_ip(request)

            if self.limiter.is_blocked(client_ip):
                response = JsonResponse(
                    {
                        "detail": "Too many failed login attempts. Account temporarily locked. Please try again later."
                    },
                    status=429,
                )
                response["Retry-After"] = str(self.limiter.block_duration_seconds)
                return response

            response = self.get_response(request)

            if response.status_code == 401:
                self.limiter.record_failure(client_ip)
            elif response.status_code == 200:
                self.limiter.reset(client_ip)

            return response

        return self.get_response(request)
