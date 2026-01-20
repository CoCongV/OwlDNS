from typing import TypeAlias, TypedDict

# DNSDict is the core dictionary structure for storing DNS records.
# Key: String representing the domain name (e.g., "example.com" or "*.local").
# Value: List of strings containing all IP addresses associated with the domain (supports mixed IPv4 and IPv6).
DNSDict: TypeAlias = dict[str, list[str]]


class UpstreamServer(TypedDict):
    """Represents a parsed upstream DNS server configuration."""
    address: str | None
    group: str | None
    proxy: str | None
