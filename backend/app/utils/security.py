import ipaddress
import socket
from urllib.parse import urlparse
from backend.app.core.errors import SSRFSecurityError


def validate_url_safety(url_str: str) -> None:
    """
    Validates URL safety and blocks SSRF attempts:
    - Only http and https schemes allowed.
    - Prohibits loopback, private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8).
    - Prohibits link-local / cloud metadata (169.254.169.254).
    """
    if not url_str:
        return

    parsed = urlparse(url_str)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SSRFSecurityError(f"Unsupported URL scheme: {parsed.scheme}. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("Invalid URL target without valid hostname")

    if hostname.lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        raise SSRFSecurityError("Access to localhost / loopback addresses is strictly prohibited by security policy.")

    # Resolve IP address to detect internal / private addresses
    try:
        ip_addr_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_addr_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise SSRFSecurityError(f"Access to private or reserved IP address ({ip_addr_str}) is prohibited.")
    except socket.gaierror:
        # If hostname cannot be resolved, allow external DNS check or raise
        pass
