"""
ShouChao (手抄) - Web Information Retrieval Assistant

Aggregates news from major media sites across 10 languages,
converts to markdown, indexes into ChromaDB, and provides
AI-powered briefings and analysis.

Now includes preprint server support (arXiv, bioRxiv, medRxiv).
"""

__version__ = "0.3.1"


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
    if name == "web_search":
        from shouchao.api import web_search
        return web_search
    if name == "text_to_speech":
        from shouchao.api import text_to_speech
        return text_to_speech
    if name == "export_document":
        from shouchao.api import export_document
        return export_document
    if name == "keyword_search_and_summarize":
        from shouchao.api import keyword_search_and_summarize
        return keyword_search_and_summarize
    if name == "summarize_content":
        from shouchao.api import summarize_content
        return summarize_content
    if name == "get_tts_voices":
        from shouchao.api import get_tts_voices
        return get_tts_voices
    if name == "summarize_and_speak":
        from shouchao.api import summarize_and_speak
        return summarize_and_speak
    # Preprint functions
    if name == "fetch_preprints":
        from shouchao.api import fetch_preprints
        return fetch_preprints
    if name == "search_preprints":
        from shouchao.api import search_preprints
        return search_preprints
    if name == "index_preprints":
        from shouchao.api import index_preprints
        return index_preprints
    if name == "get_preprint_categories":
        from shouchao.api import get_preprint_categories
        return get_preprint_categories
    # Polish function
    if name == "polish_briefing":
        from shouchao.api import polish_briefing
        return polish_briefing
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
    "web_search",
    "text_to_speech",
    "export_document",
    "keyword_search_and_summarize",
    "summarize_content",
    "get_tts_voices",
    "summarize_and_speak",
    # Preprint functions
    "fetch_preprints",
    "search_preprints",
    "index_preprints",
    "get_preprint_categories",
    # Polish function
    "polish_briefing",
]
