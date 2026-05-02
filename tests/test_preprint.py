"""
Tests for preprint functionality.
"""

import pytest
from datetime import datetime


class TestPreprintEntry:
    def test_preprint_entry_creation(self):
        from shouchao.core.preprint import PreprintEntry

        entry = PreprintEntry(
            title="Test Paper",
            url="https://arxiv.org/abs/1234.5678",
            abstract="This is a test abstract.",
            authors=["Author One", "Author Two"],
            categories=["cs.AI", "cs.LG"],
            published="2024-01-15T10:00:00Z",
            source="arxiv",
        )

        assert entry.title == "Test Paper"
        assert entry.url == "https://arxiv.org/abs/1234.5678"
        assert entry.source == "arxiv"
        assert len(entry.authors) == 2
        assert len(entry.categories) == 2

    def test_date_str_extraction(self):
        from shouchao.core.preprint import PreprintEntry

        entry = PreprintEntry(
            title="Test",
            url="https://example.com",
            abstract="Test",
            published="2024-01-15T10:00:00Z",
        )

        assert entry.date_str == "2024-01-15"

    def test_date_str_fallback(self):
        from shouchao.core.preprint import PreprintEntry

        entry = PreprintEntry(
            title="Test",
            url="https://example.com",
            abstract="Test",
            published="",
        )

        assert entry.date_str == datetime.now().strftime("%Y-%m-%d")

    def test_content_hash(self):
        from shouchao.core.preprint import PreprintEntry

        entry1 = PreprintEntry(
            title="Test",
            url="https://arxiv.org/abs/1234.5678",
            abstract="Test",
        )
        entry2 = PreprintEntry(
            title="Test",
            url="https://arxiv.org/abs/1234.5678",
            abstract="Test",
        )

        assert entry1.content_hash == entry2.content_hash

    def test_to_markdown(self):
        from shouchao.core.preprint import PreprintEntry

        entry = PreprintEntry(
            title="Test Paper",
            url="https://arxiv.org/abs/1234.5678",
            abstract="This is a test abstract.",
            authors=["Author One"],
            categories=["cs.AI"],
            published="2024-01-15T10:00:00Z",
            source="arxiv",
            pdf_url="https://arxiv.org/pdf/1234.5678",
        )

        md = entry.to_markdown()
        assert "---" in md
        assert "title:" in md
        assert "Test Paper" in md
        assert "## Abstract" in md
        assert "This is a test abstract." in md
        assert "[PDF]" in md


class TestPreprintCategories:
    def test_arxiv_categories(self):
        from shouchao.core.preprint import ARXIV_CATEGORIES

        assert "cs" in ARXIV_CATEGORIES
        assert "math" in ARXIV_CATEGORIES
        assert "cs.AI" in ARXIV_CATEGORIES["cs"]
        assert "cs.LG" in ARXIV_CATEGORIES["cs"]

    def test_biorxiv_categories(self):
        from shouchao.core.preprint import BIORXIV_CATEGORIES

        assert "bioinformatics" in BIORXIV_CATEGORIES
        assert "genomics" in BIORXIV_CATEGORIES

    def test_medrxiv_categories(self):
        from shouchao.core.preprint import MEDRXIV_CATEGORIES

        assert "oncology" in MEDRXIV_CATEGORIES
        assert "neurology" in MEDRXIV_CATEGORIES


class TestPreprintSources:
    def test_preprint_sources_exist(self):
        from shouchao.core.sources import get_preprint_sources

        sources = get_preprint_sources()
        assert len(sources) > 0

        # Check that arXiv is in the sources
        arxiv_sources = [s for s in sources if "arxiv" in s.name.lower()]
        assert len(arxiv_sources) > 0

    def test_preprint_source_categories(self):
        from shouchao.core.sources import get_preprint_sources

        ai_sources = get_preprint_sources(category="ai")
        assert len(ai_sources) > 0


class TestPreprintAPI:
    def test_fetch_preprints_import(self):
        from shouchao.api import fetch_preprints
        assert callable(fetch_preprints)

    def test_search_preprints_import(self):
        from shouchao.api import search_preprints
        assert callable(search_preprints)

    def test_index_preprints_import(self):
        from shouchao.api import index_preprints
        assert callable(index_preprints)

    def test_get_preprint_categories_import(self):
        from shouchao.api import get_preprint_categories
        assert callable(get_preprint_categories)


class TestPreprintScheduler:
    def test_scheduler_creation(self):
        from shouchao.core.scheduler import PreprintScheduler
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            scheduler = PreprintScheduler(config_path=Path(tmpdir) / "schedule.json")
            status = scheduler.get_status()
            assert "enabled" in status
            assert "running" in status
            assert "time" in status

    def test_scheduler_enable_disable(self):
        from shouchao.core.scheduler import PreprintScheduler
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            scheduler = PreprintScheduler(config_path=Path(tmpdir) / "schedule.json")

            scheduler.enable(time="08:00")
            status = scheduler.get_status()
            assert status["enabled"] is True
            assert status["time"] == "08:00"

            scheduler.disable()
            status = scheduler.get_status()
            assert status["enabled"] is False


class TestPreprintTokenization:
    def test_tokenize(self):
        from shouchao.core.preprint import _tokenize

        tokens = _tokenize("Hello world, this is a test!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_keyword_search(self):
        from shouchao.core.preprint import (
            PreprintEntry,
            search_preprints_keyword,
        )

        entries = [
            PreprintEntry(
                title="Large Language Models",
                url="https://arxiv.org/abs/1",
                abstract="This paper discusses large language models and transformers.",
                categories=["cs.CL"],
                source="arxiv",
            ),
            PreprintEntry(
                title="Computer Vision",
                url="https://arxiv.org/abs/2",
                abstract="This paper is about image classification.",
                categories=["cs.CV"],
                source="arxiv",
            ),
        ]

        results = search_preprints_keyword(
            query="language models",
            entries=entries,
            top_k=5,
        )

        assert len(results) > 0
        # The first entry should have higher score for "language models"
        assert results[0][1].title == "Large Language Models"


class TestConfigPreprintSettings:
    def test_preprint_config_defaults(self):
        from shouchao.core.config import Config

        config = Config()
        assert config.preprint_servers == ["arxiv", "biorxiv", "medrxiv"]
        assert len(config.preprint_categories) > 0
        assert config.preprint_max_results == 200
        assert config.preprint_auto_index is True
        assert config.preprint_schedule_time == "06:00"
        assert config.preprint_schedule_enabled is False

    def test_preprint_dir_exists(self):
        from shouchao.core.config import PREPRINT_DIR, ensure_dirs

        ensure_dirs()
        assert PREPRINT_DIR is not None


class TestLazyImports:
    def test_fetch_preprints_lazy_import(self):
        import shouchao
        func = shouchao.fetch_preprints
        assert callable(func)

    def test_search_preprints_lazy_import(self):
        import shouchao
        func = shouchao.search_preprints
        assert callable(func)

    def test_index_preprints_lazy_import(self):
        import shouchao
        func = shouchao.index_preprints
        assert callable(func)

    def test_get_preprint_categories_lazy_import(self):
        import shouchao
        func = shouchao.get_preprint_categories
        assert callable(func)
