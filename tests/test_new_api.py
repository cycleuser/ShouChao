"""
Tests for new API functions in v0.2.0.
"""

import pytest
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory
from pathlib import Path


class TestWebSearchAPI:
    def test_web_search_function_exists(self):
        from shouchao.api import web_search
        assert callable(web_search)

    def test_web_search_returns_tool_result(self):
        from shouchao.api import web_search, ToolResult
        result = web_search(query="test")
        assert isinstance(result, ToolResult)

    def test_web_search_success(self):
        from shouchao.api import web_search
        result = web_search(
            query="Python programming",
            engines=["duckduckgo"],
            num_results=5,
        )
        assert result.success is True
        assert "results" in result.data

    def test_web_search_with_language(self):
        from shouchao.api import web_search
        result = web_search(
            query="test",
            language="en",
        )
        assert result.success is True


class TestTextToSpeechAPI:
    def test_tts_function_exists(self):
        from shouchao.api import text_to_speech
        assert callable(text_to_speech)

    def test_tts_returns_tool_result(self):
        from shouchao.api import text_to_speech, ToolResult
        result = text_to_speech(text="Hello world")
        assert isinstance(result, ToolResult)

    def test_tts_result_has_required_fields(self):
        from shouchao.api import text_to_speech
        result = text_to_speech(text="Test")
        assert "engine" in result.data or result.error is not None


class TestExportDocumentAPI:
    def test_export_function_exists(self):
        from shouchao.api import export_document
        assert callable(export_document)

    def test_export_returns_tool_result(self):
        from shouchao.api import export_document, ToolResult
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = export_document(
                content="# Test\n\nContent",
                title="Test Document",
                output_path=output_path,
                format="md",
            )
            assert isinstance(result, ToolResult)
            assert result.success is True

    def test_export_markdown(self):
        from shouchao.api import export_document
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = export_document(
                content="# Hello\n\nWorld",
                title="Test",
                output_path=output_path,
                format="md",
            )
            assert result.success is True
            assert Path(output_path).exists()

    def test_export_html(self):
        from shouchao.api import export_document
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.html")
            result = export_document(
                content="# Test",
                title="Test",
                output_path=output_path,
                format="html",
            )
            assert result.success is True
            assert Path(output_path).exists()

    def test_export_unsupported_format(self):
        from shouchao.api import export_document
        result = export_document(
            content="Test",
            title="Test",
            output_path="/tmp/test.xyz",
            format="xyz",
        )
        assert result.success is False


class TestKeywordSearchAndSummarizeAPI:
    def test_function_exists(self):
        from shouchao.api import keyword_search_and_summarize
        assert callable(keyword_search_and_summarize)

    def test_returns_tool_result(self):
        from shouchao.api import keyword_search_and_summarize, ToolResult
        result = keyword_search_and_summarize(keywords=["test"])
        assert isinstance(result, ToolResult)

    def test_with_multiple_keywords(self):
        from shouchao.api import keyword_search_and_summarize
        result = keyword_search_and_summarize(
            keywords=["Python", "programming"],
            max_results=3,
        )
        assert result.success is True
        assert "keywords" in result.data


class TestNewToolsSchema:
    def test_tools_include_web_search(self):
        from shouchao.tools import TOOLS
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "shouchao_web_search" in tool_names

    def test_tools_include_tts(self):
        from shouchao.tools import TOOLS
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "shouchao_text_to_speech" in tool_names

    def test_tools_include_export(self):
        from shouchao.tools import TOOLS
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "shouchao_export_document" in tool_names

    def test_tools_include_keyword_search(self):
        from shouchao.tools import TOOLS
        tool_names = [t["function"]["name"] for t in TOOLS]
        assert "shouchao_keyword_search_and_summarize" in tool_names

    def test_tools_have_required_fields(self):
        from shouchao.tools import TOOLS
        for tool in TOOLS:
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"

    def test_new_tools_required_in_properties(self):
        from shouchao.tools import TOOLS
        for tool in TOOLS:
            func = tool["function"]
            props = func["parameters"]["properties"]
            for req in func["parameters"].get("required", []):
                assert req in props


class TestToolsDispatchNew:
    def test_dispatch_web_search(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_web_search", {"query": "test"})
        assert "success" in result

    def test_dispatch_tts(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_text_to_speech", {"text": "hello"})
        assert "success" in result

    def test_dispatch_export(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_export_document", {
            "content": "test",
            "title": "Test",
            "output_path": "/tmp/test_export.md",
            "format": "md",
        })
        assert "success" in result

    def test_dispatch_keyword_search(self):
        from shouchao.tools import dispatch
        result = dispatch("shouchao_keyword_search_and_summarize", {
            "keywords": ["AI"]
        })
        assert "success" in result

    def test_dispatch_unknown_tool(self):
        from shouchao.tools import dispatch
        with pytest.raises(ValueError, match="Unknown tool"):
            dispatch("shouchao_nonexistent", {})


class TestPackageExportsNew:
    def test_web_search_exported(self):
        from shouchao import web_search
        assert callable(web_search)

    def test_text_to_speech_exported(self):
        from shouchao import text_to_speech
        assert callable(text_to_speech)

    def test_export_document_exported(self):
        from shouchao import export_document
        assert callable(export_document)

    def test_keyword_search_exported(self):
        from shouchao import keyword_search_and_summarize
        assert callable(keyword_search_and_summarize)

    def test_all_exports_in_all(self):
        import shouchao
        assert "web_search" in shouchao.__all__
        assert "text_to_speech" in shouchao.__all__
        assert "export_document" in shouchao.__all__
        assert "keyword_search_and_summarize" in shouchao.__all__

    def test_version_updated(self):
        import shouchao
        assert shouchao.__version__.startswith("0.3")