import time
from typing import Dict, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse


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
        """
        Determines whether the client key is currently blocked.
        """
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
        """
        Records a failed attempt. If failures reach max_failures, blocks the key.
        """
        now = time.time()
        window_start = now - self.block_duration_seconds
        failures = [t for t in self._failures.get(key, []) if t >= window_start]
        failures.append(now)
        self._failures[key] = failures

        if len(failures) >= self.max_failures:
            self._blocked[key] = now + self.block_duration_seconds

    def reset(self, key: str) -> None:
        """
        Clears failure counts and unblocks the key (called upon successful authentication).
        """
        self._failures.pop(key, None)
        self._blocked.pop(key, None)

    def clear(self) -> None:
        """
        Clears all rate limit state across all keys (for test suite hygiene).
        """
        self._failures.clear()
        self._blocked.clear()


# Global singleton rate limiter instance for auth endpoints
login_rate_limiter = InMemoryRateLimiter(max_failures=5, block_duration_seconds=900)


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware intercepting /auth/login POST requests to guard against credential brute-forcing.
    Enforces a hard block of HTTP 429 after 5 consecutive failed login attempts.
    """

    def __init__(self, app, limiter: InMemoryRateLimiter = login_rate_limiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/auth/login", "/api/v1/auth/login") and request.method.upper() == "POST":
            client_ip = request.client.host if request.client else "unknown"

            if self.limiter.is_blocked(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many failed login attempts. Account temporarily locked. Please try again later."
                    },
                    headers={"Retry-After": str(self.limiter.block_duration_seconds)},
                )

            response = await call_next(request)

            if response.status_code == 401:
                self.limiter.record_failure(client_ip)
            elif response.status_code == 200:
                self.limiter.reset(client_ip)

            return response

        return await call_next(request)
