from __future__ import annotations
import logging
import sys
from owldns.types import DNSDict

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
