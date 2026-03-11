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
    proxy_socks5: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
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
        all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")
        if http_proxy or https_proxy or all_proxy:
            return {
                "http": http_proxy or all_proxy or "",
                "https": https_proxy or http_proxy or all_proxy or "",
            }
        return None
    elif CONFIG.proxy_mode == "manual":
        proxies = {}
        
        # Handle HTTP/HTTPS proxy
        if CONFIG.proxy_http:
            proxies["http"] = _add_auth_to_proxy(CONFIG.proxy_http, CONFIG.proxy_username, CONFIG.proxy_password)
        if CONFIG.proxy_https:
            proxies["https"] = _add_auth_to_proxy(CONFIG.proxy_https, CONFIG.proxy_username, CONFIG.proxy_password)
        
        # Handle SOCKS5 proxy
        if CONFIG.proxy_socks5:
            socks_url = _add_auth_to_proxy(CONFIG.proxy_socks5, CONFIG.proxy_username, CONFIG.proxy_password, socks=True)
            if "http" not in proxies:
                proxies["http"] = socks_url
            if "https" not in proxies:
                proxies["https"] = socks_url
        
        # Fallback: use http for https if https not set
        if "http" in proxies and "https" not in proxies:
            proxies["https"] = proxies["http"]
        if "https" in proxies and "http" not in proxies:
            proxies["http"] = proxies["https"]
            
        return proxies if proxies else None
    return None


def _add_auth_to_proxy(proxy_url: str, username: str = "", password: str = "", socks: bool = False) -> str:
    """Add authentication to proxy URL if credentials are provided."""
    if not username or not password:
        return proxy_url
    
    # Parse the proxy URL
    from urllib.parse import urlparse, urlunparse
    
    if not proxy_url.startswith(("http://", "https://", "socks5://", "socks5h://")):
        if socks:
            proxy_url = f"socks5://{proxy_url}"
        else:
            proxy_url = f"http://{proxy_url}"
    
    parsed = urlparse(proxy_url)
    
    # Reconstruct with auth
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    
    auth_netloc = f"{username}:{password}@{netloc}"
    
    new_parsed = parsed._replace(netloc=auth_netloc)
    return urlunparse(new_parsed)


def get_proxy_for_requests() -> Optional[dict]:
    """Get proxy dict formatted for requests library."""
    return get_proxies()


def get_proxy_string() -> Optional[str]:
    """Get a single proxy string for libraries that need it (like curl_cffi)."""
    proxies = get_proxies()
    if proxies:
        return proxies.get("https") or proxies.get("http")
    return None


def test_proxy_connection(test_url: str = "https://www.google.com") -> dict:
    """Test if proxy connection works."""
    import requests
    from datetime import datetime
    
    start_time = datetime.now()
    proxies = get_proxies()
    
    result = {
        "proxy_mode": CONFIG.proxy_mode,
        "proxy_used": proxies is not None,
        "success": False,
        "response_time_ms": 0,
        "error": None,
    }
    
    if CONFIG.proxy_mode == "none":
        result["error"] = "No proxy configured"
        return result
    
    try:
        resp = requests.get(test_url, proxies=proxies, timeout=10)
        result["success"] = True
        result["status_code"] = resp.status_code
    except requests.exceptions.ProxyError as e:
        result["error"] = f"Proxy error: {e}"
    except requests.exceptions.ConnectTimeout:
        result["error"] = "Connection timeout"
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL error: {e}"
    except Exception as e:
        result["error"] = str(e)
    finally:
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result["response_time_ms"] = int(elapsed)
    
    return result


def ensure_dirs() -> None:
    """Create all data directories if they don't exist."""
    for d in (DATA_DIR, NEWS_DIR, CHROMA_DIR, BRIEFINGS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
