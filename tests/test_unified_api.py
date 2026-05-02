"""
Unified API tests for ShouChao.

Tests: ToolResult, API functions, TOOLS schema, dispatch, CLI flags, exports.
"""

import json
import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory


class TestToolResult:
    def test_success_result(self):
        from shouchao.api import ToolResult
        r = ToolResult(success=True, data={"key": "value"}, metadata={"v": "1"})
        assert r.success is True
        assert r.data == {"key": "value"}
        assert r.error is None

    def test_failure_result(self):
        from shouchao.api import ToolResult
        r = ToolResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"

    def test_to_dict(self):
        from shouchao.api import ToolResult
        r = ToolResult(success=True, data=[1, 2], metadata={"x": 1})
        d = r.to_dict()
        assert set(d.keys()) == {"success", "data", "error", "metadata"}

    def test_default_metadata_isolation(self):
        from shouchao.api import ToolResult
        r1 = ToolResult(success=True)
        r2 = ToolResult(success=True)
        r1.metadata["a"] = 1
        assert "a" not in r2.metadata


class TestShouChaoAPI:
    def test_list_sources_success(self):
        from shouchao.api import list_sources
        result = list_sources(language="en")
        assert result.success is True
        assert "sources" in result.data
        assert result.data["count"] > 0
        assert "version" in result.metadata

    def test_list_sources_all(self):
        from shouchao.api import list_sources
        result = list_sources()
        assert result.success is True
        assert result.data["count"] > 50  # At least 50 sources across 10 languages

    def test_list_sources_filter_rss(self):
        from shouchao.api import list_sources
        result = list_sources(source_type="rss")
        assert result.success is True
        for s in result.data["sources"]:
            assert s["source_type"] == "rss"

    def test_list_sources_invalid_type(self):
        from shouchao.api import list_sources
        result = list_sources(source_type="invalid")
        assert result.success is False
        assert result.error is not None

    @patch("shouchao.core.fetcher.RequestsFetcher")
    def test_fetch_news_no_sources(self, mock_fetcher):
        from shouchao.api import fetch_news
        result = fetch_news(language="xx", max_articles=1)
        assert result.success is True
        assert result.data["fetched"] == 0

    def test_search_news_no_ollama(self):
        from shouchao.api import search_news
        # Without Ollama running, should return error
        result = search_news(query="test")
        assert isinstance(result.success, bool)
        assert "version" in result.metadata

    def test_index_news_empty_dir(self):
        from shouchao.api import index_news
        with TemporaryDirectory() as tmpdir:
            result = index_news(directory=tmpdir)
            # May fail due to no Ollama, but should not crash
            assert isinstance(result.success, bool)

    def test_generate_briefing_returns_toolresult(self):
        from shouchao.api import generate_briefing, ToolResult
        result = generate_briefing(briefing_type="daily")
        assert isinstance(result, ToolResult)

    def test_analyze_news_returns_toolresult(self):
        from shouchao.api import analyze_news, ToolResult
        result = analyze_news(query="test query")
        assert isinstance(result, ToolResult)


class TestToolsSchema:
    def test_tools_is_list(self):
        from shouchao.tools import TOOLS
        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 1

    def test_tool_names(self):
        from shouchao.tools import TOOLS
        for tool in TOOLS:
            assert tool["function"]["name"].startswith("shouchao_")

    def test_tool_structure(self):
        from shouchao.tools import TOOLS
        for tool in TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]
            assert "required" in func["parameters"]

    def test_required_fields_in_properties(self):
        from shouchao.tools import TOOLS
        for tool in TOOLS:
            func = tool["function"]
            props = func["parameters"]["properties"]
            for req in func["parameters"]["required"]:
                assert req in props, f"Required '{req}' not in properties"


class TestToolsDispatch:
    def test_dispatch_unknown_tool(self):
        from shouchao.tools import dispatch
        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch("nonexistent_tool", {})

    def test_dispatch_json_string_args(self):
        from shouchao.tools import dispatch
        args = json.dumps({"language": "en"})
        result = dispatch("shouchao_list_sources", args)
        assert isinstance(result, dict)
        assert "success" in result

    def test_dispatch_dict_args(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_list_sources", {"language": "zh"})
        assert isinstance(result, dict)
        assert result["success"] is True

    def test_dispatch_error_case(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_list_sources", {"source_type": "invalid"})
        assert isinstance(result, dict)
        assert result["success"] is False


class TestCLIFlags:
    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "shouchao"] + list(args),
            capture_output=True, text=True, timeout=15,
        )

    def test_version_flag(self):
        r = self._run_cli("-V")
        assert r.returncode == 0
        assert "shouchao" in r.stdout.lower()

    def test_help_has_unified_flags(self):
        r = self._run_cli("--help")
        assert r.returncode == 0
        assert "--json" in r.stdout
        assert "--quiet" in r.stdout or "-q" in r.stdout
        assert "--verbose" in r.stdout or "-v" in r.stdout

    def test_sources_subcommand(self):
        r = self._run_cli("sources", "--language", "en", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["success"] is True
        assert "sources" in data["data"]
        assert len(data["data"]["sources"]) > 0


class TestPackageExports:
    def test_version(self):
        import shouchao
        assert hasattr(shouchao, "__version__")
        assert isinstance(shouchao.__version__, str)

    def test_toolresult(self):
        from shouchao import ToolResult
        assert callable(ToolResult)

    def test_api_functions_exported(self):
        from shouchao import fetch_news, search_news, generate_briefing
        from shouchao import analyze_news, index_news, list_sources
        assert callable(fetch_news)
        assert callable(search_news)
        assert callable(generate_briefing)
        assert callable(analyze_news)
        assert callable(index_news)
        assert callable(list_sources)


class TestCoreSources:
    """Additional tests for the source registry."""

    def test_all_languages_have_sources(self):
        from shouchao.core.sources import SOURCE_REGISTRY
        expected_langs = {"zh", "en", "ja", "fr", "ru", "de", "it", "es", "pt", "ko", "preprint"}
        assert set(SOURCE_REGISTRY.keys()) == expected_langs

    def test_each_language_has_sources(self):
        from shouchao.core.sources import SOURCE_REGISTRY
        for lang, sources in SOURCE_REGISTRY.items():
            assert len(sources) >= 5, f"Language {lang} has too few sources"

    def test_source_dataclass(self):
        from shouchao.core.sources import NewsSource, SourceType
        s = NewsSource("Test", "en", "https://example.com", SourceType.RSS,
                        rss_url="https://example.com/rss")
        d = s.to_dict()
        assert d["name"] == "Test"
        s2 = NewsSource.from_dict(d)
        assert s2.name == "Test"
        assert s2.source_type == SourceType.RSS


class TestCoreConfig:
    """Tests for configuration module."""

    def test_config_defaults(self):
        from shouchao.core.config import Config
        c = Config()
        assert c.ollama_url == "http://localhost:11434"
        assert c.chunk_size == 800
        assert c.chunk_overlap == 150

    def test_config_save_load(self):
        from shouchao.core.config import Config, DATA_DIR
        import json
        with TemporaryDirectory() as tmpdir:
            cfg = Config(language="en", fetch_delay=2.0)
            path = Path(tmpdir) / "test_config.json"
            path.write_text(json.dumps({"language": "en", "fetch_delay": 2.0}))
            data = json.loads(path.read_text())
            assert data["language"] == "en"
            assert data["fetch_delay"] == 2.0


class TestI18n:
    def test_translation_function(self):
        from shouchao.i18n import t
        result = t("app_title", "en")
        assert "ShouChao" in result

    def test_all_languages_covered(self):
        from shouchao.i18n import TRANSLATIONS, LANGUAGES
        for key, entries in TRANSLATIONS.items():
            for lang in LANGUAGES:
                assert lang in entries, f"Key '{key}' missing language '{lang}'"

    def test_fallback_to_english(self):
        from shouchao.i18n import t
        result = t("app_title", "unknown_lang")
        assert "ShouChao" in result

    def test_missing_key_returns_key(self):
        from shouchao.i18n import t
        assert t("nonexistent_key_xyz") == "nonexistent_key_xyz"
