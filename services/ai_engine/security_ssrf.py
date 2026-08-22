import socket
import ipaddress
import urllib.parse
import logging

logger = logging.getLogger("ai_engine.security_ssrf")


class SSRFValidationError(ValueError):
    """Raised when a URL violates Anti-SSRF safety constraints."""
    pass


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
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
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
    """Validate URL against SSRF attacks before downloading content."""
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

    clean_host = hostname.strip('[]')
    try:
        direct_ip = ipaddress.ip_address(clean_host)
        if _is_ip_blocked(direct_ip):
            raise SSRFValidationError(f"Target IP {direct_ip} is in a blocked/private range.")
        return url
    except ValueError:
        pass

    if clean_host.lower() in ('localhost', 'localhost.localdomain', '127.0.0.1', '::1', '0.0.0.0'):
        raise SSRFValidationError(f"Target host '{clean_host}' is a forbidden local address.")

    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {e}")
    except Exception as e:
        raise SSRFValidationError(f"DNS lookup error for '{hostname}': {e}")

    if not addr_info:
        raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

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
    try:
        validate_url_anti_ssrf(url)
        return True
    except (SSRFValidationError, Exception):
        return False
