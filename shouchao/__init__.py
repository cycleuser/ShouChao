"""
ShouChao (手抄) - Web Information Retrieval Assistant

Aggregates news from major media sites across 10 languages,
converts to markdown, indexes into ChromaDB, and provides
AI-powered briefings and analysis.
"""

__version__ = "0.1.1"


def __getattr__(name):
    if name == "ToolResult":
        from shouchao.api import ToolResult
        return ToolResult
    if name == "fetch_news":
        from shouchao.api import fetch_news
        return fetch_news
    if name == "search_news":
        from shouchao.api import search_news
        return search_news
    if name == "generate_briefing":
        from shouchao.api import generate_briefing
        return generate_briefing
    if name == "analyze_news":
        from shouchao.api import analyze_news
        return analyze_news
    if name == "index_news":
        from shouchao.api import index_news
        return index_news
    if name == "list_sources":
        from shouchao.api import list_sources
        return list_sources
    raise AttributeError(f"module 'shouchao' has no attribute {name!r}")


__all__ = [
    "__version__",
    "ToolResult",
    "fetch_news",
    "search_news",
    "generate_briefing",
    "analyze_news",
    "index_news",
    "list_sources",
]
