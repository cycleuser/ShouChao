"""
OpenAI function-calling tool definitions for ShouChao.
"""

import json
from typing import Any

TOOLS = [
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


def dispatch(name: str, arguments: dict[str, Any] | str) -> dict:
    """Dispatch a tool call to the corresponding API function."""
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    if name == "shouchao_fetch_news":
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
