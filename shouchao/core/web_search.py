"""
Web search engine integration for ShouChao.

Supports multiple search backends: Google Custom Search, Bing, DuckDuckGo,
SearXNG, and Brave Search. Provides unified interface for searching the web
and aggregating results for AI-powered summarization.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str = ""
    date: Optional[str] = None
    rank: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "date": self.date,
            "rank": self.rank,
            "metadata": self.metadata,
        }


@dataclass
class SearchResponse:
    """Response from a search query."""
    query: str
    results: list[SearchResult]
    total: int = 0
    engine: str = ""
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "engine": self.engine,
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseSearchEngine(ABC):
    """Abstract base for search engine implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name identifier."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        """Execute search and return results."""
        pass

    def _get_session(self, proxy: Optional[str] = None) -> requests.Session:
        """Create requests session with optional proxy."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session


class DuckDuckGoEngine(BaseSearchEngine):
    """DuckDuckGo search engine (no API key required)."""

    @property
    def name(self) -> str:
        return "duckduckgo"

    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error="duckduckgo-search not installed. Run: pip install duckduckgo-search",
            )

        try:
            results = []
            with DDGS() as ddgs:
                search_kwargs = {"keywords": query, "max_results": num_results}
                if language:
                    search_kwargs["region"] = language
                if date_range:
                    search_kwargs["timelimit"] = date_range

                for r in ddgs.text(**search_kwargs):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source=self._extract_domain(r.get("href", "")),
                        rank=len(results) + 1,
                    ))

            return SearchResponse(
                query=query,
                results=results,
                total=len(results),
                engine=self.name,
            )
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error=str(e),
            )

    def _extract_domain(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return ""


class GoogleCustomSearchEngine(BaseSearchEngine):
    """Google Custom Search API (requires API key and CX)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ):
        self._api_key = api_key
        self._cx = search_engine_id

    @property
    def name(self) -> str:
        return "google"

    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        if not self._api_key or not self._cx:
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error="Google Custom Search requires API key and Search Engine ID. "
                      "Set GOOGLE_API_KEY and GOOGLE_CX environment variables.",
            )

        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self._api_key,
                "cx": self._cx,
                "q": query,
                "num": min(num_results, 10),
            }
            if language:
                params["lr"] = f"lang_{language}"
            if date_range:
                params["dateRestrict"] = date_range

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for i, item in enumerate(data.get("items", [])):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source=item.get("displayLink", ""),
                    rank=i + 1,
                    metadata={
                        "pagemap": item.get("pagemap", {}),
                    },
                ))

            return SearchResponse(
                query=query,
                results=results,
                total=data.get("searchInfo", {}).get("totalResults", len(results)),
                engine=self.name,
            )
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error=str(e),
            )


class BingSearchEngine(BaseSearchEngine):
    """Bing Search API (requires subscription key)."""

    def __init__(self, subscription_key: Optional[str] = None):
        self._key = subscription_key

    @property
    def name(self) -> str:
        return "bing"

    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        if not self._key:
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error="Bing Search requires subscription key. "
                      "Set BING_SUBSCRIPTION_KEY environment variable.",
            )

        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": self._key}
            params = {
                "q": query,
                "count": num_results,
                "responseFilter": "Webpages",
            }
            if language:
                params["mkt"] = language
            if date_range:
                params["freshness"] = date_range

            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = []
            web_pages = data.get("webPages", {}).get("value", [])
            for i, item in enumerate(web_pages):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source=item.get("displayUrl", ""),
                    date=item.get("dateLastCrawled"),
                    rank=i + 1,
                ))

            return SearchResponse(
                query=query,
                results=results,
                total=data.get("webPages", {}).get("totalEstimatedMatches", len(results)),
                engine=self.name,
            )
        except Exception as e:
            logger.error(f"Bing search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error=str(e),
            )


class SearXNGEngine(BaseSearchEngine):
    """SearXNG meta search engine (self-hosted or public instances)."""

    def __init__(self, instance_url: str = "https://searx.be"):
        self._instance_url = instance_url.rstrip("/")

    @property
    def name(self) -> str:
        return "searxng"

    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        try:
            url = f"{self._instance_url}/search"
            params = {
                "q": query,
                "format": "json",
                "engines": "google,bing,duckduckgo",
            }
            if language:
                params["language"] = language
            if date_range:
                params["time_range"] = date_range

            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for i, item in enumerate(data.get("results", [])[:num_results]):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=item.get("engine", ""),
                    rank=i + 1,
                    metadata={
                        "engines": item.get("engines", []),
                    },
                ))

            return SearchResponse(
                query=query,
                results=results,
                total=len(results),
                engine=self.name,
            )
        except Exception as e:
            logger.error(f"SearXNG search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error=str(e),
            )


class BraveSearchEngine(BaseSearchEngine):
    """Brave Search API."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "brave"

    def search(
        self,
        query: str,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
    ) -> SearchResponse:
        if not self._api_key:
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error="Brave Search requires API key. "
                      "Set BRAVE_API_KEY environment variable.",
            )

        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self._api_key,
            }
            params = {"q": query, "count": num_results}
            if language:
                params["search_lang"] = language
            if date_range:
                params["freshness"] = date_range

            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = []
            web_results = data.get("web", {}).get("results", [])
            for i, item in enumerate(web_results):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=item.get("profile", {}).get("name", ""),
                    rank=i + 1,
                ))

            return SearchResponse(
                query=query,
                results=results,
                total=len(results),
                engine=self.name,
            )
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
                engine=self.name,
                error=str(e),
            )


class WebSearchEngine:
    """
    Unified web search interface that aggregates results from multiple engines.

    Usage:
        engine = WebSearchEngine()
        response = engine.search("AI news", engines=["duckduckgo", "brave"])
        for result in response.results:
            print(f"{result.title}: {result.url}")
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        google_cx: Optional[str] = None,
        bing_key: Optional[str] = None,
        brave_key: Optional[str] = None,
        searxng_url: Optional[str] = None,
        proxy: Optional[str] = None,
    ):
        import os

        self._engines: dict[str, BaseSearchEngine] = {}

        google_key = google_api_key or os.environ.get("GOOGLE_API_KEY")
        google_cx = google_cx or os.environ.get("GOOGLE_CX")
        if google_key and google_cx:
            self._engines["google"] = GoogleCustomSearchEngine(google_key, google_cx)

        bing_key = bing_key or os.environ.get("BING_SUBSCRIPTION_KEY")
        if bing_key:
            self._engines["bing"] = BingSearchEngine(bing_key)

        brave_key = brave_key or os.environ.get("BRAVE_API_KEY")
        if brave_key:
            self._engines["brave"] = BraveSearchEngine(brave_key)

        if searxng_url or os.environ.get("SEARXNG_URL"):
            self._engines["searxng"] = SearXNGEngine(
                searxng_url or os.environ.get("SEARXNG_URL", "https://searx.be")
            )

        self._engines["duckduckgo"] = DuckDuckGoEngine()

        self._proxy = proxy

    @property
    def available_engines(self) -> list[str]:
        """List available search engine names."""
        return list(self._engines.keys())

    def search(
        self,
        query: str,
        engines: Optional[list[str]] = None,
        num_results: int = 10,
        language: Optional[str] = None,
        date_range: Optional[str] = None,
        aggregate: bool = True,
    ) -> SearchResponse:
        """
        Execute search across specified engines.

        Args:
            query: Search query string.
            engines: List of engine names to use. None = all available.
            num_results: Results per engine.
            language: Language code for results.
            date_range: Date filter (d=day, w=week, m=month).
            aggregate: Combine and deduplicate results.

        Returns:
            SearchResponse with combined or individual results.
        """
        if not engines:
            engines = self.available_engines

        if not aggregate or len(engines) == 1:
            engine_name = engines[0]
            if engine_name not in self._engines:
                return SearchResponse(
                    query=query,
                    results=[],
                    engine=engine_name,
                    error=f"Engine '{engine_name}' not available",
                )
            return self._engines[engine_name].search(
                query, num_results, language, date_range
            )

        all_results = []
        errors = []

        for engine_name in engines:
            if engine_name not in self._engines:
                continue
            response = self._engines[engine_name].search(
                query, num_results, language, date_range
            )
            if response.error:
                errors.append(f"{engine_name}: {response.error}")
            else:
                all_results.extend(response.results)

        if aggregate:
            all_results = self._deduplicate(all_results)
            all_results = self._rank_results(all_results)

        return SearchResponse(
            query=query,
            results=all_results[:num_results * len(engines)],
            total=len(all_results),
            engine=",".join(engines),
            metadata={"errors": errors} if errors else {},
        )

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate results by URL."""
        seen = set()
        unique = []
        for r in results:
            normalized_url = r.url.lower().rstrip("/")
            if normalized_url not in seen:
                seen.add(normalized_url)
                unique.append(r)
        return unique

    def _rank_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Rank results by combined score."""
        for i, r in enumerate(results):
            r.rank = i + 1
        return results


def search_web(
    query: str,
    engines: Optional[list[str]] = None,
    num_results: int = 10,
    language: Optional[str] = None,
) -> SearchResponse:
    """
    Convenience function for web search.

    Args:
        query: Search query.
        engines: List of engines to use (default: duckduckgo).
        num_results: Maximum results.
        language: Language filter.

    Returns:
        SearchResponse with results.
    """
    search_engine = WebSearchEngine()
    return search_engine.search(
        query=query,
        engines=engines or ["duckduckgo"],
        num_results=num_results,
        language=language,
    )