"""
Unified Python API for ShouChao.

All public functions return ToolResult and use keyword-only arguments.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result type for all API functions."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def fetch_news(
    *,
    language: Optional[str] = None,
    source: Optional[str] = None,
    max_articles: int = 50,
    fetcher: str = "requests",
) -> ToolResult:
    """Fetch news articles from configured sources.

    Args:
        language: Filter by language code (e.g. "en", "zh"). None = all.
        source: Specific source name to fetch from. None = all enabled.
        max_articles: Maximum articles to fetch per source.
        fetcher: Fetcher backend ("requests", "curl", "browser", "playwright").

    Returns:
        ToolResult with data={"fetched": N, "articles": [...]}.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config, get_proxies, ensure_dirs
        from shouchao.core.sources import get_sources, SourceType
        from shouchao.core.fetcher import create_fetcher, RateLimiter
        from shouchao.core.rss import fetch_feed
        from shouchao.core.converter import html_to_markdown
        from shouchao.core.storage import ArticleStorage

        load_config()
        ensure_dirs()

        proxy = get_proxies()
        proxy_str = proxy.get("https") if proxy else None

        storage = ArticleStorage()
        rate_limiter = RateLimiter(CONFIG.fetch_delay)

        # Get sources
        sources = get_sources(language=language)
        if source:
            sources = [s for s in sources if s.name.lower() == source.lower()]

        if not sources:
            return ToolResult(
                success=True,
                data={"fetched": 0, "articles": []},
                metadata={"version": __version__},
            )

        http_fetcher = create_fetcher(fetcher, proxy=proxy_str)
        all_articles = []

        logger.info(f"Starting fetch: language={language}, source={source}, max={max_articles}, fetcher={fetcher}")
        
        try:
            for src in sources:
                if len(all_articles) >= max_articles * len(sources):
                    break

                article_urls = []

                # RSS path: discover article URLs
                if src.source_type == SourceType.RSS and src.rss_url:
                    entries = fetch_feed(src.rss_url, proxy=proxy)
                    for entry in entries[:max_articles]:
                        article_urls.append({
                            "url": entry.url,
                            "title": entry.title,
                            "date": entry.date_str,
                        })
                else:
                    # Web path: fetch listing page and discover links
                    rate_limiter.wait(src.url)
                    html, err = http_fetcher.fetch(src.url)
                    if err or not html:
                        continue
                    # Extract article links from listing page
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    links = _extract_article_links(
                        soup, src.url, src.article_selector
                    )
                    from datetime import datetime
                    today = datetime.now().strftime("%Y-%m-%d")
                    for link_url, link_title in links[:max_articles]:
                        article_urls.append({
                            "url": link_url,
                            "title": link_title or "Untitled",
                            "date": today,
                        })

                # Fetch each article
                for info in article_urls:
                    url = info["url"]
                    title = info["title"]
                    date = info["date"]

                    if storage.article_exists(
                        src.language, src.name, date, title
                    ):
                        continue

                    rate_limiter.wait(url)
                    html, err = http_fetcher.fetch(url)
                    if err or not html:
                        continue

                    md_content, meta = html_to_markdown(html, url)

                    # Use extracted title if better
                    if meta.get("title"):
                        title = meta["title"]

                    # Add source metadata
                    meta["website"] = src.name
                    meta["language"] = src.language

                    # Rebuild front matter with updated metadata
                    from shouchao.core.converter import format_front_matter
                    meta_copy = dict(meta)
                    meta_copy["website"] = src.name
                    meta_copy["language"] = src.language
                    if "category" not in meta_copy:
                        meta_copy["category"] = ", ".join(src.category)

                    # Replace front matter
                    if md_content.startswith("---"):
                        end = md_content.find("---", 3)
                        if end > 0:
                            body = md_content[end + 3:]
                            md_content = format_front_matter(meta_copy) + body

                    path = storage.save_article(
                        src.language, src.name, date, title, md_content,
                    )
                    all_articles.append({
                        "path": str(path),
                        "title": title,
                        "source": src.name,
                        "language": src.language,
                        "date": date,
                        "url": url,
                    })
        finally:
            http_fetcher.close()

        return ToolResult(
            success=True,
            data={"fetched": len(all_articles), "articles": all_articles},
            metadata={"version": __version__},
        )

    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def search_news(
    *,
    query: str,
    language: Optional[str] = None,
    top_k: int = 10,
) -> ToolResult:
    """Semantic search across indexed news articles.

    Args:
        query: Search query text.
        language: Filter by language. None = all.
        top_k: Maximum results to return.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        results = indexer.search_news(query, language=language, top_k=top_k)

        return ToolResult(
            success=True,
            data={"results": results, "count": len(results)},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def generate_briefing(
    *,
    briefing_type: str = "daily",
    language: Optional[str] = None,
    categories: Optional[list[str]] = None,
    date: Optional[str] = None,
) -> ToolResult:
    """Generate a news briefing.

    Args:
        briefing_type: "daily", "weekly", or "domain".
        language: Output language code.
        categories: Filter by category tags.
        date: Target date (YYYY-MM-DD). Default: today.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.briefing import BriefingGenerator

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        storage = ArticleStorage()
        generator = BriefingGenerator(ollama, indexer, storage)

        if briefing_type == "weekly":
            chunks = list(generator.generate_weekly(date, language))
        elif briefing_type == "domain" and categories:
            chunks = list(generator.generate_domain(
                categories[0], date_from=date, language=language,
            ))
        else:
            chunks = list(generator.generate_daily(date, language, categories))

        content = "".join(chunks)
        return ToolResult(
            success=True,
            data={"content": content, "type": briefing_type},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def analyze_news(
    *,
    query: str,
    scenario: str = "general",
    language: Optional[str] = None,
) -> ToolResult:
    """Analyze news for a specific scenario.

    Args:
        query: Analysis query.
        scenario: "investment", "immigration", "study_abroad", or "general".
        language: Output language code.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.analyzer import AnalysisEngine

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        engine = AnalysisEngine(ollama, indexer)

        content = engine.analyze_complete(query, scenario, language)
        return ToolResult(
            success=True,
            data={"content": content, "scenario": scenario},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def index_news(
    *,
    directory: Optional[str] = None,
    collection: str = "shouchao_news",
) -> ToolResult:
    """Index news articles into the knowledge base.

    Args:
        directory: Directory to index. Default: NEWS_DIR.
        collection: ChromaDB collection name.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, NEWS_DIR, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        target = directory or str(NEWS_DIR)
        count = indexer.index_directory(target, collection)

        return ToolResult(
            success=True,
            data={"indexed": count, "directory": target, "collection": collection},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def list_sources(
    *,
    language: Optional[str] = None,
    source_type: Optional[str] = None,
) -> ToolResult:
    """List available news sources.

    Args:
        language: Filter by language code.
        source_type: "rss" or "web".
    """
    try:
        from shouchao import __version__
        from shouchao.core.sources import get_sources, SourceType

        st = None
        if source_type:
            st = SourceType(source_type.lower())

        sources = get_sources(language=language, source_type=st)
        data = [s.to_dict() for s in sources]

        return ToolResult(
            success=True,
            data={"sources": data, "count": len(data)},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_article_links(
    soup, base_url: str, selector: Optional[str] = None,
) -> list[tuple[str, str]]:
    """Extract article links from a listing page.

    Returns list of (url, title) tuples.
    """
    from urllib.parse import urljoin, urlparse

    links = []
    seen = set()

    # Use CSS selector if provided
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

    # Heuristic: find article links
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
        # Heuristic: article URLs tend to have longer paths
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
