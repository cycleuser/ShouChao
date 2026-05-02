"""
Scheduler for automatic daily preprint fetching.

Provides functions to schedule and manage automatic preprint collection.
Uses threading.Timer for simple scheduling, or APScheduler if available.
"""

import logging
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PreprintScheduler:
    """Manages automatic daily preprint fetching."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
    ):
        if config_path is None:
            from shouchao.core.config import DATA_DIR
            config_path = DATA_DIR / "preprint_schedule.json"

        self._config_path = config_path
        self._config = self._load_config()
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def _load_config(self) -> dict:
        """Load scheduler configuration."""
        if self._config_path.exists():
            try:
                return json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load schedule config: %s", e)
        return {
            "enabled": False,
            "time": "06:00",  # Default: 6 AM
            "servers": ["arxiv", "biorxiv", "medrxiv"],
            "categories": ["cs.AI", "cs.LG", "cs.CL", "q-bio.GN"],
            "keywords": [],
            "max_results": 200,
            "auto_index": True,
            "last_run": None,
            "last_status": None,
        }

    def _save_config(self):
        """Save scheduler configuration."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(
                json.dumps(self._config, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Failed to save schedule config: %s", e)

    def enable(
        self,
        *,
        time: str = "06:00",
        servers: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        max_results: int = 200,
        auto_index: bool = True,
    ):
        """Enable automatic daily fetching.

        Args:
            time: Time to run (HH:MM, 24h format).
            servers: List of servers to fetch from.
            categories: List of categories.
            keywords: Keywords to filter.
            max_results: Max results per server.
            auto_index: Whether to auto-index after fetching.
        """
        self._config["enabled"] = True
        self._config["time"] = time
        if servers:
            self._config["servers"] = servers
        if categories:
            self._config["categories"] = categories
        if keywords is not None:
            self._config["keywords"] = keywords
        self._config["max_results"] = max_results
        self._config["auto_index"] = auto_index
        self._save_config()

        self.start()
        logger.info("Preprint scheduler enabled: daily at %s", time)

    def disable(self):
        """Disable automatic fetching."""
        self._config["enabled"] = False
        self._save_config()
        self.stop()
        logger.info("Preprint scheduler disabled")

    def start(self):
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._schedule_next()
        logger.info("Preprint scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Preprint scheduler stopped")

    def _schedule_next(self):
        """Schedule the next run."""
        if not self._running:
            return

        # Parse target time
        hour, minute = map(int, self._config["time"].split(":"))
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If target is in the past, schedule for tomorrow
        if target <= now:
            target += timedelta(days=1)

        delay = (target - now).total_seconds()
        logger.info("Next preprint fetch scheduled in %.1f hours", delay / 3600)

        self._timer = threading.Timer(delay, self._run_fetch)
        self._timer.daemon = True
        self._timer.start()

    def _run_fetch(self):
        """Execute the fetch job."""
        from shouchao.core.config import get_proxies
        from shouchao.core.preprint import fetch_todays_preprints

        logger.info("Running scheduled preprint fetch...")

        try:
            result = fetch_todays_preprints(
                servers=self._config.get("servers"),
                categories=self._config.get("categories"),
                keywords=self._config.get("keywords") or None,
                max_results=self._config.get("max_results", 200),
                proxy=get_proxies(),
            )

            self._config["last_run"] = datetime.now().isoformat()
            self._config["last_status"] = {
                "success": True,
                "fetched": result["fetched"],
                "saved": result["saved"],
            }
            self._save_config()

            logger.info(
                "Scheduled fetch complete: %d fetched, %d saved",
                result["fetched"], result["saved"],
            )

            # Auto-index if enabled
            if self._config.get("auto_index"):
                self._index_preprints()

        except Exception as e:
            logger.error("Scheduled preprint fetch failed: %s", e)
            self._config["last_run"] = datetime.now().isoformat()
            self._config["last_status"] = {
                "success": False,
                "error": str(e),
            }
            self._save_config()

        # Schedule next run
        if self._running:
            self._schedule_next()

    def _index_preprints(self):
        """Index fetched preprints."""
        try:
            from shouchao.core.config import NEWS_DIR
            from shouchao.core.ollama_client import OllamaClient
            from shouchao.core.indexer import NewsIndexer
            from shouchao.core.config import CONFIG

            ollama = OllamaClient(CONFIG.ollama_url)
            indexer = NewsIndexer(ollama)
            count = indexer.index_directory(str(NEWS_DIR / "en"), "preprints")
            logger.info("Indexed %d preprints", count)
        except Exception as e:
            logger.warning("Failed to index preprints: %s", e)

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "enabled": self._config["enabled"],
            "running": self._running,
            "time": self._config["time"],
            "servers": self._config.get("servers", []),
            "categories": self._config.get("categories", []),
            "last_run": self._config.get("last_run"),
            "last_status": self._config.get("last_status"),
        }


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

_scheduler: Optional[PreprintScheduler] = None


def get_scheduler() -> PreprintScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PreprintScheduler()
    return _scheduler


def enable_scheduler(
    *,
    time: str = "06:00",
    servers: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 200,
    auto_index: bool = True,
):
    """Enable the preprint scheduler."""
    scheduler = get_scheduler()
    scheduler.enable(
        time=time,
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=max_results,
        auto_index=auto_index,
    )


def disable_scheduler():
    """Disable the preprint scheduler."""
    scheduler = get_scheduler()
    scheduler.disable()


def get_scheduler_status() -> dict:
    """Get scheduler status."""
    scheduler = get_scheduler()
    return scheduler.get_status()


def run_manual_fetch(
    *,
    servers: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 200,
    auto_index: bool = True,
) -> dict:
    """Run a manual fetch immediately.

    Args:
        servers: List of servers.
        categories: Categories to fetch.
        keywords: Keywords to filter.
        max_results: Max results per server.
        auto_index: Whether to auto-index.

    Returns:
        Fetch result dict.
    """
    from shouchao.core.config import get_proxies
    from shouchao.core.preprint import fetch_todays_preprints

    result = fetch_todays_preprints(
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=max_results,
        proxy=get_proxies(),
    )

    if auto_index:
        try:
            from shouchao.core.config import NEWS_DIR
            from shouchao.core.ollama_client import OllamaClient
            from shouchao.core.indexer import NewsIndexer
            from shouchao.core.config import CONFIG

            ollama = OllamaClient(CONFIG.ollama_url)
            indexer = NewsIndexer(ollama)
            count = indexer.index_directory(str(NEWS_DIR / "en"), "preprints")
            result["indexed"] = count
        except Exception as e:
            logger.warning("Failed to auto-index: %s", e)
            result["indexed"] = 0

    return result
