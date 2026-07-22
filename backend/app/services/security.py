"""Security utilities: SSRF protection, URL validation."""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str) -> str:
    """Validate a URL for SSRF safety. Returns normalized URL or raises ValueError."""
    # Auto-prepend https:// if no scheme present
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme must be http or https, got {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL must have a hostname")

    # Resolve DNS and check for private IPs
    try:
        ips = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")

    for ip_info in ips:
        ip_str = ip_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in PRIVATE_NETWORKS:
            if ip in network:
                raise ValueError(f"URL resolves to private IP: {ip_str}")

    # Reconstruct normalized URL
    scheme = parsed.scheme
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/"
    return f"{scheme}://{parsed.hostname}{port}{path}"


def get_safe_client() -> httpx.AsyncClient:
    """Return an httpx client configured for safe crawling."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True,
        max_redirects=3,
        headers={"User-Agent": "WebPulseAssessmentBot/1.0 (+https://webpulsehq.com)"},
    )
