"""
Tests for web search module.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSearchResult:
    def test_search_result_creation(self):
        from shouchao.core.web_search import SearchResult
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="example.com",
            rank=1,
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "example.com"
        assert result.rank == 1

    def test_search_result_to_dict(self):
        from shouchao.core.web_search import SearchResult
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Snip",
            source="test.com",
            rank=2,
            date="2024-01-01",
        )
        d = result.to_dict()
        assert d["title"] == "Test"
        assert d["url"] == "https://test.com"
        assert d["snippet"] == "Snip"
        assert d["source"] == "test.com"
        assert d["rank"] == 2
        assert d["date"] == "2024-01-01"

    def test_search_result_default_metadata(self):
        from shouchao.core.web_search import SearchResult
        result = SearchResult(
            title="Test",
            url="https://test.com",
            snippet="Snip",
        )
        assert result.metadata == {}
        assert result.rank == 0


class TestSearchResponse:
    def test_search_response_creation(self):
        from shouchao.core.web_search import SearchResponse, SearchResult
        results = [
            SearchResult(title="A", url="https://a.com", snippet="A"),
            SearchResult(title="B", url="https://b.com", snippet="B"),
        ]
        response = SearchResponse(
            query="test query",
            results=results,
            total=2,
            engine="duckduckgo",
        )
        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.total == 2
        assert response.engine == "duckduckgo"
        assert response.error is None

    def test_search_response_with_error(self):
        from shouchao.core.web_search import SearchResponse
        response = SearchResponse(
            query="test",
            results=[],
            engine="google",
            error="API key required",
        )
        assert response.error == "API key required"
        assert response.results == []

    def test_search_response_to_dict(self):
        from shouchao.core.web_search import SearchResponse, SearchResult
        results = [SearchResult(title="X", url="https://x.com", snippet="X")]
        response = SearchResponse(
            query="q",
            results=results,
            total=1,
            engine="bing",
        )
        d = response.to_dict()
        assert d["query"] == "q"
        assert len(d["results"]) == 1
        assert d["total"] == 1
        assert d["engine"] == "bing"


class TestDuckDuckGoEngine:
    def test_engine_name(self):
        from shouchao.core.web_search import DuckDuckGoEngine
        engine = DuckDuckGoEngine()
        assert engine.name == "duckduckgo"

    def test_search_without_package(self):
        from shouchao.core.web_search import DuckDuckGoEngine
        engine = DuckDuckGoEngine()
        with patch.dict("sys.modules", {"duckduckgo_search": None}):
            response = engine.search("test query")
            assert response.error is not None
            assert "not installed" in response.error

    @patch("shouchao.core.web_search.DuckDuckGoEngine.search")
    def test_search_returns_response(self, mock_search):
        from shouchao.core.web_search import DuckDuckGoEngine, SearchResponse
        mock_search.return_value = SearchResponse(
            query="test",
            results=[],
            engine="duckduckgo",
        )
        engine = DuckDuckGoEngine()
        response = engine.search("test")
        assert response.engine == "duckduckgo"


class TestGoogleCustomSearchEngine:
    def test_engine_name(self):
        from shouchao.core.web_search import GoogleCustomSearchEngine
        engine = GoogleCustomSearchEngine()
        assert engine.name == "google"

    def test_search_without_credentials(self):
        from shouchao.core.web_search import GoogleCustomSearchEngine
        engine = GoogleCustomSearchEngine()
        response = engine.search("test query")
        assert response.error is not None
        assert "API key" in response.error

    def test_search_with_credentials_mock(self):
        from shouchao.core.web_search import GoogleCustomSearchEngine
        engine = GoogleCustomSearchEngine(api_key="test_key", search_engine_id="test_cx")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch("requests.get", return_value=mock_response):
            response = engine.search("test")
            assert response.error is None


class TestBingSearchEngine:
    def test_engine_name(self):
        from shouchao.core.web_search import BingSearchEngine
        engine = BingSearchEngine()
        assert engine.name == "bing"

    def test_search_without_key(self):
        from shouchao.core.web_search import BingSearchEngine
        engine = BingSearchEngine()
        response = engine.search("test query")
        assert response.error is not None
        assert "subscription key" in response.error.lower()


class TestSearXNGEngine:
    def test_engine_name(self):
        from shouchao.core.web_search import SearXNGEngine
        engine = SearXNGEngine()
        assert engine.name == "searxng"

    def test_custom_instance(self):
        from shouchao.core.web_search import SearXNGEngine
        engine = SearXNGEngine(instance_url="https://custom.searx.com")
        assert engine._instance_url == "https://custom.searx.com"


class TestBraveSearchEngine:
    def test_engine_name(self):
        from shouchao.core.web_search import BraveSearchEngine
        engine = BraveSearchEngine()
        assert engine.name == "brave"

    def test_search_without_key(self):
        from shouchao.core.web_search import BraveSearchEngine
        engine = BraveSearchEngine()
        response = engine.search("test query")
        assert response.error is not None
        assert "API key" in response.error


class TestWebSearchEngine:
    def test_available_engines(self):
        from shouchao.core.web_search import WebSearchEngine
        engine = WebSearchEngine()
        engines = engine.available_engines
        assert "duckduckgo" in engines

    def test_search_with_invalid_engine(self):
        from shouchao.core.web_search import WebSearchEngine
        engine = WebSearchEngine()
        response = engine.search("test", engines=["invalid_engine"])
        assert response.error is not None

    def test_deduplicate_results(self):
        from shouchao.core.web_search import WebSearchEngine, SearchResult
        engine = WebSearchEngine()
        results = [
            SearchResult(title="A", url="https://example.com/page", snippet="1"),
            SearchResult(title="B", url="https://example.com/page/", snippet="2"),
            SearchResult(title="C", url="https://example.com/other", snippet="3"),
        ]
        deduped = engine._deduplicate(results)
        assert len(deduped) == 2

    def test_rank_results(self):
        from shouchao.core.web_search import WebSearchEngine, SearchResult
        engine = WebSearchEngine()
        results = [
            SearchResult(title="A", url="https://a.com", snippet=""),
            SearchResult(title="B", url="https://b.com", snippet=""),
        ]
        ranked = engine._rank_results(results)
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2


class TestWebSearchConvenience:
    def test_search_web_function_exists(self):
        from shouchao.core.web_search import search_web
        assert callable(search_web)

    @patch("shouchao.core.web_search.WebSearchEngine.search")
    def test_search_web_calls_engine(self, mock_search):
        from shouchao.core.web_search import search_web, SearchResponse
        mock_search.return_value = SearchResponse(
            query="test query",
            results=[],
            engine="duckduckgo",
        )
        result = search_web("test query")
        assert result.query == "test query"
        assert result.engine == "duckduckgo"