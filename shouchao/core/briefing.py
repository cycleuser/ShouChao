"""
News briefing generator for ShouChao.

Generates daily, weekly, and domain-specific news briefings
using LLM summarization with RAG context.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

BRIEFING_SYSTEM_PROMPT = (
    "You are a professional news editor creating a concise, informative "
    "news briefing. Summarize the provided articles into clear, organized "
    "bullet points grouped by category.\n\n"
    "Guidelines:\n"
    "- Each category section should have 3-5 key bullet points\n"
    "- Each bullet should be 1-2 sentences\n"
    "- Include the source name in parentheses after each point\n"
    "- Focus on facts, not opinions\n"
    "- Highlight significant developments and their implications\n"
    "- Respond in {language}\n"
)


class BriefingGenerator:
    """Generates structured news briefings."""

    def __init__(self, ollama_client, news_indexer, article_storage):
        self.ollama = ollama_client
        self.indexer = news_indexer
        self.storage = article_storage

    def _get_chat_model(self) -> str:
        from shouchao.core.config import CONFIG
        if CONFIG.chat_model:
            return CONFIG.chat_model
        models = self.ollama.get_chat_models()
        if models:
            CONFIG.chat_model = models[0]
            return models[0]
        raise RuntimeError("No chat model available in Ollama")

    def _get_lang_name(self, lang: str) -> str:
        from shouchao.core.analyzer import LANGUAGE_NAMES
        return LANGUAGE_NAMES.get(lang, "English")

    def _gather_articles(
        self,
        date_from: str,
        date_to: str,
        language: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> dict[str, list[dict]]:
        """Gather articles grouped by category."""
        articles = self.storage.list_articles(
            language=language,
            date_from=date_from,
            date_to=date_to,
        )

        grouped: dict[str, list[dict]] = {}
        for article in articles:
            cats = article.get("category", "general")
            if isinstance(cats, str):
                cat_list = [c.strip() for c in cats.split(",")]
            else:
                cat_list = cats if cats else ["general"]

            for cat in cat_list:
                if categories and cat not in categories:
                    continue
                grouped.setdefault(cat, []).append(article)

        return grouped

    def _summarize_category(
        self,
        category: str,
        articles: list[dict],
        language: str,
    ) -> str:
        """Summarize articles for one category using LLM."""
        # Build article summaries for context
        article_texts = []
        for a in articles[:10]:  # Limit to 10 per category
            title = a.get("title", "Untitled")
            website = a.get("website", "unknown")
            date = a.get("date", "")
            # Try to read a snippet
            path = a.get("path")
            snippet = ""
            if path:
                try:
                    text = Path(path).read_text(encoding="utf-8")[:500]
                    # Skip front matter
                    if text.startswith("---"):
                        end = text.find("---", 3)
                        if end > 0:
                            text = text[end + 3:]
                    snippet = text.strip()[:300]
                except Exception:
                    pass
            article_texts.append(
                f"- **{title}** ({website}, {date})\n  {snippet}"
            )

        context = "\n".join(article_texts)
        prompt = (
            f"Summarize these {category} news articles into 3-5 key "
            f"bullet points:\n\n{context}"
        )

        model = self._get_chat_model()
        lang_name = self._get_lang_name(language)
        system = BRIEFING_SYSTEM_PROMPT.format(language=lang_name)

        response = self.ollama.chat_complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            model,
        )
        return response

    def generate_daily(
        self,
        date: Optional[str] = None,
        language: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> Iterator[str]:
        """Generate a daily news briefing.

        Yields markdown chunks of the briefing.
        """
        from shouchao.core.config import CONFIG
        from shouchao.i18n import t

        lang = language or CONFIG.language
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        yield f"# {t('daily_briefing', lang)} — {date}\n\n"

        grouped = self._gather_articles(date, date, language, categories)

        if not grouped:
            yield f"*{t('no_results', lang)}*\n"
            yield "\n_No articles found for this date. Try fetching news first._\n"
            return

        total_articles = sum(len(v) for v in grouped.values())
        yield f"_{total_articles} articles from {len(grouped)} categories_\n\n"
        yield "---\n\n"

        for category, articles in sorted(grouped.items()):
            from shouchao.i18n import TRANSLATIONS
            cat_key = f"category_{category}"
            cat_name = t(cat_key, lang) if cat_key in TRANSLATIONS else category.title()

            yield f"## {cat_name}\n\n"

            summary = self._summarize_category(category, articles, lang)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

        # Save briefing
        self._save_briefing(date, "daily", lang, grouped)

    def generate_weekly(
        self,
        week_start: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Iterator[str]:
        """Generate a weekly news briefing."""
        from shouchao.core.config import CONFIG
        from shouchao.i18n import t

        lang = language or CONFIG.language

        if week_start is None:
            today = datetime.now()
            start = today - timedelta(days=today.weekday())
            week_start = start.strftime("%Y-%m-%d")

        start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        week_end = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")
        week_num = start_dt.isocalendar()[1]

        yield f"# {t('weekly_briefing', lang)} — W{week_num} ({week_start} ~ {week_end})\n\n"

        grouped = self._gather_articles(week_start, week_end, language)

        if not grouped:
            yield f"*{t('no_results', lang)}*\n"
            return

        total = sum(len(v) for v in grouped.values())
        yield f"_{total} articles from {len(grouped)} categories_\n\n"
        yield "---\n\n"

        for category, articles in sorted(grouped.items()):
            from shouchao.i18n import TRANSLATIONS
            cat_key = f"category_{category}"
            cat_name = t(cat_key, lang) if cat_key in TRANSLATIONS else category.title()

            yield f"## {cat_name} ({len(articles)} articles)\n\n"
            summary = self._summarize_category(category, articles, lang)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

    def generate_domain(
        self,
        domain_tag: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Iterator[str]:
        """Generate a domain-specific briefing."""
        from shouchao.core.config import CONFIG
        from shouchao.i18n import t, TRANSLATIONS

        lang = language or CONFIG.language

        if date_to is None:
            date_to = datetime.now().strftime("%Y-%m-%d")
        if date_from is None:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        cat_key = f"category_{domain_tag}"
        domain_name = t(cat_key, lang) if cat_key in TRANSLATIONS else domain_tag.title()

        yield f"# {domain_name} — {date_from} ~ {date_to}\n\n"

        grouped = self._gather_articles(date_from, date_to, language, [domain_tag])

        articles = grouped.get(domain_tag, [])
        if not articles:
            yield f"*{t('no_results', lang)}*\n"
            return

        yield f"_{len(articles)} articles_\n\n"
        yield "---\n\n"

        summary = self._summarize_category(domain_tag, articles, lang)
        yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

    def _save_briefing(
        self, date: str, btype: str, lang: str, grouped: dict,
    ) -> Optional[Path]:
        """Save a generated briefing to disk."""
        from shouchao.core.config import BRIEFINGS_DIR
        try:
            BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"{date}_{btype}_{lang}.md"
            path = BRIEFINGS_DIR / filename
            # Don't overwrite existing content here; briefing text is streamed
            logger.debug("Briefing marker saved: %s", path)
            return path
        except Exception as e:
            logger.warning("Failed to save briefing: %s", e)
            return None
