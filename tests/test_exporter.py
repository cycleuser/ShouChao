"""
Tests for exporter module.
"""

import pytest
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory, NamedTemporaryFile
from pathlib import Path


class TestExportResult:
    def test_export_result_creation(self):
        from shouchao.core.exporter import ExportResult
        result = ExportResult(
            success=True,
            output_path="/tmp/test.pdf",
            format="pdf",
            file_size=1024,
        )
        assert result.success is True
        assert result.output_path == "/tmp/test.pdf"
        assert result.format == "pdf"
        assert result.file_size == 1024

    def test_export_result_to_dict(self):
        from shouchao.core.exporter import ExportResult
        result = ExportResult(
            success=False,
            format="epub",
            error="Conversion failed",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["format"] == "epub"
        assert d["error"] == "Conversion failed"

    def test_export_result_defaults(self):
        from shouchao.core.exporter import ExportResult
        result = ExportResult(success=True)
        assert result.output_path is None
        assert result.file_size == 0
        assert result.error is None
        assert result.metadata == {}


class TestMarkdownExporter:
    def test_export_creates_file(self):
        from shouchao.core.exporter import MarkdownExporter
        exporter = MarkdownExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = exporter.export(
                content="# Test\n\nThis is content.",
                title="Test Document",
                output_path=output_path,
            )
            
            assert result.success is True
            assert Path(result.output_path).exists()
            assert result.format == "markdown"

    def test_export_with_metadata(self):
        from shouchao.core.exporter import MarkdownExporter
        exporter = MarkdownExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = exporter.export(
                content="Content",
                title="Title",
                output_path=output_path,
                metadata={"author": "Test Author", "tags": ["a", "b"]},
            )
            
            assert result.success is True
            content = Path(output_path).read_text()
            assert "author" in content.lower() or "Author" in content

    def test_export_adds_extension(self):
        from shouchao.core.exporter import MarkdownExporter
        exporter = MarkdownExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test")
            result = exporter.export(
                content="Content",
                title="Title",
                output_path=output_path,
            )
            
            assert result.output_path.endswith(".md")


class TestPDFExporter:
    def test_exporter_name(self):
        from shouchao.core.exporter import PDFExporter
        exporter = PDFExporter()
        assert exporter is not None

    def test_export_without_weasyprint(self):
        from shouchao.core.exporter import PDFExporter
        exporter = PDFExporter()
        
        with patch.dict("sys.modules", {"weasyprint": None}):
            result = exporter.export(
                content="Test content",
                title="Test",
                output_path="/tmp/test.pdf",
            )
            assert result.success is False
            assert "weasyprint" in result.error.lower()

    def test_markdown_to_html(self):
        from shouchao.core.exporter import PDFExporter
        exporter = PDFExporter()
        html = exporter._markdown_to_html("# Title\n\nParagraph", "My Doc", "professional")
        assert "<h1" in html or "Title" in html
        assert "My Doc" in html


class TestEPUBExporter:
    def test_export_without_ebooklib(self):
        from shouchao.core.exporter import EPUBExporter
        exporter = EPUBExporter()
        
        with patch.dict("sys.modules", {"ebooklib": None}):
            result = exporter.export(
                content="Test",
                title="Test",
                output_path="/tmp/test.epub",
            )
            assert result.success is False
            assert "ebooklib" in result.error.lower()


class TestDOCXExporter:
    def test_export_without_python_docx(self):
        from shouchao.core.exporter import DOCXExporter
        exporter = DOCXExporter()
        
        with patch.dict("sys.modules", {"docx": None}):
            result = exporter.export(
                content="Test",
                title="Test",
                output_path="/tmp/test.docx",
            )
            assert result.success is False
            assert "python-docx" in result.error.lower()


class TestHTMLExporter:
    def test_export_creates_file(self):
        from shouchao.core.exporter import HTMLExporter
        exporter = HTMLExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.html")
            result = exporter.export(
                content="# Test\n\nContent here.",
                title="Test Page",
                output_path=output_path,
            )
            
            assert result.success is True
            assert Path(output_path).exists()
            assert result.format == "html"

    def test_export_includes_title(self):
        from shouchao.core.exporter import HTMLExporter
        exporter = HTMLExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.html")
            result = exporter.export(
                content="Content",
                title="My Title",
                output_path=output_path,
            )
            
            content = Path(output_path).read_text()
            assert "My Title" in content

    def test_export_with_metadata(self):
        from shouchao.core.exporter import HTMLExporter
        exporter = HTMLExporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.html")
            result = exporter.export(
                content="Content",
                title="Title",
                output_path=output_path,
                metadata={"language": "zh"},
            )
            
            content = Path(output_path).read_text()
            assert 'lang="zh"' in content


class TestAudioExporter:
    def test_exporter_creation(self):
        from shouchao.core.exporter import AudioExporter
        exporter = AudioExporter()
        assert exporter._engine == "edge-tts"

    def test_exporter_custom_engine(self):
        from shouchao.core.exporter import AudioExporter
        exporter = AudioExporter(engine="gtts")
        assert exporter._engine == "gtts"


class TestExporter:
    def test_supported_formats(self):
        from shouchao.core.exporter import Exporter
        exporter = Exporter()
        formats = exporter.supported_formats
        
        assert "pdf" in formats
        assert "epub" in formats
        assert "docx" in formats
        assert "html" in formats
        assert "md" in formats
        assert "audio" in formats

    def test_export_unsupported_format(self):
        from shouchao.core.exporter import Exporter
        exporter = Exporter()
        
        result = exporter.export(
            content="Test",
            title="Test",
            output_path="/tmp/test.xyz",
            format="xyz",
        )
        
        assert result.success is False
        assert "Unsupported format" in result.error

    def test_export_markdown(self):
        from shouchao.core.exporter import Exporter
        exporter = Exporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = exporter.export(
                content="# Hello\n\nWorld",
                title="Test",
                output_path=output_path,
                format="md",
            )
            
            assert result.success is True
            assert Path(output_path).exists()

    def test_export_html(self):
        from shouchao.core.exporter import Exporter
        exporter = Exporter()
        
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.html")
            result = exporter.export(
                content="# Test",
                title="Test",
                output_path=output_path,
                format="html",
            )
            
            assert result.success is True
            assert Path(output_path).exists()


class TestExportContentFunction:
    def test_function_exists(self):
        from shouchao.core.exporter import export_content
        assert callable(export_content)

    def test_function_returns_result(self):
        from shouchao.core.exporter import export_content, ExportResult
        with TemporaryDirectory() as tmpdir:
            output_path = str(Path(tmpdir) / "test.md")
            result = export_content(
                content="Test",
                title="Test",
                output_path=output_path,
                format="md",
            )
            assert isinstance(result, ExportResult)
            assert result.success is True