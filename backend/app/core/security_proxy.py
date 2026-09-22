import ipaddress
import uuid
from typing import List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


def resolve_client_ip(request: Request) -> str:
    """
    Extracts real client IP respecting Cloudflare edge trust boundaries.
    Prevents header spoofing: only evaluates CF-Connecting-IP / X-Forwarded-For
    if immediate peer IP is within trusted CIDRs.
    """
    peer_host = request.client.host if request.client else "127.0.0.1"

    if is_trusted_peer(peer_host):
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            cleaned = cf_ip.strip()
            try:
                ipaddress.ip_address(cleaned)
                return cleaned
            except ValueError:
                pass

        xff = request.headers.get("x-forwarded-for")
        if xff:
            first_ip = xff.split(",")[0].strip()
            try:
                ipaddress.ip_address(first_ip)
                return first_ip
            except ValueError:
                pass

    return peer_host


class CloudflareProxyMiddleware(BaseHTTPMiddleware):
    """
    Middleware validating reverse-proxy edge headers from Cloudflare.
    Populates request.state.client_ip, request.state.cf_ray, and request.state.request_id.
    Injects tracing headers (X-Request-ID, CF-Ray) into all outgoing HTTP responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = resolve_client_ip(request)
        request.state.client_ip = client_ip
        cf_ray = request.headers.get("cf-ray")
        request.state.cf_ray = cf_ray

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        if cf_ray:
            response.headers["CF-Ray"] = cf_ray

        return response
