"""
Search-based news fetcher for ShouChao.

Fetches latest news by searching the web instead of relying on RSS feeds.
Uses DuckDuckGo, Google News, Bing News, and other search engines to find
current articles, then fetches and converts them to markdown.

Also supports direct scraping of news website listing pages as fallback.
"""

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


# News website listing pages that are reliable
NEWS_SOURCES = {
    "en": [
        {"name": "Reuters", "url": "https://www.reuters.com", "selector": "article a[href*='/article/'], a[href*='/world/'], a[href*='/business/']"},
        {"name": "BBC", "url": "https://www.bbc.com/news", "selector": "a[href*='/news/'][href*='/20'], a[href*='/articles/']"},
        {"name": "CNN", "url": "https://www.cnn.com", "selector": "a[href*='/202'][href*='/20']"},
        {"name": "TechCrunch", "url": "https://techcrunch.com", "selector": "a[href*='/202'][href*='/20'], a.post-block__title"},
        {"name": "The Verge", "url": "https://www.theverge.com", "selector": "a[href*='/202'][href*='/20'], h2 a"},
    ],
    "zh": [
        {"name": "新浪新闻", "url": "https://news.sina.com.cn", "selector": "a[href*='sina.com.cn'][href*='20'], a[href*='/news/']"},
        {"name": "网易新闻", "url": "https://news.163.com", "selector": "a[href*='163.com'][href*='20'], a.news_title"},
        {"name": "腾讯新闻", "url": "https://news.qq.com", "selector": "a[href*='qq.com'][href*='20'], a[href*='/news/']"},
        {"name": "36氪", "url": "https://36kr.com", "selector": "a[href*='36kr.com'][href*='/20'], a.article-item__title"},
        {"name": "澎湃新闻", "url": "https://www.thepaper.cn", "selector": "a[href*='thepaper.cn'][href*='20'], a[href*='/detail/']"},
    ],
    "ja": [
        {"name": "NHK", "url": "https://www3.nhk.or.jp/news/", "selector": "a[href*='/20'], a[href*='news']"},
        {"name": "朝日新闻", "url": "https://www.asahi.com", "selector": "a[href*='/articles/'], a[href*='/20']"},
    ],
}

# News search queries by language
NEWS_QUERIES = {
    "zh": [
        "今日新闻",
        "最新科技新闻",
        "最新经济新闻",
        "今日要闻",
    ],
    "en": [
        "today news",
        "latest technology news",
        "latest business news",
        "breaking news today",
    ],
    "ja": [
        "今日のニュース",
        "最新技術ニュース",
    ],
    "fr": [
        "actualités aujourd'hui",
        "dernières nouvelles",
    ],
    "de": [
        "heute nachrichten",
        "aktuelle news",
    ],
    "ko": [
        "오늘 뉴스",
        "최신 뉴스",
    ],
    "ru": [
        "сегодня новости",
        "последние новости",
    ],
    "es": [
        "noticias de hoy",
        "últimas noticias",
    ],
    "pt": [
        "notícias de hoje",
        "últimas notícias",
    ],
    "it": [
        "notizie di oggi",
        "ultime notizie",
    ],
}

# Category-specific queries
CATEGORY_QUERIES = {
    "technology": {
        "zh": "最新科技新闻 AI 人工智能",
        "en": "latest technology news AI artificial intelligence",
        "ja": "最新技術ニュース AI",
    },
    "economy": {
        "zh": "最新经济新闻 财经",
        "en": "latest business news economy finance",
        "ja": "最新経済ニュース",
    },
    "science": {
        "zh": "最新科学新闻 研究",
        "en": "latest science news research",
        "ja": "最新科学ニュース",
    },
    "politics": {
        "zh": "最新政治新闻",
        "en": "latest political news",
        "ja": "最新政治ニュース",
    },
}


class SearchNewsFetcher:
    """Fetches news by searching the web instead of RSS."""

    def __init__(
        self,
        proxy: Optional[dict] = None,
        fetch_delay: float = 1.0,
        max_articles_per_query: int = 10,
    ):
        self.proxy = proxy
        self.proxy_str = proxy.get("https") if proxy else None
        self.fetch_delay = fetch_delay
        self.max_articles = max_articles_per_query
        self.stats = {
            "searches": 0,
            "urls_found": 0,
            "articles_fetched": 0,
            "articles_saved": 0,
            "errors": 0,
        }

    def fetch_news_by_search(
        self,
        language: str = "en",
        categories: Optional[list[str]] = None,
        max_articles: int = 50,
        date_range: str = "d",  # d=day, w=week, m=month
    ) -> list[dict]:
        """Fetch news by web search.
        
        Args:
            language: Language code.
            categories: List of categories to search.
            max_articles: Maximum total articles.
            date_range: Date filter (d/w/m).
            
        Returns:
            List of saved article info dicts.
        """
        from shouchao.core.config import ensure_dirs
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.web_search import WebSearchEngine
        from shouchao.core.converter import html_to_markdown
        from shouchao.core.fetcher import create_fetcher, RateLimiter

        ensure_dirs()
        storage = ArticleStorage()
        rate_limiter = RateLimiter(self.fetch_delay)
        http_fetcher = create_fetcher("requests", proxy=self.proxy_str)
        
        all_articles = []
        seen_urls = set()

        # Try search engine first
        try:
            search_engine = WebSearchEngine(proxy=self.proxy_str)
            queries = self._build_queries(language, categories)
            
            logger.info(f"Search news: language={language}, queries={len(queries)}, max={max_articles}")

            for query in queries:
                if len(all_articles) >= max_articles:
                    break

                self.stats["searches"] += 1
                
                try:
                    response = search_engine.search(
                        query=query,
                        engines=["duckduckgo"],
                        num_results=self.max_articles,
                        language=language,
                        date_range=date_range,
                    )
                    
                    if response.error:
                        logger.warning(f"Search failed for '{query}': {response.error}")
                        continue

                    logger.info(f"Search '{query}': found {len(response.results)} results")
                    self.stats["urls_found"] += len(response.results)

                    # Fetch each article
                    for result in response.results:
                        if len(all_articles) >= max_articles:
                            break

                        url = result.url
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)

                        article = self._fetch_and_save(
                            url, result.title, language, storage, 
                            rate_limiter, http_fetcher, seen_urls,
                        )
                        if article:
                            all_articles.append(article)

                except Exception as e:
                    logger.error(f"Search error for '{query}': {e}")
                    self.stats["errors"] += 1

        except Exception as e:
            logger.warning(f"Search engine unavailable, falling back to direct scraping: {e}")

        # Fallback: scrape news websites directly
        if len(all_articles) < max_articles:
            logger.info(f"Only {len(all_articles)} articles from search, trying direct scraping...")
            articles_from_scraping = self._scrape_news_sites(
                language, max_articles - len(all_articles),
                storage, rate_limiter, http_fetcher, seen_urls,
            )
            all_articles.extend(articles_from_scraping)

        http_fetcher.close()
        
        logger.info(
            f"Search news complete: {self.stats['searches']} searches, "
            f"{self.stats['urls_found']} URLs found, "
            f"{self.stats['articles_fetched']} fetched, "
            f"{self.stats['articles_saved']} saved"
        )
        return all_articles

    def _scrape_news_sites(
        self, language: str, max_articles: int,
        storage, rate_limiter, http_fetcher, seen_urls: set,
    ) -> list[dict]:
        """Fallback: scrape news website listing pages directly."""
        from bs4 import BeautifulSoup
        from shouchao.core.converter import html_to_markdown

        sources = NEWS_SOURCES.get(language, NEWS_SOURCES.get("en", []))
        articles = []

        for source in sources:
            if len(articles) >= max_articles:
                break

            try:
                rate_limiter.wait(source["url"])
                html, err = http_fetcher.fetch(source["url"])
                if err or not html:
                    continue

                soup = BeautifulSoup(html, "html.parser")
                links = self._extract_article_links(soup, source["url"], source.get("selector"))
                
                today = datetime.now().strftime("%Y-%m-%d")
                
                for url, title in links[:15]:
                    if len(articles) >= max_articles:
                        break
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    article = self._fetch_and_save(
                        url, title, language, storage,
                        rate_limiter, http_fetcher, seen_urls,
                        source_name=source["name"],
                    )
                    if article:
                        articles.append(article)

            except Exception as e:
                logger.warning(f"Failed to scrape {source['name']}: {e}")
                self.stats["errors"] += 1

        return articles

    def _fetch_and_save(
        self, url: str, title: str, language: str,
        storage, rate_limiter, http_fetcher, seen_urls: set,
        source_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Fetch article content and save to storage."""
        from shouchao.core.converter import html_to_markdown, format_front_matter

        try:
            rate_limiter.wait(url)
            html, err = http_fetcher.fetch(url)
            if err or not html:
                self.stats["errors"] += 1
                return None

            self.stats["articles_fetched"] += 1

            # Convert to markdown
            try:
                md_content, meta = html_to_markdown(html, url)
            except Exception as e:
                logger.warning(f"Conversion failed for {url}: {e}")
                return None

            # Extract metadata
            title = meta.get("title", title)
            date = self._extract_date(meta)
            website = source_name or self._extract_website(url)

            if not title or len(title) < 5:
                return None

            # Check if already exists
            if storage.article_exists(language, website, date, title):
                return None

            # Add source metadata
            meta["website"] = website
            meta["language"] = language

            # Rebuild front matter
            meta_copy = dict(meta)
            meta_copy["website"] = website
            meta_copy["language"] = language

            if md_content.startswith("---"):
                end = md_content.find("---", 3)
                if end > 0:
                    body = md_content[end + 3:]
                    md_content = format_front_matter(meta_copy) + body

            # Save article
            try:
                path = storage.save_article(
                    language, website, date, title, md_content,
                )
                self.stats["articles_saved"] += 1
                return {
                    "path": str(path),
                    "title": title,
                    "source": website,
                    "language": language,
                    "date": date,
                    "url": url,
                }
            except Exception as e:
                logger.warning(f"Failed to save article: {e}")
                self.stats["errors"] += 1

        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            self.stats["errors"] += 1

        return None

    def _build_queries(
        self,
        language: str,
        categories: Optional[list[str]] = None,
    ) -> list[str]:
        """Build search queries for the given language and categories."""
        queries = []
        
        # Add general news queries
        base_queries = NEWS_QUERIES.get(language, NEWS_QUERIES["en"])
        queries.extend(base_queries)

        # Add category-specific queries
        if categories:
            for cat in categories:
                cat_queries = CATEGORY_QUERIES.get(cat, {})
                query = cat_queries.get(language, cat_queries.get("en", cat))
                if query:
                    queries.append(query)

        # Add trending topics
        today = datetime.now().strftime("%Y-%m-%d")
        queries.append(f"news {today}")
        queries.append(f"latest news today")

        return queries

    def _extract_date(self, meta: dict) -> str:
        """Extract date from metadata."""
        for key in ("published", "date", "published_time", "datePublished"):
            if key in meta and meta[key]:
                date_str = str(meta[key])[:10]
                if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                    return date_str

        return datetime.now().strftime("%Y-%m-%d")

    def _extract_website(self, url: str) -> str:
        """Extract website name from URL."""
        try:
            domain = urlparse(url).netloc
            domain = domain.replace("www.", "")
            domain = domain.split(".")[0]
            return domain.capitalize()
        except Exception:
            return "Unknown"

    def _extract_article_links(
        self, soup, base_url: str, selector: Optional[str] = None,
    ) -> list[tuple[str, str]]:
        """Extract article links from listing page."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        links = []
        seen = set()
        base_domain = urlparse(base_url).netloc
        
        # Accept articles from past 3 days, not just today
        today = datetime.now()
        date_patterns = []
        for i in range(4):  # Today + 3 days back
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            date_patterns.append(d)
            date_patterns.append(d.replace("-", ""))  # Also try YYYYMMDD
            date_patterns.append(d[:7])  # YYYY-MM

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

        if selector:
            for el in soup.select(selector):
                a = el if el.name == "a" else el.find("a")
                if a and a.get("href"):
                    url = urljoin(base_url, a["href"])
                    title = a.get_text(strip=True)
                    if url not in seen and len(title) > 5:
                        seen.add(url)
                        links.append((url, title))
            return links

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

            # Check if URL contains a recent date (more flexible)
            has_recent_date = any(dp in url for dp in date_patterns)

            # If no date in URL, still include if path looks like an article
            path = parsed.path.strip("/")
            is_article_like = (
                path.count("/") >= 1 and
                len(path) > 10 and
                not any(path.endswith(ext.lstrip(".")) for ext in skip_extensions)
            )

            # Also accept paths that look like article URLs even without dates
            is_news_path = any(pattern in path.lower() for pattern in [
                "news", "article", "story", "detail", "view", "page"
            ])

            if not has_recent_date and not is_article_like and not is_news_path:
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


def fetch_news_by_search(
    *,
    language: str = "en",
    categories: Optional[list[str]] = None,
    max_articles: int = 50,
    date_range: str = "d",
    proxy: Optional[dict] = None,
) -> dict:
    """Convenience function to fetch news by web search.
    
    Args:
        language: Language code.
        categories: List of categories.
        max_articles: Maximum articles.
        date_range: Date filter (d/w/m).
        proxy: Proxy settings.
        
    Returns:
        Dict with articles and stats.
    """
    fetcher = SearchNewsFetcher(proxy=proxy)
    articles = fetcher.fetch_news_by_search(
        language=language,
        categories=categories,
        max_articles=max_articles,
        date_range=date_range,
    )
    return {
        "articles": articles,
        "count": len(articles),
        "stats": fetcher.get_stats(),
    }
