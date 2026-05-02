"""
Unified Python API for ShouChao.

All public functions return ToolResult and use keyword-only arguments.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result type for all API functions."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


def web_search(
    *,
    query: str,
    engines: Optional[list[str]] = None,
    num_results: int = 10,
    language: Optional[str] = None,
) -> ToolResult:
    """Search the web using multiple search engines.

    Args:
        query: Search query string.
        engines: List of engines to use (duckduckgo, google, bing, brave, searxng).
        num_results: Maximum results per engine.
        language: Language filter for results.

    Returns:
        ToolResult with search results.
    """
    try:
        from shouchao import __version__
        from shouchao.core.web_search import WebSearchEngine

        search_engine = WebSearchEngine()
        response = search_engine.search(
            query=query,
            engines=engines or ["duckduckgo"],
            num_results=num_results,
            language=language,
        )

        return ToolResult(
            success=True,
            data=response.to_dict(),
            metadata={"version": __version__, "engine": response.engine},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def text_to_speech(
    *,
    text: str,
    output_path: Optional[str] = None,
    engine: Optional[str] = None,
    voice: Optional[str] = None,
    language: Optional[str] = None,
    rate: float = 1.0,
) -> ToolResult:
    """Convert text to speech audio.

    Args:
        text: Text to convert to speech.
        output_path: Output audio file path (auto-generated if None).
        engine: TTS engine (edge-tts, pyttsx3, gtts, sherpa-onnx).
        voice: Voice ID to use.
        language: Language code for voice selection.
        rate: Speech rate multiplier (1.0 = normal).

    Returns:
        ToolResult with audio file path.
    """
    try:
        from shouchao import __version__
        from shouchao.core.tts import TTSEngine

        tts = TTSEngine(preferred_engine=engine)
        result = tts.synthesize(
            text=text,
            output_path=output_path,
            voice=voice,
            language=language,
            rate=rate,
        )

        return ToolResult(
            success=result.success,
            data={
                "audio_path": result.audio_path,
                "duration": result.duration,
                "engine": result.engine,
            },
            error=result.error,
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def export_document(
    *,
    content: str,
    title: str,
    output_path: str,
    format: str = "pdf",
    language: Optional[str] = None,
) -> ToolResult:
    """Export content to various document formats.

    Args:
        content: Content to export (Markdown format).
        title: Document title.
        output_path: Output file path.
        format: Export format (pdf, epub, docx, html, md, audio).
        language: Language for audio export.

    Returns:
        ToolResult with export status and file path.
    """
    try:
        from shouchao import __version__
        from shouchao.core.exporter import Exporter

        exporter = Exporter()
        result = exporter.export(
            content=content,
            title=title,
            output_path=output_path,
            format=format,
            metadata={"language": language} if language else None,
        )

        return ToolResult(
            success=result.success,
            data={
                "output_path": result.output_path,
                "file_size": result.file_size,
                "format": result.format,
            },
            error=result.error,
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def keyword_search_and_summarize(
    *,
    keywords: list[str],
    engines: Optional[list[str]] = None,
    language: Optional[str] = None,
    scenario: str = "general",
    max_results: int = 10,
) -> ToolResult:
    """Search web for keywords and generate AI summary.

    Args:
        keywords: List of keywords to search.
        engines: Search engines to use.
        language: Language filter.
        scenario: Analysis scenario (general, investment, immigration, study_abroad).
        max_results: Maximum results per keyword.

    Returns:
        ToolResult with combined search results and AI summary.
    """
    try:
        from shouchao import __version__
        from shouchao.core.web_search import WebSearchEngine
        from shouchao.core.config import CONFIG, load_config

        load_config()

        search_engine = WebSearchEngine()
        all_results = []
        query_parts = []

        for keyword in keywords:
            response = search_engine.search(
                query=keyword,
                engines=engines or ["duckduckgo"],
                num_results=max_results,
                language=language,
            )
            if response.results:
                all_results.extend(response.results)
                query_parts.append(keyword)

        combined_query = " ".join(query_parts)

        summary = None
        if all_results and CONFIG.ollama_url:
            try:
                from shouchao.core.ollama_client import OllamaClient
                from shouchao.core.summarizer import ContentSummarizer

                ollama = OllamaClient(CONFIG.ollama_url)
                summarizer = ContentSummarizer(ollama)

                context = "\n\n".join([
                    f"**{r.title}**\n{r.snippet}\nSource: {r.source}"
                    for r in all_results[:10]
                ])

                summary = summarizer.summarize_complete(
                    content=context,
                    target_language=language or CONFIG.language,
                    style="detailed",
                )
            except Exception as e:
                logger.warning(f"Failed to generate summary: {e}")

        return ToolResult(
            success=True,
            data={
                "keywords": keywords,
                "results": [r.to_dict() for r in all_results[:max_results * len(keywords)]],
                "total": len(all_results),
                "summary": summary,
            },
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def summarize_content(
    *,
    content: str,
    target_language: str = "en",
    style: str = "detailed",
    source_language: Optional[str] = None,
    max_length: Optional[int] = None,
) -> ToolResult:
    """Summarize content with AI, supporting language translation.

    Args:
        content: The content to summarize.
        target_language: Target language for the summary (e.g., "en", "zh").
        style: Summary style ("brief", "detailed", "bullet", "executive", "story").
        source_language: Source language (auto-detected if None).
        max_length: Maximum length in words (optional).

    Returns:
        ToolResult with the summary.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.summarizer import ContentSummarizer, SUMMARY_STYLES

        load_config()

        if style not in SUMMARY_STYLES:
            style = "detailed"

        ollama = OllamaClient(CONFIG.ollama_url)
        summarizer = ContentSummarizer(ollama)

        if source_language and source_language != target_language:
            summary = summarizer.translate_and_summarize_complete(
                content=content,
                source_language=source_language,
                target_language=target_language,
                style=style,
            )
        else:
            summary = summarizer.summarize_complete(
                content=content,
                target_language=target_language,
                style=style,
                max_length=max_length,
            )

        return ToolResult(
            success=True,
            data={
                "summary": summary,
                "target_language": target_language,
                "style": style,
            },
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def get_tts_voices(
    *,
    engine: str = "edge-tts",
    language: Optional[str] = None,
) -> ToolResult:
    """Get available TTS voices for an engine.

    Args:
        engine: TTS engine name (edge-tts, pyttsx3, gtts).
        language: Filter voices by language.

    Returns:
        ToolResult with list of available voices.
    """
    try:
        from shouchao import __version__
        from shouchao.core.tts import TTSEngine

        tts = TTSEngine(preferred_engine=engine)
        voices = tts.get_voices(engine=engine, language=language)

        return ToolResult(
            success=True,
            data={
                "engine": engine,
                "voices": [v.to_dict() for v in voices],
                "count": len(voices),
            },
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def summarize_and_speak(
    *,
    content: str,
    target_language: str = "en",
    style: str = "story",
    voice: Optional[str] = None,
    tts_engine: str = "edge-tts",
    output_path: Optional[str] = None,
) -> ToolResult:
    """Summarize content and convert to speech in one step.

    This is optimized for creating audio briefings - uses "story" style
    by default which produces narrative summaries ideal for TTS.

    Args:
        content: Content to summarize.
        target_language: Target language for summary and speech.
        style: Summary style (default: "story" for TTS).
        voice: Specific voice ID to use.
        tts_engine: TTS engine (edge-tts, gtts, pyttsx3).
        output_path: Output audio file path (auto-generated if None).

    Returns:
        ToolResult with audio path and summary.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.summarizer import ContentSummarizer
        from shouchao.core.tts import TTSEngine

        load_config()

        ollama = OllamaClient(CONFIG.ollama_url)
        summarizer = ContentSummarizer(ollama)

        summary = summarizer.summarize_complete(
            content=content,
            target_language=target_language,
            style=style,
        )

        tts = TTSEngine(preferred_engine=tts_engine)

        if not voice:
            voices = tts.get_voices(engine=tts_engine, language=target_language)
            if voices:
                voice = voices[0].id

        tts_result = tts.synthesize(
            text=summary,
            output_path=output_path,
            engine=tts_engine,
            voice=voice,
            language=target_language,
        )

        return ToolResult(
            success=tts_result.success,
            data={
                "summary": summary,
                "audio_path": tts_result.audio_path,
                "duration": tts_result.duration,
                "voice": voice,
                "engine": tts_engine,
            },
            error=tts_result.error,
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def fetch_news(
    *,
    language: Optional[str] = None,
    source: Optional[str] = None,
    max_articles: int = 50,
    fetcher: str = "requests",
    force_refresh: bool = False,
) -> ToolResult:
    """Fetch news articles from configured sources.

    Args:
        language: Filter by language code (e.g. "en", "zh"). None = all.
        source: Specific source name to fetch from. None = all enabled.
        max_articles: Maximum articles to fetch per source.
        fetcher: Fetcher backend ("requests", "curl", "browser", "playwright").
        force_refresh: Ignore dedup and fetch all (for fresh content).

    Returns:
        ToolResult with data={"fetched": N, "articles": [...]}.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config, get_proxies, ensure_dirs
        from shouchao.core.sources import get_sources, SourceType
        from shouchao.core.fetcher import create_fetcher, RateLimiter
        from shouchao.core.rss import fetch_feed
        from shouchao.core.converter import html_to_markdown
        from shouchao.core.storage import ArticleStorage

        load_config()
        ensure_dirs()

        proxy = get_proxies()
        proxy_str = proxy.get("https") if proxy else None

        storage = ArticleStorage()
        rate_limiter = RateLimiter(CONFIG.fetch_delay)

        # Get sources
        sources = get_sources(language=language)
        if source:
            sources = [s for s in sources if s.name.lower() == source.lower()]

        # Also include preprint sources if no language specified
        if language is None:
            preprint_sources = get_sources(language="preprint")
            sources = sources + preprint_sources

        if not sources:
            return ToolResult(
                success=True,
                data={"fetched": 0, "articles": []},
                metadata={"version": __version__},
            )

        http_fetcher = create_fetcher(fetcher, proxy=proxy_str)
        all_articles = []
        seen_urls = set()

        logger.info(f"Starting fetch: language={language}, source={source}, max={max_articles}, fetcher={fetcher}")
        
        try:
            for src in sources:
                if len(all_articles) >= max_articles * len(sources):
                    break

                article_urls = []

                # RSS path: discover article URLs
                if src.source_type == SourceType.RSS and src.rss_url:
                    entries = fetch_feed(src.rss_url, proxy=proxy)
                    for entry in entries[:max_articles]:
                        article_urls.append({
                            "url": entry.url,
                            "title": entry.title,
                            "date": entry.date_str,
                        })
                else:
                    # Web path: fetch listing page and discover links
                    rate_limiter.wait(src.url)
                    html, err = http_fetcher.fetch(src.url)
                    if err or not html:
                        continue
                    # Extract article links from listing page
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    links = _extract_article_links(
                        soup, src.url, src.article_selector
                    )
                    from datetime import datetime
                    today = datetime.now().strftime("%Y-%m-%d")
                    for link_url, link_title in links[:max_articles]:
                        article_urls.append({
                            "url": link_url,
                            "title": link_title or "Untitled",
                            "date": today,
                        })

                # Fetch each article
                for info in article_urls:
                    url = info["url"]
                    title = info["title"]
                    date = info["date"]

                    if storage.article_exists(
                        src.language, src.name, date, title
                    ):
                        continue

                    rate_limiter.wait(url)
                    html, err = http_fetcher.fetch(url)
                    if err or not html:
                        continue

                    md_content, meta = html_to_markdown(html, url)

                    # Use extracted title if better
                    if meta.get("title"):
                        title = meta["title"]

                    # Add source metadata
                    meta["website"] = src.name
                    meta["language"] = src.language

                    # Rebuild front matter with updated metadata
                    from shouchao.core.converter import format_front_matter
                    meta_copy = dict(meta)
                    meta_copy["website"] = src.name
                    meta_copy["language"] = src.language
                    if "category" not in meta_copy:
                        meta_copy["category"] = ", ".join(src.category)

                    # Replace front matter
                    if md_content.startswith("---"):
                        end = md_content.find("---", 3)
                        if end > 0:
                            body = md_content[end + 3:]
                            md_content = format_front_matter(meta_copy) + body

                    path = storage.save_article(
                        src.language, src.name, date, title, md_content,
                    )
                    all_articles.append({
                        "path": str(path),
                        "title": title,
                        "source": src.name,
                        "language": src.language,
                        "date": date,
                        "url": url,
                    })
        finally:
            http_fetcher.close()

        return ToolResult(
            success=True,
            data={"fetched": len(all_articles), "articles": all_articles},
            metadata={"version": __version__},
        )

    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"version": __version__},
        )


def search_news(
    *,
    query: str,
    language: Optional[str] = None,
    top_k: int = 10,
) -> ToolResult:
    """Semantic search across indexed news articles.

    Args:
        query: Search query text.
        language: Filter by language. None = all.
        top_k: Maximum results to return.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        results = indexer.search_news(query, language=language, top_k=top_k)

        return ToolResult(
            success=True,
            data={"results": results, "count": len(results)},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def generate_briefing(
    *,
    briefing_type: str = "daily",
    language: Optional[str] = None,
    categories: Optional[list[str]] = None,
    date: Optional[str] = None,
    show_source: bool = False,
) -> ToolResult:
    """Generate a news briefing.

    Args:
        briefing_type: "daily", "weekly", or "domain".
        language: Output language code.
        categories: Filter by category tags.
        date: Target date (YYYY-MM-DD). Default: today.
        show_source: Whether to include source attribution in the briefing.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.briefing import BriefingGenerator

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        storage = ArticleStorage()
        generator = BriefingGenerator(ollama, indexer, storage)

        if briefing_type == "weekly":
            chunks = list(generator.generate_weekly(week_start=date, language=language, show_source=show_source))
        elif briefing_type == "domain" and categories:
            chunks = list(generator.generate_domain(
                categories[0], date_from=date, language=language, show_source=show_source,
            ))
        else:
            chunks = list(generator.generate_daily(date, language, categories, show_source))

        content = "".join(chunks)
        return ToolResult(
            success=True,
            data={"content": content, "type": briefing_type},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def generate_briefing_from_articles(
    *,
    article_paths: list[str],
    language: str = "zh",
    show_source: bool = True,
    title: Optional[str] = None,
) -> ToolResult:
    """Generate a briefing from selected articles.

    Args:
        article_paths: List of file paths to selected articles.
        language: Output language code.
        show_source: Whether to include source attribution.
        title: Optional title for the briefing.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.briefing import BriefingGenerator

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        storage = ArticleStorage()
        generator = BriefingGenerator(ollama, indexer, storage)

        chunks = list(generator.generate_from_articles(
            article_paths=article_paths,
            language=language,
            show_source=show_source,
            title=title,
        ))

        content = "".join(chunks)
        return ToolResult(
            success=True,
            data={"content": content, "article_count": len(article_paths)},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def analyze_news(
    *,
    query: str,
    scenario: str = "general",
    language: Optional[str] = None,
) -> ToolResult:
    """Analyze news for a specific scenario.

    Args:
        query: Analysis query.
        scenario: "investment", "immigration", "study_abroad", or "general".
        language: Output language code.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer
        from shouchao.core.analyzer import AnalysisEngine

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        engine = AnalysisEngine(ollama, indexer)

        content = engine.analyze_complete(query, scenario, language)
        return ToolResult(
            success=True,
            data={"content": content, "scenario": scenario},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def index_news(
    *,
    directory: Optional[str] = None,
    collection: str = "shouchao_news",
) -> ToolResult:
    """Index news articles into the knowledge base.

    Args:
        directory: Directory to index. Default: NEWS_DIR.
        collection: ChromaDB collection name.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, NEWS_DIR, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)
        target = directory or str(NEWS_DIR)
        count = indexer.index_directory(target, collection)

        return ToolResult(
            success=True,
            data={"indexed": count, "directory": target, "collection": collection},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def list_sources(
    *,
    language: Optional[str] = None,
    source_type: Optional[str] = None,
) -> ToolResult:
    """List available news sources.

    Args:
        language: Filter by language code.
        source_type: "rss" or "web".
    """
    try:
        from shouchao import __version__
        from shouchao.core.sources import get_sources, SourceType

        st = None
        if source_type:
            st = SourceType(source_type.lower())

        sources = get_sources(language=language, source_type=st)
        data = [s.to_dict() for s in sources]

        return ToolResult(
            success=True,
            data={"sources": data, "count": len(data)},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def fetch_preprints(
    *,
    servers: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> ToolResult:
    """Fetch preprints from arXiv, bioRxiv, and medRxiv.

    Args:
        servers: List of servers ("arxiv", "biorxiv", "medrxiv"). Default: all.
        categories: List of categories (e.g., "cs.AI", "cs.LG", "genomics").
        keywords: Keywords to filter articles.
        max_results: Max results per server.
        date_from: Start date (YYYY-MM-DD). Default: today.
        date_to: End date (YYYY-MM-DD). Default: today.

    Returns:
        ToolResult with fetched and saved preprint info.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, get_proxies, ensure_dirs
        from shouchao.core.preprint import (
            fetch_preprints as _fetch,
            save_preprints as _save,
        )

        ensure_dirs()
        proxy = get_proxies()

        entries = _fetch(
            servers=servers,
            categories=categories,
            keywords=keywords,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
            proxy=proxy,
        )

        saved = _save(entries)

        return ToolResult(
            success=True,
            data={
                "fetched": len(entries),
                "saved": len(saved),
                "preprints": saved,
                "by_source": _count_by_source(entries),
            },
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def search_preprints(
    *,
    query: str,
    mode: str = "keyword",
    top_k: int = 10,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> ToolResult:
    """Search preprints with multiple matching modes.

    Args:
        query: Search query.
        mode: "keyword" (text match), "semantic" (vector search),
              or "model" (LLM ranking).
        top_k: Number of results.
        date_from: Filter by date from.
        date_to: Filter by date to.

    Returns:
        ToolResult with search results.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, load_config, NEWS_DIR
        from shouchao.core.preprint import (
            search_preprints_keyword,
            search_preprints_semantic,
            rank_preprints_with_model,
            PreprintEntry,
        )
        from shouchao.core.storage import ArticleStorage
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()

        # Load preprints from storage
        storage = ArticleStorage()
        articles = storage.list_articles(
            website=None,
            date_from=date_from,
            date_to=date_to,
        )

        # Filter to preprint sources
        preprint_sources = {"arxiv", "biorxiv", "medrxiv"}
        preprint_articles = [
            a for a in articles
            if a.get("website", "").lower() in preprint_sources
        ]

        if mode == "keyword":
            # Build entries from stored articles
            entries = []
            for art in preprint_articles:
                try:
                    content = storage.get_article(art["path"])
                    entry = _parse_article_to_entry(content, art)
                    entries.append(entry)
                except Exception:
                    continue

            results = search_preprints_keyword(
                query=query, entries=entries, top_k=top_k,
            )
            formatted = [
                {
                    "score": score,
                    "title": e.title,
                    "url": e.url,
                    "source": e.source,
                    "date": e.date_str,
                    "authors": e.authors[:3],
                    "categories": e.categories,
                    "abstract": e.abstract[:300],
                }
                for score, e in results
            ]

        elif mode == "semantic":
            ollama = OllamaClient(CONFIG.ollama_url)
            indexer = NewsIndexer(ollama)
            results = indexer.search_news(
                query, collection="preprints", top_k=top_k,
            )
            formatted = results

        elif mode == "model":
            # First get keyword matches, then rank with model
            entries = []
            for art in preprint_articles:
                try:
                    content = storage.get_article(art["path"])
                    entry = _parse_article_to_entry(content, art)
                    entries.append(entry)
                except Exception:
                    continue

            ollama = OllamaClient(CONFIG.ollama_url)
            results = rank_preprints_with_model(
                query=query, entries=entries,
                ollama_client=ollama, top_k=top_k,
            )
            formatted = [
                {
                    "score": score,
                    "title": e.title,
                    "url": e.url,
                    "source": e.source,
                    "date": e.date_str,
                    "authors": e.authors[:3],
                    "categories": e.categories,
                    "abstract": e.abstract[:300],
                }
                for score, e in results
            ]
        else:
            return ToolResult(
                success=False,
                error=f"Unknown search mode: {mode}. Use 'keyword', 'semantic', or 'model'.",
                metadata={"version": __version__},
            )

        return ToolResult(
            success=True,
            data={
                "query": query,
                "mode": mode,
                "results": formatted,
                "count": len(formatted),
            },
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def index_preprints(
    *,
    directory: Optional[str] = None,
    collection: str = "preprints",
) -> ToolResult:
    """Index preprint articles into knowledge base.

    Args:
        directory: Directory to index. Default: preprints subdirectory.
        collection: ChromaDB collection name.
    """
    try:
        from shouchao import __version__
        from shouchao.core.config import CONFIG, NEWS_DIR, load_config
        from shouchao.core.ollama_client import OllamaClient
        from shouchao.core.indexer import NewsIndexer

        load_config()
        ollama = OllamaClient(CONFIG.ollama_url)
        indexer = NewsIndexer(ollama)

        if directory is None:
            directory = str(NEWS_DIR / "en")

        count = indexer.index_directory(directory, collection)

        return ToolResult(
            success=True,
            data={"indexed": count, "directory": directory, "collection": collection},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


def get_preprint_categories(
    *,
    server: Optional[str] = None,
) -> ToolResult:
    """Get available preprint categories.

    Args:
        server: Filter by server ("arxiv", "biorxiv", "medrxiv"). None = all.

    Returns:
        ToolResult with category lists.
    """
    try:
        from shouchao import __version__
        from shouchao.core.preprint import (
            ARXIV_CATEGORIES, BIORXIV_CATEGORIES, MEDRXIV_CATEGORIES,
        )

        result = {}
        if server is None or server == "arxiv":
            result["arxiv"] = ARXIV_CATEGORIES
        if server is None or server == "biorxiv":
            result["biorxiv"] = BIORXIV_CATEGORIES
        if server is None or server == "medrxiv":
            result["medrxiv"] = MEDRXIV_CATEGORIES

        return ToolResult(
            success=True,
            data={"categories": result},
            metadata={"version": __version__},
        )
    except Exception as e:
        from shouchao import __version__
        return ToolResult(
            success=False, error=str(e),
            metadata={"version": __version__},
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_by_source(entries: list) -> dict:
    """Count entries by source."""
    from shouchao.core.preprint import PreprintEntry
    counts = {}
    for e in entries:
        if isinstance(e, PreprintEntry):
            counts[e.source] = counts.get(e.source, 0) + 1
    return counts


def _parse_article_to_entry(content: str, article_info: dict):
    """Parse a stored article markdown to PreprintEntry."""
    from shouchao.core.preprint import PreprintEntry

    title = article_info.get("title", "")
    url = ""
    abstract = ""
    authors = []
    categories = []
    source = article_info.get("website", "")

    # Parse front matter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            fm_block = content[3:end].strip()
            for line in fm_block.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"')
                    if key == "url":
                        url = val
                    elif key == "authors":
                        authors = [a.strip() for a in val.split(",") if a.strip()]
                    elif key == "categories":
                        categories = [c.strip() for c in val.split(",") if c.strip()]
                    elif key == "source":
                        source = val

    # Extract abstract (after "## Abstract" heading)
    abstract_marker = content.find("## Abstract")
    if abstract_marker > 0:
        abstract = content[abstract_marker + 11:].strip()
        # Remove links at the end
        for marker in ("[PDF]", "[Source]"):
            idx = abstract.find(marker)
            if idx > 0:
                abstract = abstract[:idx].strip()

    return PreprintEntry(
        title=title,
        url=url,
        abstract=abstract,
        authors=authors,
        categories=categories,
        source=source,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_article_links(
    soup, base_url: str, selector: Optional[str] = None,
) -> list[tuple[str, str]]:
    """Extract article links from a listing page.

    Returns list of (url, title) tuples.
    """
    from urllib.parse import urljoin, urlparse

    links = []
    seen = set()

    # Use CSS selector if provided
    if selector:
        for el in soup.select(selector):
            a = el if el.name == "a" else el.find("a")
            if a and a.get("href"):
                url = urljoin(base_url, a["href"])
                title = a.get_text(strip=True)
                if url not in seen:
                    seen.add(url)
                    links.append((url, title))
        return links

    # Heuristic: find article links
    base_domain = urlparse(base_url).netloc
    skip_patterns = (
        "/tag/", "/category/", "/author/", "/page/",
        "/search", "/login", "/register", "/about",
        "/contact", "/privacy", "/terms", "#",
        "javascript:", "mailto:", "tel:",
    )
    skip_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
        ".pdf", ".mp4", ".mp3", ".zip", ".css", ".js",
    )

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(p in href.lower() for p in skip_patterns):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.netloc != base_domain:
            continue
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            continue
        # Heuristic: article URLs tend to have longer paths
        path = parsed.path.strip("/")
        if path.count("/") < 1 and len(path) < 10:
            continue
        title = a.get_text(strip=True)
        if len(title) < 5:
            continue
        if url not in seen:
            seen.add(url)
            links.append((url, title))

    return links
