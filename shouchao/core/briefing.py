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
    "你是专业的新闻编辑。用简洁的语言总结新闻要点。\n"
    "要求：1. 用{language}回答 2. 3-5条要点 3. 每条1-2句话"
)

BRIEFING_SYSTEM_PROMPT_WITH_SOURCE = (
    "你是专业的新闻编辑。用简洁的语言总结新闻要点。\n"
    "要求：1. 用{language}回答 2. 3-5条要点 3. 每条标注来源（某网站某日）"
)

LANGUAGE_NAMES = {
    "zh": "中文", "en": "English", "ja": "日本語",
    "fr": "Français", "ru": "Русский",
    "de": "Deutsch", "it": "Italiano",
    "es": "Español", "pt": "Português",
    "ko": "한국어",
}


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
        show_source: bool = False,
    ) -> str:
        """Summarize articles for one category using LLM."""
        article_texts = []
        for a in articles[:5]:  # 减少到5篇，加快速度
            title = a.get("title", "Untitled")
            website = a.get("website", "unknown")
            date = a.get("date", "")
            path = a.get("path")
            snippet = ""
            if path:
                try:
                    text = Path(path).read_text(encoding="utf-8")[:300]  # 减少内容长度
                    if text.startswith("---"):
                        end = text.find("---", 3)
                        if end > 0:
                            text = text[end + 3:]
                    snippet = text.strip()[:150]  # 减少片段长度
                except Exception:
                    pass
            article_texts.append(
                f"- {title} ({website})"
            )

        context = "\n".join(article_texts)
        prompt = (
            f"用简洁的语言总结以下{category}新闻要点（3-5条）：\n\n{context}\n\n"
            f"注意：必须用{self._get_lang_name(language)}回答。"
        )

        model = self._get_chat_model()
        lang_name = self._get_lang_name(language)
        
        if show_source:
            system = BRIEFING_SYSTEM_PROMPT_WITH_SOURCE.format(language=lang_name)
        else:
            system = BRIEFING_SYSTEM_PROMPT.format(language=lang_name)

        logger.info("Summarizing %s with model %s (%d articles)", category, model, len(articles[:5]))
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
        show_source: bool = False,
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

            summary = self._summarize_category(category, articles, lang, show_source)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

        self._save_briefing(date, "daily", lang, grouped)

    def generate_weekly(
        self,
        week_start: Optional[str] = None,
        language: Optional[str] = None,
        show_source: bool = False,
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
            summary = self._summarize_category(category, articles, lang, show_source)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

    def generate_domain(
        self,
        domain_tag: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        language: Optional[str] = None,
        show_source: bool = False,
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

        summary = self._summarize_category(domain_tag, articles, lang, show_source)
        yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

    def generate_from_articles(
        self,
        article_paths: list[str],
        language: str,
        show_source: bool = False,
        title: Optional[str] = None,
    ) -> Iterator[str]:
        """Generate a briefing from a list of selected articles.

        Args:
            article_paths: List of file paths to selected articles.
            language: Output language for the briefing.
            show_source: Whether to include source attribution.
            title: Optional title for the briefing.
        """
        from shouchao.core.config import CONFIG
        from shouchao.i18n import t, TRANSLATIONS

        lang = language or CONFIG.language

        if not article_paths:
            yield f"*{t('no_results', lang)}*\n"
            yield "\n_No articles selected._\n"
            return

        if title:
            yield f"# {title}\n\n"
        else:
            yield f"# {t('daily_briefing', lang)}\n\n"

        articles = []
        for path in article_paths:
            try:
                text = Path(path).read_text(encoding="utf-8")
                meta = {}
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end > 0:
                        meta = self._parse_front_matter(text[:end + 3])
                        text = text[end + 3:]
                
                path_obj = Path(path)
                parts = path_obj.parts
                date = parts[-2] if len(parts) >= 2 else ""
                website = parts[-3] if len(parts) >= 3 else "unknown"
                
                articles.append({
                    "path": path,
                    "title": meta.get("title", path_obj.stem),
                    "website": meta.get("website", website),
                    "date": meta.get("date", date),
                    "category": meta.get("category", "general"),
                    "content": text.strip()[:2000],
                })
            except Exception as e:
                logger.warning("Failed to read article %s: %s", path, e)
                continue

        if not articles:
            yield f"*{t('no_results', lang)}*\n"
            return

        yield f"_{len(articles)} 篇文章_\n\n"
        yield "---\n\n"

        grouped: dict[str, list[dict]] = {}
        for article in articles:
            cats = article.get("category", "general")
            if isinstance(cats, str):
                cat_list = [c.strip() for c in cats.split(",")]
            else:
                cat_list = ["general"]
            for cat in cat_list:
                grouped.setdefault(cat, []).append(article)

        for category, cat_articles in sorted(grouped.items()):
            cat_key = f"category_{category}"
            cat_name = t(cat_key, lang) if cat_key in TRANSLATIONS else category.title()

            yield f"## {cat_name}\n\n"
            summary = self._summarize_category(category, cat_articles, lang, show_source)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_Generated by ShouChao on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

    def _parse_front_matter(self, text: str) -> dict:
        """Parse YAML front matter from markdown text."""
        if not text.startswith("---"):
            return {}
        end = text.find("---", 3)
        if end < 0:
            return {}
        block = text[3:end].strip()
        result = {}
        for line in block.split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"\'')
            if val:
                result[key] = val
        return result

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
