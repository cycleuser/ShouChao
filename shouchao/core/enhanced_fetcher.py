"""
Enhanced news fetcher for ShouChao.

Improved reliability with:
- Multiple fetch strategies (RSS, API, web scraping)
- Smart deduplication with content hashing
- Flexible date handling
- Retry with different fetchers
- Better error handling and logging
"""

import logging
import hashlib
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    
    parsed = urlparse(url)
    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_content",
        "utm_term", "ref", "source", "fbclid", "gclid",
    }
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {k: v for k, v in params.items()
                    if k.lower() not in tracking_params}
        query = urlencode(filtered, doseq=True) if filtered else ""
    else:
        query = ""
    normalized = urlunparse((
        parsed.scheme, parsed.netloc, parsed.path.rstrip("/"),
        parsed.params, query, "",
    ))
    return normalized.lower()


def _content_hash(title: str, url: str, date: str = "") -> str:
    """Generate content hash for deduplication."""
    content = f"{title.lower().strip()}|{_normalize_url(url)}|{date}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def _extract_date_from_text(text: str) -> Optional[str]:
    """Try to extract date from text content."""
    patterns = [
        (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
        (r"(\d{2}/\d{2}/\d{4})", "%m/%d/%Y"),
        (r"(\d{4}/\d{2}/\d{2})", "%Y/%m/%d"),
    ]
    for pattern, fmt in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


class EnhancedFetcher:
    """Enhanced news fetcher with multiple strategies."""

    def __init__(self, proxy: Optional[dict] = None, fetch_delay: float = 1.0):
        self.proxy = proxy
        self.fetch_delay = fetch_delay
        self._seen_hashes: set[str] = set()
        self.stats = {
            "fetched": 0,
            "skipped_duplicate": 0,
            "skipped_error": 0,
            "saved": 0,
        }

    def fetch_all_sources(
        self,
        sources: list,
        max_articles: int = 50,
        fetcher_type: str = "requests",
    ) -> list[dict]:
        """Fetch from multiple sources with retry logic.
        
        Args:
            sources: List of NewsSource objects.
            max_articles: Max articles per source.
            fetcher_type: Preferred fetcher type.
            
        Returns:
            List of saved article info dicts.
        """
        from shouchao.core.config import CONFIG, get_proxies
        from shouchao.core.sources import SourceType
        from shouchao.core.rss import fetch_feed
        from shouchao.core.converter import html_to_markdown
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.fetcher import create_fetcher, RateLimiter

        proxy = get_proxies()
        proxy_str = proxy.get("https") if proxy else None
        storage = ArticleStorage()
        rate_limiter = RateLimiter(self.fetch_delay)
        all_articles = []

        for src in sources:
            try:
                articles = self._fetch_single_source(
                    src, max_articles, fetcher_type,
                    proxy_str, rate_limiter, storage,
                )
                all_articles.extend(articles)
            except Exception as e:
                logger.warning(f"Failed to fetch {src.name}: {e}")
                self.stats["skipped_error"] += 1

        logger.info(
            f"Fetch complete: {self.stats['fetched']} fetched, "
            f"{self.stats['skipped_duplicate']} duplicates, "
            f"{self.stats['saved']} saved"
        )
        return all_articles

    def _fetch_single_source(
        self, src, max_articles: int, fetcher_type: str,
        proxy_str: Optional[str], rate_limiter, storage,
    ) -> list[dict]:
        """Fetch articles from a single source."""
        from shouchao.core.sources import SourceType
        from shouchao.core.rss import fetch_feed
        from shouchao.core.converter import html_to_markdown
        from shouchao.core.fetcher import create_fetcher

        articles = []
        article_urls = []

        # Strategy 1: RSS feed (most reliable)
        if src.source_type == SourceType.RSS and src.rss_url:
            article_urls = self._fetch_rss(src, max_articles)

        # Strategy 2: Web scraping fallback
        if not article_urls:
            article_urls = self._fetch_web(src, max_articles, fetcher_type, proxy_str, rate_limiter)

        # Fetch each article
        for info in article_urls[:max_articles]:
            url = info["url"]
            title = info.get("title", "")
            date = info.get("date", datetime.now().strftime("%Y-%m-%d"))

            # Check deduplication
            content_h = _content_hash(title, url, date)
            if content_h in self._seen_hashes:
                self.stats["skipped_duplicate"] += 1
                continue

            if storage.article_exists(src.language, src.name, date, title):
                self.stats["skipped_duplicate"] += 1
                self._seen_hashes.add(content_h)
                continue

            # Fetch article content
            rate_limiter.wait(url)
            html, err = self._fetch_url(url, fetcher_type, proxy_str)
            if err or not html:
                logger.debug(f"Failed to fetch article: {url}")
                self.stats["skipped_error"] += 1
                continue

            # Convert to markdown
            try:
                md_content, meta = html_to_markdown(html, url)
            except Exception as e:
                logger.warning(f"Conversion failed for {url}: {e}")
                continue

            # Use extracted title if better
            if meta.get("title") and len(meta["title"]) > len(title):
                title = meta["title"]

            # Add source metadata
            meta["website"] = src.name
            meta["language"] = src.language
            meta["category"] = ", ".join(src.category) if src.category else ""

            # Rebuild front matter
            from shouchao.core.converter import format_front_matter
            meta_copy = dict(meta)
            meta_copy["website"] = src.name
            meta_copy["language"] = src.language
            if "category" not in meta_copy:
                meta_copy["category"] = ", ".join(src.category)

            # Replace front matter if exists
            if md_content.startswith("---"):
                end = md_content.find("---", 3)
                if end > 0:
                    body = md_content[end + 3:]
                    md_content = format_front_matter(meta_copy) + body

            # Save article
            try:
                path = storage.save_article(
                    src.language, src.name, date, title, md_content,
                )
                self._seen_hashes.add(content_h)
                self.stats["saved"] += 1
                articles.append({
                    "path": str(path),
                    "title": title,
                    "source": src.name,
                    "language": src.language,
                    "date": date,
                    "url": url,
                })
            except Exception as e:
                logger.warning(f"Failed to save article: {e}")
                self.stats["skipped_error"] += 1

        self.stats["fetched"] += len(article_urls)
        return articles

    def _fetch_rss(self, src, max_articles: int) -> list[dict]:
        """Fetch article URLs from RSS feed."""
        from shouchao.core.rss import fetch_feed
        from shouchao.core.config import get_proxies

        proxy = get_proxies()
        try:
            entries = fetch_feed(src.rss_url, proxy=proxy)
            urls = []
            for entry in entries[:max_articles]:
                if entry.url and entry.title:
                    urls.append({
                        "url": entry.url,
                        "title": entry.title,
                        "date": entry.date_str,
                    })
            logger.debug(f"RSS {src.name}: found {len(urls)} articles")
            return urls
        except Exception as e:
            logger.warning(f"RSS fetch failed for {src.name}: {e}")
            return []

    def _fetch_web(
        self, src, max_articles: int, fetcher_type: str,
        proxy_str: Optional[str], rate_limiter,
    ) -> list[dict]:
        """Fetch article URLs from web page."""
        from shouchao.core.fetcher import create_fetcher
        from bs4 import BeautifulSoup

        rate_limiter.wait(src.url)
        html, err = self._fetch_url(src.url, fetcher_type, proxy_str)
        if err or not html:
            return []

        try:
            soup = BeautifulSoup(html, "html.parser")
            links = self._extract_article_links(
                soup, src.url, src.article_selector
            )
            today = datetime.now().strftime("%Y-%m-%d")
            urls = []
            for link_url, link_title in links[:max_articles]:
                urls.append({
                    "url": link_url,
                    "title": link_title or "Untitled",
                    "date": today,
                })
            logger.debug(f"Web {src.name}: found {len(urls)} articles")
            return urls
        except Exception as e:
            logger.warning(f"Web extraction failed for {src.name}: {e}")
            return []

    def _fetch_url(
        self, url: str, fetcher_type: str, proxy_str: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        """Fetch URL with fallback chain."""
        from shouchao.core.fetcher import create_fetcher

        # Try preferred fetcher first
        fetcher = create_fetcher(fetcher_type, proxy=proxy_str, timeout=20)
        try:
            html, err = fetcher.fetch(url)
            if html:
                return html, None
        except Exception:
            pass
        finally:
            fetcher.close()

        # Fallback to requests
        if fetcher_type != "requests":
            fetcher = create_fetcher("requests", proxy=proxy_str, timeout=20)
            try:
                html, err = fetcher.fetch(url)
                if html:
                    return html, None
            except Exception:
                pass
            finally:
                fetcher.close()

        return None, "All fetchers failed"

    def _extract_article_links(
        self, soup, base_url: str, selector: Optional[str] = None,
    ) -> list[tuple[str, str]]:
        """Extract article links from listing page."""
        links = []
        seen = set()

        if selector:
            for el in soup.select(selector):
                a = el if el.name == "a" else el.find("a")
                if a and a.get("href"):
                    url = urljoin(base_url, a["href"])
                    title = a.get_text(strip=True)
                    if url not in seen:
                        seen.add(url)
                        links.append((url, title))
            return links

        base_domain = urlparse(base_url).netloc
        skip_patterns = (
            "/tag/", "/category/", "/author/", "/page/",
            "/search", "/login", "/register", "/about",
            "/contact", "/privacy", "/terms", "#",
            "javascript:", "mailto:", "tel:",
        )
        skip_extensions = (
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
            ".pdf", ".mp4", ".mp3", ".zip", ".css", ".js",
        )

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(p in href.lower() for p in skip_patterns):
                continue
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            if parsed.netloc != base_domain:
                continue
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                continue
            path = parsed.path.strip("/")
            if path.count("/") < 1 and len(path) < 10:
                continue
            title = a.get_text(strip=True)
            if len(title) < 5:
                continue
            if url not in seen:
                seen.add(url)
                links.append((url, title))

        return links

    def get_stats(self) -> dict:
        """Return fetch statistics."""
        return dict(self.stats)
