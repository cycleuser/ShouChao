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

BRIEFING_SYSTEM_PROMPT = """你是信息整理助手。你的任务是整理今日信息汇总。

【重要规则】
- 不要假设有特定主题，只是汇总信息
- 直接列出要点，不要写成长文
- 保持简洁、客观、准确
- 使用{language}回答
- 每条信息后面用 [来源: 网站] 标注来源

【格式要求】
- 每条信息用简短的句子概括
- 重要数据用**粗体**标注
- 按类别分组
- 来源格式：[来源: 网站名称]"""

BRIEFING_SYSTEM_PROMPT_WITH_SOURCE = """你是信息整理助手。你的任务是整理今日信息汇总。

【重要规则】
- 不要假设有特定主题，只是汇总信息
- 直接列出要点，不要写成长文
- 保持简洁、客观、准确
- 使用{language}回答
- 每条信息后面标注来源链接

【格式要求】
- 每条信息用简短的句子概括
- 重要数据用**粗体**标注
- 按类别分组
- 来源格式：[来源: 网站名称，日期](链接地址)"""

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
        for a in articles[:10]:
            title = a.get("title", "Untitled")
            website = a.get("website", "unknown")
            date = a.get("date", "")
            path = a.get("path")
            
            full_content = ""
            if path:
                try:
                    text = Path(path).read_text(encoding="utf-8")
                    if text.startswith("---"):
                        end = text.find("---", 3)
                        if end > 0:
                            text = text[end + 3:]
                    full_content = text.strip()[:2000]
                except Exception as e:
                    logger.warning("Failed to read article %s: %s", path, e)
            
            article_texts.append(f"- {title} ({website}, {date})\n  {full_content[:500] if full_content else ''}")

        context = "\n\n".join(article_texts)
        
        model = self._get_chat_model()
        lang_name = self._get_lang_name(language)
        
        if show_source:
            system = BRIEFING_SYSTEM_PROMPT_WITH_SOURCE.format(language=lang_name)
        else:
            system = BRIEFING_SYSTEM_PROMPT.format(language=lang_name)
        
        user_prompt = f"""请整理以下{category}类别的信息，直接列出要点：

{context}

要求：
1. 每条信息用一句话概括核心内容
2. 不要添加分析或评论
3. 保持客观中立
4. 用{lang_name}回答"""

        logger.info("Summarizing %s with model %s (%d articles)", category, model, len(articles[:10]))
        print(f"📝 正在整理 {category} 信息...")
        
        response = self.ollama.chat_complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            model,
        )
        
        if response:
            print(f"✓ 完成")
        
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

        yield f"# 今日信息汇总 ({date})\n\n"

        grouped = self._gather_articles(date, date, language, categories)

        if not grouped:
            yield f"*{t('no_results', lang)}*\n"
            yield "\n暂无信息，请先抓取新闻。\n"
            return

        total_articles = sum(len(v) for v in grouped.values())
        yield f"共 {total_articles} 条信息\n\n"
        yield "---\n\n"

        for category, articles in sorted(grouped.items()):
            from shouchao.i18n import TRANSLATIONS
            cat_key = f"category_{category}"
            cat_name = t(cat_key, lang) if cat_key in TRANSLATIONS else category.title()

            yield f"## {cat_name}\n\n"

            summary = self._summarize_category(category, articles, lang, show_source)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

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
        from shouchao.i18n import t

        lang = language or CONFIG.language
        today = datetime.now().strftime("%Y-%m-%d")

        if not article_paths:
            yield f"*{t('no_results', lang)}*\n"
            return

        yield f"# 今日信息汇总 ({today})\n\n"

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
                    "content": text.strip()[:1500],
                })
            except Exception as e:
                logger.warning("Failed to read article %s: %s", path, e)
                continue

        if not articles:
            yield f"*{t('no_results', lang)}*\n"
            return

        yield f"共 {len(articles)} 条信息\n\n"
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
            from shouchao.i18n import TRANSLATIONS
            cat_key = f"category_{category}"
            cat_name = t(cat_key, lang) if cat_key in TRANSLATIONS else category.title()

            yield f"## {cat_name}\n\n"
            summary = self._summarize_category(category, cat_articles, lang, show_source)
            yield summary + "\n\n"

        yield "---\n\n"
        yield f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"

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
