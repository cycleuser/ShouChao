"""
Configuration management for ShouChao.

Provides Config dataclass, path resolution, and JSON persistence.
Compatible with GangDan's configuration pattern.
"""

import json
import os
import locale
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Resolve data directory: env -> ~/.shouchao -> ./data."""
    env = os.environ.get("SHOUCHAO_DATA_DIR")
    if env:
        return Path(env)
    home_dir = Path.home() / ".shouchao"
    dev_dir = Path(__file__).resolve().parent.parent.parent / "data"
    if dev_dir.exists() and (dev_dir / "shouchao_config.json").exists():
        return dev_dir
    return home_dir


DATA_DIR: Path = _get_data_dir()
NEWS_DIR: Path = DATA_DIR / "news"
CHROMA_DIR: Path = DATA_DIR / "chroma"
BRIEFINGS_DIR: Path = DATA_DIR / "briefings"
LOGS_DIR: Path = DATA_DIR / "logs"
CONFIG_FILE: Path = DATA_DIR / "shouchao_config.json"
CUSTOM_SOURCES_FILE: Path = DATA_DIR / "custom_sources.json"


@dataclass
class Config:
    """Application configuration."""
    ollama_url: str = "http://localhost:11434"
    chat_model: str = ""
    embedding_model: str = ""
    language: str = "zh"
    proxy_mode: str = "none"  # "none", "system", "manual"
    proxy_http: str = ""
    proxy_https: str = ""
    fetch_delay: float = 1.0
    default_fetcher: str = "requests"  # "requests", "curl", "browser", "playwright"
    vector_db_type: str = "chroma"  # "chroma", "memory"
    top_k: int = 15
    chunk_size: int = 800
    chunk_overlap: int = 150
    max_context_tokens: int = 3000
    web_port: int = 5001
    web_host: str = "0.0.0.0"


def _detect_language() -> str:
    """Auto-detect UI language from system locale."""
    try:
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
    except Exception:
        loc = os.environ.get("LANG", "")
    code = loc.lower()
    lang_map = {
        "zh": "zh", "cn": "zh", "ja": "ja", "jp": "ja",
        "ko": "ko", "kr": "ko", "fr": "fr", "de": "de",
        "ru": "ru", "it": "it", "es": "es", "pt": "pt",
    }
    for prefix, lang in lang_map.items():
        if code.startswith(prefix):
            return lang
    return "en"


CONFIG = Config()


def load_config() -> Config:
    """Load configuration from JSON file."""
    global CONFIG
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in data.items():
                if hasattr(CONFIG, k):
                    setattr(CONFIG, k, v)
            logger.debug("Config loaded from %s", CONFIG_FILE)
        except Exception as e:
            logger.warning("Failed to load config: %s", e)
    else:
        CONFIG.language = _detect_language()
    return CONFIG


def save_config(config: Optional[Config] = None) -> None:
    """Save configuration to JSON file."""
    cfg = config or CONFIG
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_FILE.write_text(
            json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug("Config saved to %s", CONFIG_FILE)
    except Exception as e:
        logger.warning("Failed to save config: %s", e)


def get_proxies() -> Optional[dict]:
    """Resolve proxy settings based on config."""
    if CONFIG.proxy_mode == "system":
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if http_proxy or https_proxy:
            return {
                "http": http_proxy or "",
                "https": https_proxy or http_proxy or "",
            }
        return None
    elif CONFIG.proxy_mode == "manual":
        if CONFIG.proxy_http or CONFIG.proxy_https:
            return {
                "http": CONFIG.proxy_http,
                "https": CONFIG.proxy_https or CONFIG.proxy_http,
            }
        return None
    return None


def ensure_dirs() -> None:
    """Create all data directories if they don't exist."""
    for d in (DATA_DIR, NEWS_DIR, CHROMA_DIR, BRIEFINGS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
