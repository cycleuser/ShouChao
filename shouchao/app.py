"""
Flask web application for ShouChao.

Provides a dashboard with news browsing, briefings, analysis,
search, and settings management with SSE streaming.
"""

import json
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Configure Flask/Werkzeug to use our logging
def _configure_flask_logging():
    """Configure Flask to log to stdout with unified format."""
    import logging
    
    # Get the root logger (configured by cli.py)
    root = logging.getLogger()
    
    # Add werkzeug to root logger if not already present
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers from werkzeug to avoid duplicate logs
    for h in werkzeug_logger.handlers[:]:
        werkzeug_logger.removeHandler(h)
    
    # Use root logger's handlers (stdout StreamHandler)
    werkzeug_logger.propagate = True


def create_app():
    """Create and configure the Flask application."""
    # Configure Flask logging to use our unified logging
    _configure_flask_logging()
    
    from flask import (
        Flask, render_template, request, jsonify, Response,
        stream_with_context,
    )
    from flask_cors import CORS

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    CORS(app)

    from shouchao import __version__
    from shouchao.core.config import CONFIG, load_config, save_config, ensure_dirs
    load_config()
    ensure_dirs()

    # ---- Routes ----

    @app.route("/")
    def index():
        from shouchao.i18n import TRANSLATIONS, LANGUAGES
        from dataclasses import asdict
        return render_template(
            "index.html",
            version=__version__,
            config=asdict(CONFIG),
            translations=TRANSLATIONS,
            languages=LANGUAGES,
            current_lang=CONFIG.language,
        )

    @app.route("/api/news/list")
    def api_news_list():
        language = request.args.get("language")
        website = request.args.get("website")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))

        from shouchao.core.storage import ArticleStorage
        storage = ArticleStorage()
        articles = storage.list_articles(
            language=language, website=website,
            date_from=date_from, date_to=date_to,
        )
        total = len(articles)
        start = (page - 1) * per_page
        return jsonify({
            "articles": articles[start:start + per_page],
            "total": total,
            "page": page,
            "pages": (total + per_page - 1) // per_page,
        })

    @app.route("/api/news/article")
    def api_news_article():
        path = request.args.get("path", "")
        if not path or not Path(path).exists():
            return jsonify({"error": "Article not found"}), 404
        content = Path(path).read_text(encoding="utf-8")
        return jsonify({"content": content, "path": path})

    @app.route("/api/news/fetch", methods=["POST"])
    def api_news_fetch():
        data = request.get_json(silent=True) or {}
        language = data.get("language")
        source = data.get("source")
        max_articles = data.get("max_articles", 20)
        fetcher = data.get("fetcher", "requests")

        def generate():
            yield _sse_data({"status": "started"})
            try:
                from shouchao.api import fetch_news
                result = fetch_news(
                    language=language, source=source,
                    max_articles=max_articles, fetcher=fetcher,
                )
                if result.success:
                    articles = result.data.get("articles", [])
                    yield _sse_data({
                        "status": "complete",
                        "fetched": len(articles),
                        "articles": articles,
                    })
                else:
                    yield _sse_data({"status": "error", "error": result.error})
            except Exception as e:
                yield _sse_data({"status": "error", "error": str(e)})

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
        )

    @app.route("/api/briefing/generate", methods=["POST"])
    def api_briefing_generate():
        data = request.get_json(silent=True) or {}
        briefing_type = data.get("type", "daily")
        language = data.get("language")
        categories = data.get("categories")
        date = data.get("date")

        def generate():
            try:
                from shouchao.core.config import CONFIG as cfg
                from shouchao.core.ollama_client import OllamaClient
                from shouchao.core.indexer import NewsIndexer
                from shouchao.core.storage import ArticleStorage
                from shouchao.core.briefing import BriefingGenerator

                ollama = OllamaClient(cfg.ollama_url)
                indexer = NewsIndexer(ollama)
                storage = ArticleStorage()
                gen = BriefingGenerator(ollama, indexer, storage)

                if briefing_type == "weekly":
                    chunks = gen.generate_weekly(date, language)
                elif briefing_type == "domain" and categories:
                    chunks = gen.generate_domain(
                        categories[0], date_from=date, language=language,
                    )
                else:
                    chunks = gen.generate_daily(date, language, categories)

                for chunk in chunks:
                    yield _sse_data({"content": chunk})
                yield _sse_data({"done": True})
            except Exception as e:
                yield _sse_data({"error": str(e)})

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
        )

    @app.route("/api/briefing/list")
    def api_briefing_list():
        from shouchao.core.config import BRIEFINGS_DIR
        briefings = []
        if BRIEFINGS_DIR.exists():
            for f in sorted(BRIEFINGS_DIR.glob("*.md"), reverse=True):
                briefings.append({
                    "name": f.stem,
                    "path": str(f),
                    "size": f.stat().st_size,
                })
        return jsonify({"briefings": briefings})

    @app.route("/api/analysis", methods=["POST"])
    def api_analysis():
        data = request.get_json(silent=True) or {}
        query = data.get("query", "")
        scenario = data.get("scenario", "general")
        language = data.get("language")

        def generate():
            try:
                from shouchao.core.config import CONFIG as cfg
                from shouchao.core.ollama_client import OllamaClient
                from shouchao.core.indexer import NewsIndexer
                from shouchao.core.analyzer import AnalysisEngine

                ollama = OllamaClient(cfg.ollama_url)
                indexer = NewsIndexer(ollama)
                engine = AnalysisEngine(ollama, indexer)

                for chunk in engine.analyze(query, scenario, language):
                    yield _sse_data({"content": chunk})
                yield _sse_data({"done": True})
            except Exception as e:
                yield _sse_data({"error": str(e)})

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
        )

    @app.route("/api/search", methods=["POST"])
    def api_search():
        data = request.get_json(silent=True) or {}
        query = data.get("query", "")
        language = data.get("language")
        top_k = data.get("top_k", 10)

        from shouchao.api import search_news
        result = search_news(query=query, language=language, top_k=top_k)
        return jsonify(result.to_dict())

    @app.route("/api/sources")
    def api_sources():
        language = request.args.get("language")
        from shouchao.api import list_sources
        result = list_sources(language=language)
        return jsonify(result.to_dict())

    @app.route("/api/sources/toggle", methods=["POST"])
    def api_sources_toggle():
        data = request.get_json(silent=True) or {}
        name = data.get("name", "")
        enabled = data.get("enabled", True)
        from shouchao.core.sources import SOURCE_REGISTRY
        for lang_sources in SOURCE_REGISTRY.values():
            for src in lang_sources:
                if src.name == name:
                    src.enabled = enabled
                    return jsonify({"success": True})
        return jsonify({"success": False, "error": "Source not found"}), 404

    @app.route("/api/settings", methods=["GET", "POST"])
    def api_settings():
        from dataclasses import asdict
        if request.method == "GET":
            return jsonify(asdict(CONFIG))
        data = request.get_json(silent=True) or {}
        for k, v in data.items():
            if hasattr(CONFIG, k):
                current = getattr(CONFIG, k)
                if isinstance(current, bool):
                    v = bool(v)
                elif isinstance(current, int):
                    v = int(v)
                elif isinstance(current, float):
                    v = float(v)
                setattr(CONFIG, k, v)
        save_config()
        return jsonify({"success": True})

    @app.route("/api/models")
    def api_models():
        try:
            from shouchao.core.ollama_client import OllamaClient
            url = request.args.get("url", CONFIG.ollama_url)
            client = OllamaClient(url)
            return jsonify({
                "available": client.is_available(),
                "chat_models": client.get_chat_models(),
                "embedding_models": client.get_embedding_models(),
            })
        except Exception as e:
            return jsonify({"available": False, "error": str(e)})

    @app.route("/api/stats")
    def api_stats():
        from shouchao.core.storage import ArticleStorage
        storage = ArticleStorage()
        counts = storage.count_articles()
        from shouchao.core.sources import get_sources
        sources_count = len(get_sources())
        
        indexed_count = 0
        try:
            from shouchao.core.indexer import NewsIndexer
            from shouchao.core.ollama_client import OllamaClient
            ollama = OllamaClient(CONFIG.ollama_url)
            indexer = NewsIndexer(ollama)
            indexed_count = indexer.get_document_count()
        except Exception:
            pass
        
        return jsonify({
            "articles": counts,
            "sources_count": sources_count,
            "indexed": indexed_count,
            "version": __version__,
        })

    @app.route("/api/test-connection")
    def api_test_connection():
        from shouchao.core.ollama_client import OllamaClient
        client = OllamaClient(CONFIG.ollama_url)
        available = client.is_available()
        return jsonify({"available": available, "url": CONFIG.ollama_url})

    @app.route("/api/index", methods=["POST"])
    def api_index():
        data = request.get_json(silent=True) or {}
        collection = data.get("collection", "shouchao_news")

        from shouchao.api import index_news
        result = index_news(collection=collection)
        return jsonify(result.to_dict())

    @app.route("/api/web-search", methods=["POST"])
    def api_web_search():
        data = request.get_json(silent=True) or {}
        query = data.get("query", "")
        engines = data.get("engines")
        num_results = data.get("num_results", 10)
        language = data.get("language")

        from shouchao.api import web_search
        result = web_search(
            query=query,
            engines=engines,
            num_results=num_results,
            language=language,
        )
        return jsonify(result.to_dict())

    @app.route("/api/tts", methods=["POST"])
    def api_tts():
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        engine = data.get("engine")
        voice = data.get("voice")
        language = data.get("language")
        rate = data.get("rate", 1.0)

        from shouchao.api import text_to_speech
        result = text_to_speech(
            text=text,
            engine=engine,
            voice=voice,
            language=language,
            rate=rate,
        )
        return jsonify(result.to_dict())

    @app.route("/api/tts/voices", methods=["GET"])
    def api_tts_voices():
        engine = request.args.get("engine", "edge-tts")
        language = request.args.get("language")

        from shouchao.core.tts import TTSEngine
        tts = TTSEngine(preferred_engine=engine)
        voices = tts.get_voices(engine=engine, language=language)
        return jsonify({"voices": [v.to_dict() for v in voices]})

    @app.route("/api/export", methods=["POST"])
    def api_export():
        data = request.get_json(silent=True) or {}
        content = data.get("content", "")
        title = data.get("title", "Untitled")
        output_path = data.get("output_path")
        format = data.get("format", "pdf")
        language = data.get("language")

        if not output_path:
            from shouchao.core.config import DATA_DIR
            export_dir = DATA_DIR / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            import uuid
            output_path = str(export_dir / f"{uuid.uuid4().hex}.{format}")

        from shouchao.api import export_document
        result = export_document(
            content=content,
            title=title,
            output_path=output_path,
            format=format,
            language=language,
        )
        return jsonify(result.to_dict())

    @app.route("/api/keyword-search", methods=["POST"])
    def api_keyword_search():
        data = request.get_json(silent=True) or {}
        keywords = data.get("keywords", [])
        engines = data.get("engines")
        language = data.get("language")
        scenario = data.get("scenario", "general")
        max_results = data.get("max_results", 10)

        from shouchao.api import keyword_search_and_summarize
        result = keyword_search_and_summarize(
            keywords=keywords,
            engines=engines,
            language=language,
            scenario=scenario,
            max_results=max_results,
        )
        return jsonify(result.to_dict())

    @app.route("/api/summarize", methods=["POST"])
    def api_summarize():
        data = request.get_json(silent=True) or {}
        content = data.get("content", "")
        target_language = data.get("target_language", "en")
        style = data.get("style", "detailed")
        source_language = data.get("source_language")
        max_length = data.get("max_length")

        from shouchao.api import summarize_content
        result = summarize_content(
            content=content,
            target_language=target_language,
            style=style,
            source_language=source_language,
            max_length=max_length,
        )
        return jsonify(result.to_dict())

    @app.route("/api/summarize-and-speak", methods=["POST"])
    def api_summarize_and_speak():
        data = request.get_json(silent=True) or {}
        content = data.get("content", "")
        target_language = data.get("target_language", "en")
        style = data.get("style", "story")
        voice = data.get("voice")
        tts_engine = data.get("tts_engine", "edge-tts")

        from shouchao.api import summarize_and_speak
        result = summarize_and_speak(
            content=content,
            target_language=target_language,
            style=style,
            voice=voice,
            tts_engine=tts_engine,
        )
        return jsonify(result.to_dict())

    @app.route("/api/fetch-url", methods=["POST"])
    def api_fetch_url():
        data = request.get_json(silent=True) or {}
        url = data.get("url", "")

        if not url:
            return jsonify({"success": False, "error": "URL is required"})

        try:
            from shouchao.core.config import CONFIG, get_proxies
            from shouchao.core.converter import html_to_markdown

            proxy = get_proxies()
            proxy_str = proxy.get("https") if proxy else None

            import requests
            session = requests.Session()
            if proxy_str:
                session.proxies = {"http": proxy_str, "https": proxy_str}

            resp = session.get(url, timeout=15)
            resp.raise_for_status()

            content, meta = html_to_markdown(resp.text, url)

            return jsonify({
                "success": True,
                "data": {
                    "content": content,
                    "title": meta.get("title", ""),
                    "url": url,
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/proxy/test", methods=["POST"])
    def api_proxy_test():
        data = request.get_json(silent=True) or {}

        from shouchao.core.config import test_proxy_connection
        
        mode = data.get("mode", "none")
        if mode == "manual":
            from shouchao.core.config import CONFIG
            CONFIG.proxy_mode = mode
            CONFIG.proxy_http = data.get("http", "")
            CONFIG.proxy_https = data.get("https", "")
            CONFIG.proxy_socks5 = data.get("socks5", "")
            CONFIG.proxy_username = data.get("username", "")
            CONFIG.proxy_password = data.get("password", "")
        elif mode == "system":
            from shouchao.core.config import CONFIG
            CONFIG.proxy_mode = mode

        result = test_proxy_connection()
        return jsonify(result)

    @app.route("/api/audio")
    def api_audio():
        audio_path = request.args.get("path", "")
        if not audio_path or not Path(audio_path).exists():
            return "Audio not found", 404
        
        from flask import send_file
        return send_file(audio_path, mimetype="audio/mpeg")

    return app


def _sse_data(data: dict) -> str:
    """Format data as SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
