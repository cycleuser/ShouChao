# AGENTS.md - AI Agent Guidelines for ShouChao

This document provides essential information for AI coding agents working in this repository.

## Project Overview

ShouChao (手抄) is a Python package for web information retrieval. It aggregates news from 100+ sources across 10 languages, converts articles to markdown, indexes them into ChromaDB, and provides AI-powered analysis via Ollama. Version 0.2.0 adds web search, TTS, and export capabilities.

## Workflow

The application follows a 5-step workflow:

1. **Model Settings** - Configure Ollama models and proxy
2. **Fetch News** - Select languages and fetch articles
3. **Content Search** - Search local news and web
4. **Generate Briefing** - AI summarize in any language
5. **TTS Playback** - Convert briefing to audio

## Build / Lint / Test Commands

### Installation
```bash
pip install -e ".[dev]"
pip install -e ".[all]"  # Install all optional dependencies
```

### Running Tests
```bash
python -m pytest tests/test_unified_api.py -v
```

### Running a Single Test
```bash
python -m pytest tests/test_unified_api.py::TestToolResult::test_success_result -v
python -m pytest tests/test_unified_api.py::TestShouChaoAPI -v
python -m pytest tests/test_unified_api.py -k "test_list_sources" -v
```

### Running All Tests
```bash
python -m pytest tests/ -v
```

### Type Checking (if mypy is installed)
```bash
python -m mypy shouchao --ignore-missing-imports
```

### Building the Package
```bash
python -m build
```

## Code Style Guidelines

### Imports

Group imports in this order, separated by blank lines:
1. Standard library imports (alphabetically)
2. Third-party imports (alphabetically)
3. Local imports (alphabetically)

```python
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from flask import Flask

from shouchao.core.config import CONFIG, load_config
from shouchao.core.sources import get_sources
```

Use explicit imports rather than `from module import *`.

### Naming Conventions

- **Modules**: snake_case (`config.py`, `ollama_client.py`, `web_search.py`, `tts.py`)
- **Classes**: PascalCase (`ToolResult`, `NewsSource`, `RateLimiter`, `WebSearchEngine`)
- **Functions**: snake_case (`fetch_news`, `create_fetcher`, `get_proxies`, `web_search`)
- **Variables**: snake_case (`all_articles`, `source_type`)
- **Constants**: UPPER_SNAKE_CASE (`BROWSER_HEADERS`, `DEFAULT_UA`, `DATA_DIR`)
- **Private functions**: prefix with underscore (`_extract_article_links`, `_build_main_parser`)
- **Type variables**: PascalCase with suffix (e.g., `SourceType`)

### Type Hints

Use type hints for all function signatures:

```python
def fetch_news(
    *,
    language: Optional[str] = None,
    source: Optional[str] = None,
    max_articles: int = 50,
) -> ToolResult:
    ...

def search(self, query: str, language: Optional[str] = None, top_k: int = 10) -> list[dict]:
    ...
```

- Use `Optional[T]` for optional parameters (not `T | None` for Python 3.10 compatibility)
- Use `list[T]`, `dict[K, V]`, `tuple[T1, T2]` for generic types
- Use `from typing import ...` for typing utilities

### Keyword-Only Arguments

All public API functions use keyword-only arguments with the `*,` pattern:

```python
def fetch_news(
    *,
    language: Optional[str] = None,
    max_articles: int = 50,
) -> ToolResult:
```

This makes the API self-documenting and prevents positional argument errors.

### Docstrings

Use triple-quoted docstrings for modules, classes, and public functions:

```python
def fetch_news(*, language: Optional[str] = None) -> ToolResult:
    """Fetch news articles from configured sources.

    Args:
        language: Filter by language code (e.g. "en", "zh"). None = all.
        max_articles: Maximum articles to fetch per source.

    Returns:
        ToolResult with data={"fetched": N, "articles": [...]}.
    """
```

### Error Handling

The codebase uses a `ToolResult` pattern for consistent error handling:

```python
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

All public API functions return `ToolResult`:

```python
try:
    result = do_something()
    return ToolResult(success=True, data=result)
except Exception as e:
    return ToolResult(success=False, error=str(e))
```

Never raise exceptions from public API functions - catch and return ToolResult.

### Dataclasses

Use `@dataclass` for data structures:

```python
@dataclass
class Config:
    ollama_url: str = "http://localhost:11434"
    language: str = "zh"
    fetch_delay: float = 1.0
```

### Logging

Use module-level loggers:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Fetching URL: %s", url)
logger.info("Process completed")
logger.warning("Failed to load config: %s", e)
logger.error("Request failed: %s", e)
```

### File Organization

- `shouchao/__init__.py` - Package exports, lazy imports via `__getattr__`
- `shouchao/api.py` - Public Python API, all functions return ToolResult
- `shouchao/cli.py` - CLI interface with subcommands
- `shouchao/tools.py` - OpenAI function-calling tool definitions
- `shouchao/core/` - Core business logic modules
  - `web_search.py` - Multi-engine web search (DuckDuckGo, Google, Bing, Brave)
  - `tts.py` - Text-to-speech (edge-tts, pyttsx3, gtts, sherpa-onnx)
  - `exporter.py` - Document export (PDF, EPUB, DOCX, HTML, Audio)
- `tests/` - Test files, one test class per feature area

### Test Patterns

Test files follow pytest conventions:

```python
class TestToolResult:
    def test_success_result(self):
        from shouchao.api import ToolResult
        r = ToolResult(success=True, data={"key": "value"})
        assert r.success is True

    def test_failure_result(self):
        r = ToolResult(success=False, error="something broke")
        assert r.error == "something broke"
```

- Test class names: `Test<FeatureName>`
- Test method names: `test_<description>`
- Use `from shouchao.api import ...` for imports inside tests
- Use `pytest.raises` for expected exceptions
- Use `unittest.mock.patch` for mocking

### Configuration

- Config stored in `~/.shouchao/shouchao_config.json`
- Use `DATA_DIR`, `NEWS_DIR`, `CHROMA_DIR` from `shouchao.core.config`
- Call `ensure_dirs()` before file operations
- Call `load_config()` at the start of CLI commands

### Code Formatting

- Line length: ~100 characters (soft limit)
- Indentation: 4 spaces
- Blank lines: 2 between top-level definitions, 1 between methods
- Trailing commas in multi-line structures

## Key Architectural Patterns

### ToolResult Pattern

All public functions return `ToolResult`:

```python
from shouchao.api import ToolResult

def my_function(*, param: str) -> ToolResult:
    try:
        result = _do_work(param)
        return ToolResult(
            success=True,
            data=result,
            metadata={"version": __version__}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))
```

### Lazy Imports in `__init__.py`

```python
def __getattr__(name):
    if name == "fetch_news":
        from shouchao.api import fetch_news
        return fetch_news
    raise AttributeError(f"module 'shouchao' has no attribute {name!r}")
```

### CLI Subcommand Pattern

Each subcommand has its own function and parser:

```python
def cmd_fetch():
    parser = argparse.ArgumentParser(prog="shouchao fetch")
    _parse_common_flags(parser)
    parser.add_argument("--language", "-l")
    args = parser.parse_args()
    _setup_logging(args.verbose, args.quiet)
    from shouchao.api import fetch_news
    result = fetch_news(language=args.language)
```

## New Features in v0.2.0

### Web Search API

```python
from shouchao import web_search

result = web_search(
    query="AI news",
    engines=["duckduckgo", "brave"],
    num_results=10,
    language="en",
)
```

### Text-to-Speech API

```python
from shouchao import text_to_speech

result = text_to_speech(
    text="Hello, this is a test.",
    engine="edge-tts",  # or "pyttsx3", "gtts"
    language="en",
)
# Audio saved to result.data["audio_path"]
```

### Export API

```python
from shouchao import export_document

result = export_document(
    content="# My Document\n\nContent here...",
    title="My Document",
    output_path="output.pdf",
    format="pdf",  # or "epub", "docx", "html", "md"
)
```

### Keyword Search & Summarize

```python
from shouchao import keyword_search_and_summarize

result = keyword_search_and_summarize(
    keywords=["AI", "machine learning", "neural networks"],
    scenario="investment",
    max_results=10,
)
# result.data["results"] contains search results
# result.data["summary"] contains AI-generated summary
```

### Content Summarization

```python
from shouchao import summarize_content

# Summarize content in any language to any target language
result = summarize_content(
    content="Long article content here...",
    target_language="zh",  # Output language
    style="detailed",  # brief, detailed, bullet, executive, story
)
# result.data["summary"] contains the summary
```

### Get TTS Voices

```python
from shouchao import get_tts_voices

result = get_tts_voices(
    engine="edge-tts",
    language="en",
)
# result.data["voices"] contains list of available voices
```

### Summarize and Speak (One-step)

```python
from shouchao import summarize_and_speak

# Summarize content and convert to speech
result = summarize_and_speak(
    content="Article to summarize and speak...",
    target_language="en",
    style="story",  # Best for TTS
    tts_engine="edge-tts",
)
# result.data["summary"] contains the summary
# result.data["audio_path"] contains path to audio file
```

## Proxy Configuration

All interfaces support proxy settings:

```python
from shouchao.core.config import CONFIG, get_proxies, test_proxy_connection

# Set proxy mode: "none", "system", "manual"
CONFIG.proxy_mode = "manual"
CONFIG.proxy_http = "127.0.0.1:7890"
CONFIG.proxy_https = "127.0.0.1:7890"
CONFIG.proxy_socks5 = "127.0.0.1:1080"  # Optional SOCKS5
CONFIG.proxy_username = "user"  # Optional auth
CONFIG.proxy_password = "pass"  # Optional auth

# Get proxies for requests library
proxies = get_proxies()  # Returns {"http": "...", "https": "..."}

# Test proxy connection
result = test_proxy_connection()  # Returns {"success": True/False, "response_time_ms": 100}
```

## Dependencies

### Core Dependencies
- requests, beautifulsoup4, html2text, feedparser
- flask, flask-cors
- chromadb
- rich (for CLI output)

### Optional Dependencies
- curl-cffi: HTTP with TLS fingerprint impersonation
- DrissionPage: Browser automation with system Chrome
- playwright: Headless Chromium for JS rendering
- readability-lxml: Better content extraction
- duckduckgo-search: DuckDuckGo web search
- edge-tts: Microsoft Edge TTS (high quality, free)
- pyttsx3: Offline TTS
- gtts: Google Translate TTS
- weasyprint: PDF export
- ebooklib: EPUB export
- python-docx: DOCX export
- markdown: Markdown to HTML conversion
- pydub: Audio processing

### Development Dependencies
- pytest>=7.0
- build, twine (for PyPI publishing)