"""
Briefing polisher for ShouChao.

Polishes AI-generated briefings to make them:
- More readable and engaging
- Better structured for TTS audio generation
- Natural flowing narrative style
- Optimized for listening experience
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# TTS-friendly formatting rules
TTS_RULES = {
    # Remove markdown that doesn't work well in TTS
    "remove_patterns": [
        r"\*\*",  # Bold markers
        r"\*",    # Italic markers
        r"#{1,6}\s",  # Headers
        r"!\[.*?\]\(.*?\)",  # Images
        r"\[([^\]]+)\]\([^)]+\)",  # Links -> just text
    ],
    # Replace with TTS-friendly alternatives
    "replacements": {
        "---": "\n\n",
        "###": "\n\n",
        "##": "\n\n",
        "#": "\n\n",
        "- ": "\n• ",
        "• ": "\n• ",
        "1. ": "\n第一，",
        "2. ": "\n第二，",
        "3. ": "\n第三，",
        "4. ": "\n第四，",
        "5. ": "\n第五，",
    },
}


class BriefingPolisher:
    """Polishes briefing content for better reading and TTS."""

    def __init__(self, ollama_client=None):
        self.ollama = ollama_client

    def polish_for_reading(
        self,
        content: str,
        style: str = "narrative",
        language: str = "zh",
    ) -> str:
        """Polish briefing for better reading experience.
        
        Args:
            content: Raw briefing content.
            style: Polish style ("narrative", "bullet", "executive").
            language: Output language.
            
        Returns:
            Polished content.
        """
        if not content or not content.strip():
            return content

        # Step 1: Clean up formatting
        cleaned = self._clean_formatting(content)

        # Step 2: Apply style-specific polishing
        if style == "narrative":
            cleaned = self._make_narrative(cleaned, language)
        elif style == "bullet":
            cleaned = self._make_bullet_points(cleaned, language)
        elif style == "executive":
            cleaned = self._make_executive_summary(cleaned, language)

        # Step 3: Add natural transitions
        cleaned = self._add_transitions(cleaned, language)

        return cleaned

    def polish_for_tts(
        self,
        content: str,
        language: str = "zh",
        pace: str = "normal",
    ) -> str:
        """Polish briefing specifically for TTS audio generation.
        
        Args:
            content: Briefing content to polish.
            language: Language code.
            pace: Speaking pace ("slow", "normal", "fast").
            
        Returns:
            TTS-optimized content.
        """
        if not content or not content.strip():
            return content

        # Step 1: Remove markdown formatting
        cleaned = self._remove_markdown(content)

        # Step 2: Optimize for speech
        cleaned = self._optimize_for_speech(cleaned, language)

        # Step 3: Add natural pauses
        cleaned = self._add_pauses(cleaned, pace)

        # Step 4: Fix pronunciation issues
        cleaned = self._fix_pronunciation(cleaned, language)

        return cleaned

    def polish_with_llm(
        self,
        content: str,
        style: str = "tts",
        language: str = "zh",
    ) -> str:
        """Use LLM to polish content for better quality.
        
        Args:
            content: Raw content.
            style: Target style ("tts", "reading", "broadcast").
            language: Language code.
            
        Returns:
            LLM-polished content.
        """
        if not self.ollama or not content:
            return self.polish_for_reading(content, language=language)

        style_prompts = {
            "tts": f"""请将以下新闻简报改写为适合语音播报的格式。要求：
1. 使用口语化、自然的表达方式
2. 句子不要太长，每句控制在20字以内
3. 添加适当的过渡词，使内容流畅
4. 去除所有Markdown格式标记
5. 保持信息完整，不要遗漏重要内容
6. 使用"首先"、"其次"、"另外"、"最后"等过渡词

原始内容：
{content[:3000]}

请直接输出改写后的内容，不要添加任何解释。""",
            "reading": f"""请将以下新闻简报改写为更易读的版本。要求：
1. 优化段落结构，每段一个主题
2. 使用小标题分隔不同内容
3. 保持专业但易懂的语言风格
4. 保留所有关键信息和数据
5. 添加适当的引言和总结

原始内容：
{content[:3000]}

请直接输出改写后的内容。""",
            "broadcast": f"""请将以下新闻改写为广播稿风格。要求：
1. 开场白要吸引注意力
2. 使用"本台消息"、"据报道"等广播用语
3. 重要信息要重复强调
4. 结尾要有总结和预告
5. 语言要正式但不生硬

原始内容：
{content[:3000]}

请直接输出改写后的广播稿。""",
        }

        prompt = style_prompts.get(style, style_prompts["tts"])

        try:
            result = self.ollama.chat(prompt, temperature=0.3)
            if result and result.strip():
                return result.strip()
        except Exception as e:
            logger.warning(f"LLM polishing failed: {e}")

        # Fallback to rule-based polishing
        if style == "tts":
            return self.polish_for_tts(content, language)
        return self.polish_for_reading(content, language=language)

    def _clean_formatting(self, content: str) -> str:
        """Clean up basic formatting issues."""
        import re

        # Remove excessive blank lines
        content = re.sub(r"\n{4,}", "\n\n\n", content)

        # Fix inconsistent spacing
        content = re.sub(r"  +", " ", content)

        # Remove trailing whitespace
        content = "\n".join(line.rstrip() for line in content.split("\n"))

        return content

    def _make_narrative(self, content: str, language: str) -> str:
        """Convert to narrative style."""
        import re

        lines = content.split("\n")
        result = []
        in_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Headers become section intros
            if line.startswith("#"):
                title = re.sub(r"#+\s*", "", line)
                if language == "zh":
                    result.append(f"\n【{title}】\n")
                else:
                    result.append(f"\n--- {title} ---\n")
                in_section = True
            elif line.startswith("- ") or line.startswith("• "):
                item = re.sub(r"^[-•]\s*", "", line)
                if language == "zh":
                    result.append(f"• {item}")
                else:
                    result.append(f"  - {item}")
            elif line.startswith("> "):
                # Skip source attributions in narrative
                continue
            else:
                result.append(line)

        return "\n".join(result)

    def _make_bullet_points(self, content: str, language: str) -> str:
        """Convert to clear bullet points."""
        import re

        lines = content.split("\n")
        result = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#"):
                title = re.sub(r"#+\s*", "", line)
                result.append(f"\n**{title}**")
            elif line.startswith("- ") or line.startswith("• "):
                result.append(line)
            elif line.startswith("> "):
                continue
            elif len(line) > 50:
                # Long lines become bullets
                result.append(f"• {line}")
            else:
                result.append(line)

        return "\n".join(result)

    def _make_executive_summary(self, content: str, language: str) -> str:
        """Convert to executive summary style."""
        import re

        # Extract key sections
        sections = re.split(r"#{1,3}\s+", content)
        result = ["# 执行摘要\n"]

        for i, section in enumerate(sections[:5]):  # Top 5 sections
            section = section.strip()
            if not section:
                continue

            # Get first line as title
            lines = section.split("\n")
            title = lines[0] if lines else f"要点 {i+1}"
            content_lines = [l for l in lines[1:] if l.strip() and not l.startswith(">")]

            if content_lines:
                result.append(f"\n## {title}")
                # Take first 2-3 key points
                for line in content_lines[:3]:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        result.append(f"• {line}")

        return "\n".join(result)

    def _add_transitions(self, content: str, language: str) -> str:
        """Add natural transitions between sections."""
        import re

        if language == "zh":
            transitions = ["此外，", "另一方面，", "值得注意的是，", "与此同时，"]
        else:
            transitions = ["Additionally, ", "On the other hand, ", "Notably, ", "Meanwhile, "]

        # Add transitions between sections
        lines = content.split("\n")
        result = []
        trans_idx = 0

        for i, line in enumerate(lines):
            if line.startswith("【") or line.startswith("---") or line.startswith("##"):
                if i > 0 and trans_idx < len(transitions):
                    result.append(transitions[trans_idx])
                    trans_idx += 1
            result.append(line)

        return "\n".join(result)

    def _remove_markdown(self, content: str) -> str:
        """Remove all Markdown formatting for TTS."""
        import re

        # Remove bold/italic
        content = re.sub(r"\*\*\*(.*?)\*\*\*", r"\1", content)
        content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
        content = re.sub(r"\*(.*?)\*", r"\1", content)

        # Remove headers
        content = re.sub(r"#{1,6}\s+", "", content)

        # Remove links but keep text
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)

        # Remove images
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

        # Remove blockquotes
        content = re.sub(r"^>\s*", "", content, flags=re.MULTILINE)

        # Remove horizontal rules
        content = re.sub(r"^-{3,}$", "", content, flags=re.MULTILINE)

        # Clean up list markers for TTS
        content = re.sub(r"^- ", "• ", content, flags=re.MULTILINE)

        return content

    def _optimize_for_speech(self, content: str, language: str) -> str:
        """Optimize text for natural speech."""
        import re

        # Break long sentences
        if language == "zh":
            # Split long Chinese sentences
            sentences = re.split(r"[。！？；]", content)
            result = []
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if len(sent) > 30:
                    # Add natural pause points
                    sent = re.sub(r"，", "，\n", sent)
                result.append(sent)
            content = "。\n".join(result)
        else:
            # Split long English sentences
            sentences = re.split(r"[.!?;]", content)
            result = []
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if len(sent) > 25:
                    sent = re.sub(r",", ",\n", sent)
                result.append(sent)
            content = ".\n".join(result)

        return content

    def _add_pauses(self, content: str, pace: str) -> str:
        """Add natural pauses for TTS."""
        import re

        # Pace determines pause length
        pause_map = {
            "slow": "\n\n",
            "normal": "\n",
            "fast": " ",
        }
        pause = pause_map.get(pace, "\n")

        # Add pauses after sections
        lines = content.split("\n")
        result = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Headers get longer pause
            if line.startswith("【") or "---" in line:
                result.append(line)
                result.append("")
            elif line.startswith("•"):
                result.append(line)
                result.append("")
            else:
                result.append(line)

        return "\n".join(result)

    def _fix_pronunciation(self, content: str, language: str) -> str:
        """Fix common pronunciation issues for TTS."""
        import re

        if language == "zh":
            # Fix common issues
            fixes = {
                "AI": "人工智能",
                "API": "应用程序接口",
                "CEO": "首席执行官",
                "CTO": "首席技术官",
                "IPO": "首次公开募股",
                "GDP": "国内生产总值",
                "URL": "网址",
                "HTTP": "超文本传输协议",
                "GitHub": "GitHub",
                "arXiv": "arXiv预印本",
            }
            for abbr, full in fixes.items():
                content = content.replace(abbr, full)

            # Fix numbers for better TTS
            content = re.sub(r"(\d+)%", r"百分之\1", content)
            content = re.sub(r"(\d+)\s*亿", r"\1亿", content)
            content = re.sub(r"(\d+)\s*万", r"\1万", content)

        return content
