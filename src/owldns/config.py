from typing import Any

# Global configuration dictionary
# This will be populated by the CLI when a config file is loaded.
config: dict[str, Any] = {}


def update_config(new_config: dict[str, Any]) -> None:
    """Recursively updates the global config."""
    def merge(target, source):
        for k, v in source.items():
            if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                merge(target[k], v)
            else:
                target[k] = v
    merge(config, new_config)
