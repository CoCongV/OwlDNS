import logging
import sys

# Global logger for the owldns package
logger = logging.getLogger("owldns")


def setup_logger(level="INFO"):
    """
    Configures the project-wide logger.
    """
    logger = logging.getLogger("owldns")
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


def load_hosts(file_path):
    """
    Parses a hosts-style file and returns a dictionary of records.
    Standard format: IP domain1 [domain2 ...]
    """
    records = {}
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
                        records[domain] = ip
    except Exception as e:
        logger.error(
            f"Error loading hosts file {file_path}: {e}")
    return records
