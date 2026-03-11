"""
Content summarization module for ShouChao.

Provides AI-powered summarization with multi-language support.
Can summarize content from any language to any target language.
"""

import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "zh": "Chinese (中文)",
    "en": "English",
    "ja": "Japanese (日本語)",
    "fr": "French (Français)",
    "ru": "Russian (Русский)",
    "de": "German (Deutsch)",
    "it": "Italian (Italiano)",
    "es": "Spanish (Español)",
    "pt": "Portuguese (Português)",
    "ko": "Korean (한국어)",
}

SUMMARY_STYLES = {
    "brief": {
        "name": "Brief Summary",
        "description": "Short, concise summary in 2-3 sentences",
        "max_length": 200,
    },
    "detailed": {
        "name": "Detailed Summary",
        "description": "Comprehensive summary with key points",
        "max_length": 500,
    },
    "bullet": {
        "name": "Bullet Points",
        "description": "Key points as bullet list",
        "max_length": 400,
    },
    "executive": {
        "name": "Executive Summary",
        "description": "Professional executive summary format",
        "max_length": 600,
    },
    "story": {
        "name": "Narrative Summary",
        "description": "Story-like summary, good for TTS",
        "max_length": 800,
    },
}

SUMMARY_PROMPTS = {
    "brief": """Summarize the following content in 2-3 concise sentences.
Focus on the main message and key facts.
Write the summary in {target_language}.

Content:
{content}

Summary:""",

    "detailed": """Provide a detailed summary of the following content.
Include:
- Main topic and key points
- Important details and facts
- Conclusions or implications

Write the summary in {target_language}.

Content:
{content}

Detailed Summary:""",

    "bullet": """Extract and summarize the key points from the following content.
Present as a bullet list with 5-8 main points.
Write in {target_language}.

Content:
{content}

Key Points:
•""",

    "executive": """Create an executive summary of the following content.
Format:
## Overview
[Brief overview in 1-2 sentences]

## Key Findings
[Main findings and facts]

## Implications
[What this means]

## Recommendations
[Suggested actions, if applicable]

Write in {target_language}.

Content:
{content}

Executive Summary:""",

    "story": """Rewrite the following content as an engaging narrative summary.
Make it flow naturally as if telling a story - suitable for text-to-speech.
Keep the important facts but make it conversational and easy to listen to.
Write in {target_language}.

Content:
{content}

Narrative Summary:""",
}


class ContentSummarizer:
    """AI-powered content summarizer with multi-language support."""

    def __init__(self, ollama_client=None):
        self.ollama = ollama_client

    def _get_ollama(self):
        """Get or create Ollama client."""
        if self.ollama is None:
            from shouchao.core.ollama_client import OllamaClient
            from shouchao.core.config import CONFIG
            self.ollama = OllamaClient(CONFIG.ollama_url)
        return self.ollama

    def _get_chat_model(self) -> str:
        """Get the configured chat model."""
        from shouchao.core.config import CONFIG
        ollama = self._get_ollama()
        
        if CONFIG.chat_model:
            return CONFIG.chat_model
        models = ollama.get_chat_models()
        if models:
            CONFIG.chat_model = models[0]
            return models[0]
        raise RuntimeError("No chat model available in Ollama")

    def summarize(
        self,
        content: str,
        target_language: str = "en",
        style: str = "detailed",
        max_length: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Summarize content with streaming response.

        Args:
            content: The content to summarize
            target_language: Language code for output (e.g., "en", "zh")
            style: Summary style ("brief", "detailed", "bullet", "executive", "story")
            max_length: Maximum length in words (optional)

        Yields:
            Text chunks of the summary.
        """
        if style not in SUMMARY_PROMPTS:
            style = "detailed"

        lang_name = LANGUAGE_NAMES.get(target_language, "English")
        prompt_template = SUMMARY_PROMPTS[style]

        prompt = prompt_template.format(
            content=content[:8000],  # Limit content length
            target_language=lang_name,
        )

        if max_length:
            prompt += f"\n\nKeep the summary under {max_length} words."

        messages = [{"role": "user", "content": prompt}]

        ollama = self._get_ollama()
        model = self._get_chat_model()

        yield from ollama.chat_stream(messages, model)

    def summarize_complete(
        self,
        content: str,
        target_language: str = "en",
        style: str = "detailed",
        max_length: Optional[int] = None,
    ) -> str:
        """Non-streaming summarization. Returns full response."""
        chunks = list(self.summarize(content, target_language, style, max_length))
        return "".join(chunks)

    def translate_and_summarize(
        self,
        content: str,
        source_language: Optional[str] = None,
        target_language: str = "en",
        style: str = "detailed",
    ) -> Iterator[str]:
        """
        Translate and summarize content from one language to another.

        Args:
            content: The content to process
            source_language: Source language (auto-detected if None)
            target_language: Target language for output
            style: Summary style

        Yields:
            Text chunks of the translated summary.
        """
        source_lang = LANGUAGE_NAMES.get(source_language, "the original language")
        
        lang_name = LANGUAGE_NAMES.get(target_language, "English")
        
        prompt = f"""The following content is in {source_lang}.
Please:
1. Understand the content
2. Summarize it
3. Write the summary in {lang_name}

Use the "{SUMMARY_STYLES.get(style, SUMMARY_STYLES['detailed'])['name']}" style.

Content:
{content[:8000]}

Summary in {lang_name}:"""

        messages = [{"role": "user", "content": prompt}]

        ollama = self._get_ollama()
        model = self._get_chat_model()

        yield from ollama.chat_stream(messages, model)

    def translate_and_summarize_complete(
        self,
        content: str,
        source_language: Optional[str] = None,
        target_language: str = "en",
        style: str = "detailed",
    ) -> str:
        """Non-streaming translate and summarize."""
        chunks = list(self.translate_and_summarize(
            content, source_language, target_language, style
        ))
        return "".join(chunks)


def get_available_styles() -> dict:
    """Get all available summary styles."""
    return SUMMARY_STYLES


def get_supported_languages() -> dict:
    """Get all supported languages."""
    return LANGUAGE_NAMES