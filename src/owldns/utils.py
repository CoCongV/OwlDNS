from __future__ import annotations
import logging
import re
import sys
import tomllib
from owldns.types import DNSDict, UpstreamServer

# Global logger for the owldns package
logger = logging.getLogger("owldns")


def setup_logger(level: str | int = "INFO") -> logging.Logger:
    """
    Configures the project-wide logger.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def load_config(file_path: str) -> dict:
    """Loads and parses a TOML configuration file, processing specialized fields."""
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        # Post-process upstreams if they exist in [run] section
        if "run" in data and isinstance(data["run"], dict):
            upstreams = data["run"].get("upstream")
            if isinstance(upstreams, list):
                parsed_upstreams = []
                for item in upstreams:
                    if isinstance(item, str):
                        parsed = parse_upstream_server(item)
                        # Strictly require address (pattern MUST match 'server ...')
                        if parsed["address"]:
                            parsed_upstreams.append(parsed)
                data["run"]["upstream"] = parsed_upstreams

        return data
    except Exception as e:
        logger.error("Error loading config file %s: %s", file_path, e)
        return {}


def load_hosts(file_path: str) -> DNSDict:
    """
    Parses a hosts-style file and returns a dictionary of records.
    Supports multiple IPs (IPv4 and IPv6) for the same domain.
    """
    records: DNSDict = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    for domain in parts[1:]:
                        if domain not in records:
                            records[domain] = []
                        if ip not in records[domain]:
                            records[domain].append(ip)
    except Exception as e:
        logger.error("Error loading hosts file %s: %s", file_path, e)
    return records


def parse_upstream_server(server_str: str) -> UpstreamServer:
    """
    Parses an upstream server configuration string.
    Format: server <address> [--group <group>] [--proxy <proxy>]
    """
    # Regex to extract address, and optional group/proxy flags
    pattern = (
        r"server\s+(?P<address>[^\s]+)"
        r"(?:\s+--group\s+(?P<group>[^\s]+))?"
        r"(?:\s+--proxy\s+(?P<proxy>[^\s]+))?"
    )
    match = re.search(pattern, server_str)
    if match:
        # Use cast or explicit return to satisfy TypedDict
        return match.groupdict()  # type: ignore

    return {"address": None, "group": None, "proxy": None}
