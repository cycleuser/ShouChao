"""
RSS/Atom feed parser for ShouChao.

Provides lightweight news discovery via RSS feeds using feedparser.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse

logger = logging.getLogger(__name__)


@dataclass
class RSSEntry:
    """A single RSS feed entry."""
    title: str
    url: str
    published: Optional[str] = None
    summary: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    categories: list = field(default_factory=list)

    @property
    def date_str(self) -> str:
        """Extract YYYY-MM-DD from published date."""
        if not self.published:
            return datetime.now().strftime("%Y-%m-%d")
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(self.published, fmt)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        return datetime.now().strftime("%Y-%m-%d")

    @property
    def content_hash(self) -> str:
        """Generate a hash for deduplication."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication."""
    parsed = urlparse(url)
    # Strip tracking parameters
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
    # Remove fragment, normalize
    normalized = urlunparse((
        parsed.scheme, parsed.netloc, parsed.path.rstrip("/"),
        parsed.params, query, "",
    ))
    return normalized


def fetch_feed(url: str, proxy: Optional[dict] = None) -> list[RSSEntry]:
    """Parse an RSS/Atom feed and return entries.

    Args:
        url: RSS feed URL
        proxy: Optional proxy dict {"http": ..., "https": ...}

    Returns:
        List of RSSEntry objects
    """
    logger.debug(f"RSS: Fetching feed: {url}")
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return []

    try:
        # feedparser handles proxy via environment; set if needed
        feed = feedparser.parse(url)
    except Exception as e:
        logger.error("Failed to parse feed %s: %s", url, e)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s has errors: %s", url, feed.bozo_exception)
        return []

    logger.debug(f"RSS: Parsed {len(feed.entries)} entries from {url}")
    entries = []
    seen_urls = set()

    for entry in feed.entries:
        link = entry.get("link", "")
        if not link:
            continue

        normalized = _normalize_url(link)
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)

        # Extract published date
        published = None
        for date_field in ("published", "updated", "created"):
            val = entry.get(date_field)
            if val:
                published = val
                break

        # Extract categories
        categories = []
        for tag in entry.get("tags", []):
            term = tag.get("term", "")
            if term:
                categories.append(term.lower())

        entries.append(RSSEntry(
            title=entry.get("title", "").strip(),
            url=link,
            published=published,
            summary=entry.get("summary", ""),
            author=entry.get("author"),
            categories=categories,
        ))

    logger.debug("Parsed %d entries from %s", len(entries), url)
    return entries


def discover_rss(html: str, base_url: str) -> list[str]:
    """Discover RSS/Atom feed URLs from HTML page.

    Args:
        html: HTML content of the page
        base_url: Base URL for resolving relative links

    Returns:
        List of discovered feed URLs
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    feeds = []

    for link in soup.find_all("link", rel=True):
        rel = " ".join(link.get("rel", []))
        link_type = link.get("type", "")
        href = link.get("href", "")

        if not href:
            continue

        if "alternate" in rel and any(
            t in link_type
            for t in ("application/rss+xml", "application/atom+xml",
                      "application/xml", "text/xml")
        ):
            full_url = urljoin(base_url, href)
            feeds.append(full_url)

    return feeds
