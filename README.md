# ShouChao (守巢) - Global News Intelligence Platform

Aggregates news from 100+ major media sources across 10 languages, converts articles to structured markdown, indexes them into a ChromaDB knowledge base, and provides AI-powered briefings and analysis for investment, immigration, and study abroad scenarios.

## Features

- **10-Language Coverage**: Chinese, English, Japanese, French, Russian, German, Italian, Spanish, Portuguese, Korean
- **100+ News Sources**: Reuters, BBC, NHK, Le Monde, TASS, DW, ANSA, El Pais, Folha, Yonhap, and many more
- **Multiple Fetcher Backends**: requests, curl_cffi, DrissionPage, Playwright with human-like browsing behavior
- **RSS + Web Scraping**: RSS feeds for efficient discovery, web scraping for full articles
- **Markdown Storage**: Articles saved as `{lang}/{site}/{date}/{title}.md` with YAML front matter
- **ChromaDB Knowledge Base**: GangDan-compatible vector database for semantic search
- **AI Analysis**: Investment, immigration, study abroad, and general news analysis via Ollama
- **News Briefings**: Daily, weekly, and domain-specific briefings with LLM summarization
- **Three Interfaces**: CLI, GUI (tkinter), and Web (Flask) dashboard
- **i18n**: Full 10-language UI support

## Requirements

- Python >= 3.10
- [Ollama](https://ollama.ai) (for AI features: analysis, briefings, semantic search)

## Installation

```bash
pip install shouchao
```

Or install from source:

```bash
git clone https://github.com/cycleuser/ShouChao.git
cd ShouChao
pip install -e .
```

### Optional dependencies

```bash
pip install shouchao[all]        # All optional fetchers + readability
pip install shouchao[curl]       # curl_cffi for better bot evasion
pip install shouchao[browser]    # DrissionPage (system Chrome)
pip install shouchao[readability] # Better content extraction
```

## Quick Start

```bash
# List available news sources
shouchao sources --language en

# Fetch news articles
shouchao fetch --language en --max 10

# Search indexed news
shouchao search "AI regulation"

# Generate a daily briefing (requires Ollama)
shouchao briefing --type daily

# Analyze news for investment impact (requires Ollama)
shouchao analyze "EU policy changes" --scenario investment

# Start web dashboard
shouchao web --port 5001

# Launch GUI
shouchao gui
```

## Usage

### CLI Options

| Command | Description |
|---------|-------------|
| `shouchao fetch` | Fetch news from sources |
| `shouchao search "query"` | Search indexed news |
| `shouchao briefing` | Generate news briefings |
| `shouchao analyze "query"` | Analyze news for scenarios |
| `shouchao index` | Index articles into ChromaDB |
| `shouchao sources` | List/manage news sources |
| `shouchao config` | View/update configuration |
| `shouchao web` | Start Flask web server |
| `shouchao gui` | Launch tkinter GUI |

### Global Flags

| Flag | Description |
|------|-------------|
| `-V, --version` | Show version |
| `-v, --verbose` | Verbose output |
| `--json` | JSON output |
| `-q, --quiet` | Suppress non-essential output |
| `--data-dir PATH` | Custom data directory |

### Fetch Examples

```bash
shouchao fetch --language zh --max 20              # Chinese news
shouchao fetch --language en --source "Reuters"     # Specific source
shouchao fetch --fetcher curl                       # Use curl_cffi backend
shouchao fetch --language ja,ko --max 5             # Multiple languages
```

### Analysis Scenarios

```bash
shouchao analyze "Impact of new EU AI Act" --scenario investment
shouchao analyze "Canada immigration policy 2026" --scenario immigration
shouchao analyze "UK university tuition changes" --scenario study_abroad
shouchao analyze "Global semiconductor trends" --scenario general
```

## Python API

```python
from shouchao import fetch_news, search_news, analyze_news, list_sources

# List sources
result = list_sources(language="en")
print(result.data["count"])  # Number of English sources

# Fetch news
result = fetch_news(language="en", max_articles=10)
print(result.data["fetched"])  # Articles fetched

# Search
result = search_news(query="climate change", top_k=5)
for r in result.data["results"]:
    print(r["metadata"]["title"])

# Analyze
result = analyze_news(query="market trends", scenario="investment")
print(result.data["content"])
```

## Agent Integration (OpenAI Function Calling)

ShouChao exposes OpenAI-compatible tools for LLM agents:

```python
from shouchao.tools import TOOLS, dispatch

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=TOOLS,
)

result = dispatch(
    tool_call.function.name,
    tool_call.function.arguments,
)
```

## CLI Help

![CLI Help](images/shouchao_help.png)

## Project Structure

```
shouchao/
├── core/
│   ├── config.py        # Configuration management
│   ├── sources.py       # 100+ news source registry
│   ├── fetcher.py       # HTTP fetcher backends
│   ├── rss.py           # RSS/Atom feed parser
│   ├── converter.py     # HTML-to-Markdown pipeline
│   ├── storage.py       # Article file storage
│   ├── indexer.py       # ChromaDB indexer
│   ├── ollama_client.py # Ollama API client
│   ├── analyzer.py      # LLM analysis engine
│   └── briefing.py      # Briefing generator
├── cli.py               # CLI interface
├── gui.py               # Tkinter GUI
├── app.py               # Flask web server
├── api.py               # Python API
├── tools.py             # OpenAI tools
└── i18n.py              # 10-language translations
```

## Development

```bash
git clone https://github.com/cycleuser/ShouChao.git
cd ShouChao
pip install -e ".[dev]"
python -m pytest tests/test_unified_api.py -v
```

## License

GPL-3.0-or-later
