import socket
import ipaddress
import urllib.parse
import logging

logger = logging.getLogger(__name__)


class SSRFValidationError(ValueError):
    """Raised when a URL violates Anti-SSRF safety constraints."""
    pass


# Explicitly forbidden IP networks and addresses
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 blocked ranges
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls into loopback, private, link-local, or reserved ranges."""
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True

    for network in BLOCKED_IP_NETWORKS:
        if ip in network:
            return True

    return False


def validate_url_anti_ssrf(url: str) -> str:
    """
    Strict Anti-SSRF URL validator:
    1. Ensures scheme is strictly 'http' or 'https'.
    2. Validates hostname exists and parses correctly.
    3. Resolves DNS to all corresponding IP addresses.
    4. Rejects any URL resolving to private, link-local, loopback, or cloud-metadata IP ranges.
    
    Returns the validated URL string or raises SSRFValidationError.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as e:
        raise SSRFValidationError(f"Malformed URL: {e}")

    if parsed.scheme.lower() not in ('http', 'https'):
        raise SSRFValidationError(f"Forbidden scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL lacks a valid hostname.")

    # Check if hostname is directly an IP address
    # Remove bracket notation from IPv6 if present
    clean_host = hostname.strip('[]')
    try:
        direct_ip = ipaddress.ip_address(clean_host)
        if _is_ip_blocked(direct_ip):
            raise SSRFValidationError(f"Target IP {direct_ip} is in a blocked/private range.")
        return url
    except ValueError:
        # Not a direct IP literal; proceed to DNS resolution
        pass

    # Block well-known localhost aliases upfront
    if clean_host.lower() in ('localhost', 'localhost.localdomain', '127.0.0.1', '::1', '0.0.0.0'):
        raise SSRFValidationError(f"Target host '{clean_host}' is a forbidden local address.")

    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        # If DNS fails or host does not resolve, reject for safety
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {e}")
    except Exception as e:
        raise SSRFValidationError(f"DNS lookup error for '{hostname}': {e}")

    if not addr_info:
        raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

    # Verify every resolved IP against blocked networks
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            resolved_ip = ipaddress.ip_address(ip_str)
            if _is_ip_blocked(resolved_ip):
                raise SSRFValidationError(
                    f"Hostname '{hostname}' resolved to blocked private/loopback IP {resolved_ip}."
                )
        except ValueError:
            raise SSRFValidationError(f"Invalid IP address format resolved: {ip_str}")

    return url


def is_safe_url(url: str) -> bool:
    """Convenience boolean helper to check if a URL is safe from SSRF."""
    try:
        validate_url_anti_ssrf(url)
        return True
    except (SSRFValidationError, Exception):
        return False
