"""
ShouChao core modules.

Exports configuration, fetching, conversion, storage, indexing,
analysis, and briefing components.
"""

from shouchao.core.config import (
    Config,
    CONFIG,
    CONFIG_FILE,
    DATA_DIR,
    NEWS_DIR,
    CHROMA_DIR,
    BRIEFINGS_DIR,
    LOGS_DIR,
    load_config,
    save_config,
    get_proxies,
)

__all__ = [
    "Config",
    "CONFIG",
    "CONFIG_FILE",
    "DATA_DIR",
    "NEWS_DIR",
    "CHROMA_DIR",
    "BRIEFINGS_DIR",
    "LOGS_DIR",
    "load_config",
    "save_config",
    "get_proxies",
]
