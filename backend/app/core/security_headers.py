from typing import Optional, Dict
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

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
    High-performance ASGI middleware enforcing strict HTTP security headers across all responses.
    Provides MitM defense (HSTS), clickjacking mitigation (X-Frame-Options), MIME-sniffing
    prevention (X-Content-Type-Options), referrer information protection, and CSP enforcement.
    """

    def __init__(
        self,
        app: ASGIApp,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.app = app
        self.headers = dict(DEFAULT_SECURITY_HEADERS)
        if custom_headers:
            self.headers.update(custom_headers)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for header_name, header_value in self.headers.items():
                    headers[header_name] = header_value
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
