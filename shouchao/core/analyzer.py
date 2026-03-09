"""
LLM-powered news analysis engine for ShouChao.

Provides analysis for investment, immigration, study abroad, and general scenarios.
Uses RAG to ground analysis in actual news content.
"""

import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scenario prompt templates (bilingual: system prompts in English with
# output language controlled by user language setting)
# ---------------------------------------------------------------------------

SCENARIO_PROMPTS = {
    "investment": {
        "system": (
            "You are an experienced financial analyst specializing in global "
            "markets. Analyze the provided news articles and the user's query "
            "to provide investment-relevant insights.\n\n"
            "Structure your response as:\n"
            "## Executive Summary\n"
            "Brief overview of key findings.\n\n"
            "## Key Events\n"
            "Important events from the news that affect markets.\n\n"
            "## Market Impact\n"
            "How these events may affect different sectors, asset classes, "
            "and regions.\n\n"
            "## Risk Assessment\n"
            "Potential risks and uncertainties to watch.\n\n"
            "## Recommendations\n"
            "Actionable suggestions for investors.\n\n"
            "Base your analysis strictly on the provided news context. "
            "Cite specific articles when possible. "
            "Respond in {language}."
        ),
    },
    "immigration": {
        "system": (
            "You are an immigration policy analyst with expertise in global "
            "migration trends. Analyze the provided news articles and the "
            "user's query to provide immigration-relevant insights.\n\n"
            "Structure your response as:\n"
            "## Policy Changes\n"
            "Recent or upcoming immigration policy changes.\n\n"
            "## Country-by-Country Impact\n"
            "How different countries are affected.\n\n"
            "## Timeline & Processing\n"
            "Expected timelines and processing changes.\n\n"
            "## Actionable Steps\n"
            "Concrete recommendations for those considering immigration.\n\n"
            "Base your analysis strictly on the provided news context. "
            "Cite specific articles when possible. "
            "Respond in {language}."
        ),
    },
    "study_abroad": {
        "system": (
            "You are an international education consultant with expertise in "
            "global university systems. Analyze the provided news articles "
            "and the user's query to provide study-abroad-relevant insights.\n\n"
            "Structure your response as:\n"
            "## Education Policy Updates\n"
            "Recent policy changes affecting international students.\n\n"
            "## University & Rankings Impact\n"
            "Changes in university landscape and rankings.\n\n"
            "## Cost & Living Trends\n"
            "Tuition, scholarship, and cost-of-living trends.\n\n"
            "## Application Advice\n"
            "Practical recommendations for prospective students.\n\n"
            "Base your analysis strictly on the provided news context. "
            "Cite specific articles when possible. "
            "Respond in {language}."
        ),
    },
    "general": {
        "system": (
            "You are a senior news analyst providing in-depth analysis of "
            "current events. Analyze the provided news articles and the "
            "user's query.\n\n"
            "Structure your response as:\n"
            "## Summary\n"
            "Key takeaways from the news.\n\n"
            "## Context & Background\n"
            "Relevant historical and geopolitical context.\n\n"
            "## Implications\n"
            "Short-term and long-term implications.\n\n"
            "## Different Perspectives\n"
            "How different stakeholders view the situation.\n\n"
            "Base your analysis strictly on the provided news context. "
            "Cite specific articles when possible. "
            "Respond in {language}."
        ),
    },
}

LANGUAGE_NAMES = {
    "zh": "Chinese (中文)", "en": "English", "ja": "Japanese (日本語)",
    "fr": "French (Français)", "ru": "Russian (Русский)",
    "de": "German (Deutsch)", "it": "Italian (Italiano)",
    "es": "Spanish (Español)", "pt": "Portuguese (Português)",
    "ko": "Korean (한국어)",
}


class AnalysisEngine:
    """LLM-powered news analysis with RAG context."""

    def __init__(self, ollama_client, news_indexer):
        self.ollama = ollama_client
        self.indexer = news_indexer

    def _get_chat_model(self) -> str:
        """Get the configured chat model."""
        from shouchao.core.config import CONFIG
        if CONFIG.chat_model:
            return CONFIG.chat_model
        models = self.ollama.get_chat_models()
        if models:
            CONFIG.chat_model = models[0]
            return models[0]
        raise RuntimeError("No chat model available in Ollama")

    def _build_context(
        self,
        query: str,
        language: Optional[str] = None,
        top_k: int = 10,
    ) -> str:
        """Retrieve relevant news articles as context."""
        results = self.indexer.search_news(
            query, language=language, top_k=top_k,
        )
        if not results:
            return "(No relevant news articles found in the knowledge base.)"

        context_parts = []
        seen_titles = set()
        for r in results:
            meta = r.get("metadata", {})
            title = meta.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            source = meta.get("website", "unknown")
            date = meta.get("date", "")
            doc = r.get("document", "")
            context_parts.append(
                f"### [{title}] ({source}, {date})\n{doc}\n"
            )

        return "\n---\n".join(context_parts)

    def analyze(
        self,
        query: str,
        scenario: str = "general",
        language: Optional[str] = None,
    ) -> Iterator[str]:
        """Run analysis with streaming response.

        Args:
            query: User's analysis query
            scenario: One of "investment", "immigration", "study_abroad", "general"
            language: Output language code (default: CONFIG.language)

        Yields:
            Text chunks of the analysis response.
        """
        from shouchao.core.config import CONFIG

        lang = language or CONFIG.language
        lang_name = LANGUAGE_NAMES.get(lang, "English")

        if scenario not in SCENARIO_PROMPTS:
            scenario = "general"

        template = SCENARIO_PROMPTS[scenario]["system"]
        system_prompt = template.format(language=lang_name)

        # Retrieve relevant articles
        context = self._build_context(query, top_k=CONFIG.top_k)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"## News Context\n\n{context}\n\n"
                    f"---\n\n## User Query\n\n{query}"
                ),
            },
        ]

        model = self._get_chat_model()
        yield from self.ollama.chat_stream(messages, model)

    def analyze_complete(
        self,
        query: str,
        scenario: str = "general",
        language: Optional[str] = None,
    ) -> str:
        """Non-streaming analysis. Returns full response."""
        chunks = list(self.analyze(query, scenario, language))
        return "".join(chunks)
