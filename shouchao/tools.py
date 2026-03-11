"""
OpenAI function-calling tool definitions for ShouChao.
"""

import json
from typing import Any

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "shouchao_web_search",
            "description": (
                "Search the web using multiple search engines (DuckDuckGo, Google, "
                "Bing, Brave). Returns aggregated results from all engines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "engines": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of engines to use (duckduckgo, google, bing, brave)",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Maximum results per engine",
                        "default": 10,
                    },
                    "language": {
                        "type": "string",
                        "description": "Language filter for results",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_text_to_speech",
            "description": (
                "Convert text to speech audio using various TTS engines. "
                "Supports offline (pyttsx3) and online (edge-tts, gtts) synthesis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech",
                    },
                    "engine": {
                        "type": "string",
                        "description": "TTS engine to use",
                        "enum": ["edge-tts", "gtts", "pyttsx3"],
                        "default": "edge-tts",
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice ID to use",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code for voice selection",
                    },
                    "rate": {
                        "type": "number",
                        "description": "Speech rate multiplier",
                        "default": 1.0,
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_export_document",
            "description": (
                "Export content to various document formats including PDF, "
                "EPUB, DOCX, HTML, and Markdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to export (Markdown format)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["pdf", "epub", "docx", "html", "md"],
                        "default": "pdf",
                    },
                },
                "required": ["content", "title", "output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_keyword_search_and_summarize",
            "description": (
                "Search web for multiple keywords and generate an AI-powered "
                "summary of the combined results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords to search",
                    },
                    "scenario": {
                        "type": "string",
                        "description": "Analysis scenario",
                        "enum": ["general", "investment", "immigration", "study_abroad"],
                        "default": "general",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results per keyword",
                        "default": 10,
                    },
                },
                "required": ["keywords"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_fetch_news",
            "description": (
                "Fetch news articles from global media sources across "
                "10 languages. Supports RSS feeds and web reading with "
                "human-like browsing behavior for assisted reading."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Language code to filter sources (e.g. 'en', 'zh', 'ja')",
                    },
                    "source": {
                        "type": "string",
                        "description": "Specific source name (e.g. 'Reuters', 'BBC News')",
                    },
                    "max_articles": {
                        "type": "integer",
                        "description": "Maximum articles to fetch per source",
                        "default": 50,
                    },
                    "fetcher": {
                        "type": "string",
                        "description": "HTTP backend to use",
                        "enum": ["requests", "curl", "browser", "playwright"],
                        "default": "requests",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_search_news",
            "description": (
                "Semantic search across indexed news articles using "
                "vector similarity in ChromaDB."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter results by language code",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_generate_briefing",
            "description": (
                "Generate a news briefing (daily, weekly, or domain-specific) "
                "summarizing recent news by category."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "briefing_type": {
                        "type": "string",
                        "description": "Type of briefing to generate",
                        "enum": ["daily", "weekly", "domain"],
                        "default": "daily",
                    },
                    "language": {
                        "type": "string",
                        "description": "Output language code",
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Category tags to filter",
                    },
                    "date": {
                        "type": "string",
                        "description": "Target date in YYYY-MM-DD format",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_analyze_news",
            "description": (
                "Analyze current news for specific scenarios: investment "
                "opportunities, immigration policy, study abroad decisions, "
                "or general analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Analysis query or topic",
                    },
                    "scenario": {
                        "type": "string",
                        "description": "Analysis scenario",
                        "enum": ["investment", "immigration", "study_abroad", "general"],
                        "default": "general",
                    },
                    "language": {
                        "type": "string",
                        "description": "Output language code",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_index_news",
            "description": (
                "Index news articles into the ChromaDB knowledge base "
                "for semantic search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to index",
                    },
                    "collection": {
                        "type": "string",
                        "description": "ChromaDB collection name",
                        "default": "shouchao_news",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shouchao_list_sources",
            "description": (
                "List available news sources with their language, "
                "type (RSS/web), and categories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Filter by language code",
                    },
                    "source_type": {
                        "type": "string",
                        "description": "Filter by source type",
                        "enum": ["rss", "web"],
                    },
                },
                "required": [],
            },
        },
    },
]


def dispatch(name: str, arguments: Any) -> dict:
    """Dispatch a tool call to the corresponding API function."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if name == "shouchao_web_search":
        from shouchao.api import web_search
        return web_search(**arguments).to_dict()
    elif name == "shouchao_text_to_speech":
        from shouchao.api import text_to_speech
        return text_to_speech(**arguments).to_dict()
    elif name == "shouchao_export_document":
        from shouchao.api import export_document
        return export_document(**arguments).to_dict()
    elif name == "shouchao_keyword_search_and_summarize":
        from shouchao.api import keyword_search_and_summarize
        return keyword_search_and_summarize(**arguments).to_dict()
    elif name == "shouchao_fetch_news":
        from shouchao.api import fetch_news
        return fetch_news(**arguments).to_dict()
    elif name == "shouchao_search_news":
        from shouchao.api import search_news
        return search_news(**arguments).to_dict()
    elif name == "shouchao_generate_briefing":
        from shouchao.api import generate_briefing
        return generate_briefing(**arguments).to_dict()
    elif name == "shouchao_analyze_news":
        from shouchao.api import analyze_news
        return analyze_news(**arguments).to_dict()
    elif name == "shouchao_index_news":
        from shouchao.api import index_news
        return index_news(**arguments).to_dict()
    elif name == "shouchao_list_sources":
        from shouchao.api import list_sources
        return list_sources(**arguments).to_dict()
    else:
        raise ValueError(f"Unknown tool: {name}")
