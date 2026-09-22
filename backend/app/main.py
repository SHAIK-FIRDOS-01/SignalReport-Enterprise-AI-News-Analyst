import os
import logging
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.security_headers import SecurityHeadersMiddleware
from app.core.security.rate_limiter import LoginRateLimitMiddleware
from app.core.security_proxy import CloudflareProxyMiddleware
from app.core.scheduler import start_scheduler, stop_scheduler

from app.api.v1.auth_register import router as auth_register_router
from app.api.v1.auth_login import router as auth_login_router
from app.api.v1.routes_bookmarks import router as bookmarks_router
from app.api.v1.routes_reads import router as reads_router
from app.api.v1.routes_feed import router as feed_router
from app.api.v1.routes_search import router as search_router
from app.api.v1.routes_share import router as share_router

logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup: Initializes background news poller if ENABLE_SCHEDULER is enabled.
    Shutdown: Gracefully cancels and awaits background scheduler task.
    """
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "false").lower() in ("true", "1")
    scheduler_task = None
    if enable_scheduler:
        scheduler_task = start_scheduler()
    yield
    if scheduler_task is not None:
        await stop_scheduler()


app = FastAPI(
    title="SignalReport Enterprise AI News Analyst API",
    description="Production-grade API for SignalReport platform services.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enforce reverse-proxy Cloudflare IP extraction
app.add_middleware(CloudflareProxyMiddleware)

# Enforce strict security headers (HSTS, CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# Enforce brute-force rate limiting on login
app.add_middleware(LoginRateLimitMiddleware)

# Mount API Routers under /api/v1 prefix and root
app.include_router(auth_register_router, prefix="/api/v1")
app.include_router(auth_register_router)
app.include_router(auth_login_router, prefix="/api/v1")
app.include_router(auth_login_router)
app.include_router(bookmarks_router, prefix="/api/v1")
app.include_router(bookmarks_router)
app.include_router(reads_router, prefix="/api/v1")
app.include_router(reads_router)
app.include_router(feed_router, prefix="/api/v1")
app.include_router(feed_router)
app.include_router(search_router, prefix="/api/v1")
app.include_router(search_router)
app.include_router(share_router, prefix="/api/v1")
app.include_router(share_router)


@app.get("/health", tags=["System"])
def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint reporting service operational status.
    """
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global catch-all error boundary returning standard JSON structure
    and preventing internal trace leakage.
    """
    logger.error(
        f"Unhandled error processing {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred. Please try again later."},
    )
