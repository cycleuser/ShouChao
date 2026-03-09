"""
Flask web application for ShouChao.

Provides a dashboard with news browsing, briefings, analysis,
search, and settings management with SSE streaming.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
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
            client = OllamaClient(CONFIG.ollama_url)
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
        return jsonify({
            "articles": counts,
            "sources_count": sources_count,
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

    return app


def _sse_data(data: dict) -> str:
    """Format data as SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
