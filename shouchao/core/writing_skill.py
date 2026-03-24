"""
Professional Writing Skill for ShouChao.

Supports multiple writing styles:
- WeChat Official Account Articles
- Official Documents (公文)
- Academic Papers
- Technical Documentation
- Blog Posts
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class WritingRequest:
    """Writing task request."""
    topic: str
    style: str  # wechat, official, academic, technical, blog
    content_type: str = "article"  # article, report, paper, guide
    target_audience: str = "general"
    key_points: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    tone: str = "professional"  # professional, casual, formal
    length: str = "medium"  # short, medium, long
    language: str = "zh"  # zh, en


@dataclass
class WritingResult:
    """Writing task result."""
    success: bool
    title: str = ""
    content: str = ""
    summary: str = ""
    outline: list[str] = field(default_factory=list)
    word_count: int = 0
    read_time: int = 0  # minutes
    tags: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "outline": self.outline,
            "word_count": self.word_count,
            "read_time": self.read_time,
            "tags": self.tags,
            "references": self.references,
            "error": self.error,
        }


class WritingSkill:
    """
    Professional writing assistant.
    
    Implements writing patterns from:
    - official-document-writer (GB/T 9704-2012)
    - academic-writer (IEEE/ACM/AAAI)
    - software-planner (documentation)
    """
    
    # Writing templates by style
    TEMPLATES = {
        "wechat": {
            "title_patterns": [
                "🔥 {topic}：{highlight}",
                "💡 关于{topic}，你需要知道的一切",
                "📊 {topic}深度解析：{angle}",
                "🚀 {topic}完全指南",
                "⭐️ {topic}：从入门到精通",
            ],
            "structure": [
                "引言（吸引注意）",
                "背景介绍",
                "核心内容（分点阐述）",
                "案例分析",
                "实践建议",
                "总结",
                "互动引导",
            ],
            "style_guide": {
                "paragraph_length": 200,
                "use_emoji": True,
                "use_subheadings": True,
                "use_bullet_points": True,
                "call_to_action": True,
            }
        },
        "official": {
            "title_patterns": [
                "关于{topic}的{type}",
                "{topic}的通知",
                "关于印发{topic}方案的通知",
            ],
            "structure": [
                "发文机关标志",
                "发文字号",
                "标题",
                "主送机关",
                "正文（一、二、三...）",
                "附件说明",
                "发文机关署名",
                "成文日期",
            ],
            "hierarchy": [
                "一、", "（一）", "1.", "（1）"
            ],
            "style_guide": {
                "font": "仿宋",
                "size": "3 号",
                "line_spacing": "28 磅",
                "paper": "A4",
            }
        },
        "academic": {
            "title_patterns": [
                "{topic}: A {approach} Approach",
                "Towards {goal}: A Study on {topic}",
                "{method} for {task}",
            ],
            "structure": [
                "Abstract",
                "Keywords",
                "1. Introduction",
                "2. Related Work",
                "3. Methodology",
                "4. Experiments",
                "5. Conclusion",
                "References",
            ],
            "style_guide": {
                "voice": "passive",
                "tense": "present",
                "citation_style": "IEEE",
                "avoid_contractions": True,
            }
        },
        "technical": {
            "title_patterns": [
                "{topic}技术文档",
                "{topic}使用指南",
                "如何{task}：{topic}教程",
            ],
            "structure": [
                "概述",
                "前置要求",
                "安装/配置",
                "快速开始",
                "详细用法",
                "API 参考",
                "常见问题",
                "故障排除",
            ],
            "style_guide": {
                "code_examples": True,
                "step_by_step": True,
                "screenshots": True,
                "troubleshooting": True,
            }
        },
        "blog": {
            "title_patterns": [
                "我如何{achieve}：{topic}经验分享",
                "{topic}的最佳实践",
                "为什么你应该关注{topic}",
                "{topic}的{number}个技巧",
            ],
            "structure": [
                "引人入胜的开头",
                "问题描述",
                "解决方案",
                "实施步骤",
                "经验总结",
                "参考资料",
            ],
            "style_guide": {
                "personal_voice": True,
                "storytelling": True,
                "practical_tips": True,
                "conversational": True,
            }
        },
    }
    
    def __init__(self):
        self._session = None
    
    def write(
        self,
        request: WritingRequest,
        context: Optional[dict] = None,
    ) -> WritingResult:
        """
        Generate written content.
        
        Args:
            request: Writing request with requirements
            context: Additional context (source materials, references)
            
        Returns:
            WritingResult with generated content
        """
        try:
            template = self.TEMPLATES.get(request.style, self.TEMPLATES["wechat"])
            
            # Generate title
            title = self._generate_title(request, template)
            
            # Generate outline
            outline = self._generate_outline(request, template)
            
            # Generate content
            content = self._generate_content(request, template, context)
            
            # Calculate stats
            word_count = len(content)
            read_time = max(1, word_count // 300)
            
            # Generate tags
            tags = self._generate_tags(request)
            
            return WritingResult(
                success=True,
                title=title,
                content=content,
                outline=outline,
                word_count=word_count,
                read_time=read_time,
                tags=tags,
            )
            
        except Exception as e:
            logger.error(f"Writing error: {e}")
            return WritingResult(
                success=False,
                error=str(e),
            )
    
    def _generate_title(
        self,
        request: WritingRequest,
        template: dict,
    ) -> str:
        """Generate title based on template."""
        import random
        
        patterns = template.get("title_patterns", ["{topic}"])
        pattern = random.choice(patterns)
        
        # Fill placeholders
        title = pattern.format(
            topic=request.topic,
            highlight=request.key_points[0] if request.key_points else "详解",
            angle="多角度分析",
            goal="better understanding",
            method="A Novel Method",
            task=request.key_points[0] if request.key_points else "完成任务",
            achieve=request.key_points[0] if request.key_points else "成功",
            number="5",
            type="报告",
        )
        
        return title
    
    def _generate_outline(
        self,
        request: WritingRequest,
        template: dict,
    ) -> list[str]:
        """Generate content outline."""
        structure = template.get("structure", [])
        
        # Customize outline based on key points
        outline = []
        for section in structure:
            outline.append(section)
        
        return outline
    
    def _generate_content(
        self,
        request: WritingRequest,
        template: dict,
        context: Optional[dict] = None,
    ) -> str:
        """Generate full content."""
        lines = []
        
        style = request.style
        guide = template.get("style_guide", {})
        
        if style == "wechat":
            lines = self._write_wechat(request, guide, context)
        elif style == "official":
            lines = self._write_official(request, guide, context)
        elif style == "academic":
            lines = self._write_academic(request, guide, context)
        elif style == "technical":
            lines = self._write_technical(request, guide, context)
        else:  # blog
            lines = self._write_blog(request, guide, context)
        
        return "\n\n".join(lines)
    
    def _write_wechat(
        self,
        request: WritingRequest,
        guide: dict,
        context: Optional[dict],
    ) -> list[str]:
        """Write WeChat article style."""
        lines = []
        
        # Title
        lines.append(f"# {request.topic}")
        
        # Intro
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"**作者**: ShouChao")
        lines.append("")
        
        # Opening hook
        lines.append("## 📌 引言")
        lines.append(f"今天我们来聊聊**{request.topic}**这个话题。")
        lines.append("")
        
        # Background
        if context and context.get("background"):
            lines.append("## 📖 背景介绍")
            lines.append(context["background"])
            lines.append("")
        
        # Main content
        lines.append("## 💡 核心内容")
        for i, point in enumerate(request.key_points[:5], 1):
            lines.append(f"### {i}. {point}")
            if context and point in context:
                lines.append(context[point])
            else:
                lines.append(f"关于{point}，这是一个重要的方面...")
            lines.append("")
        
        # Summary
        lines.append("## 📝 总结")
        lines.append(f"以上就是关于**{request.topic}**的主要内容。")
        lines.append("")
        
        # CTA
        lines.append("---")
        lines.append("**欢迎在评论区分享你的看法！** 💬")
        lines.append("")
        lines.append("**关注我，获取更多精彩内容！** ✨")
        
        return lines
    
    def _write_official(
        self,
        request: WritingRequest,
        guide: dict,
        context: Optional[dict],
    ) -> list[str]:
        """Write official document style (GB/T 9704-2012)."""
        lines = []
        
        # Header info
        lines.append(f"发文机关：{context.get('agency', 'XXX 单位') if context else 'XXX 单位'}")
        lines.append(f"发文字号：{context.get('doc_number', '〔2024〕X 号') if context else '〔2024〕X 号'}")
        lines.append("")
        
        # Title
        lines.append(f"关于{request.topic}的{request.content_type}")
        lines.append("")
        
        # Main recipient
        lines.append(f"{context.get('recipient', '各单位') if context else '各单位'}：")
        lines.append("")
        
        # Body with proper hierarchy
        lines.append("一、背景和意义")
        lines.append(f"{request.key_points[0] if request.key_points else '说明背景和重要性'}")
        lines.append("")
        
        lines.append("二、主要任务")
        lines.append(f"{request.key_points[1] if len(request.key_points) > 1 else '说明主要任务'}")
        lines.append("")
        
        lines.append("三、实施步骤")
        lines.append("（一）准备阶段")
        lines.append("1. 制定方案")
        lines.append("2. 组织人员")
        lines.append("")
        
        lines.append("（二）实施阶段")
        lines.append("1. 按计划推进")
        lines.append("2. 监督检查")
        lines.append("")
        
        lines.append("四、工作要求")
        lines.append("（一）加强领导")
        lines.append("（二）落实责任")
        lines.append("（三）及时反馈")
        lines.append("")
        
        # Footer
        lines.append(f"{context.get('agency', 'XXX 单位') if context else 'XXX 单位'}")
        lines.append(f"{datetime.now().strftime('%Y 年%m 月%d 日')}")
        
        return lines
    
    def _write_academic(
        self,
        request: WritingRequest,
        guide: dict,
        context: Optional[dict],
    ) -> list[str]:
        """Write academic paper style."""
        lines = []
        
        # Abstract
        lines.append("## Abstract")
        lines.append(f"This paper presents a study on {request.topic}. ")
        lines.append(f"We propose a novel approach to address the challenges in this domain. ")
        lines.append(f"Experimental results demonstrate the effectiveness of our method.")
        lines.append("")
        
        lines.append("**Keywords**: " + ", ".join(request.key_points[:5] or [request.topic]))
        lines.append("")
        
        # Introduction
        lines.append("## 1. Introduction")
        lines.append(f"In recent years, {request.topic} has attracted significant attention.")
        lines.append("However, existing approaches suffer from several limitations.")
        lines.append("To address these challenges, we propose a novel method.")
        lines.append("")
        
        # Related Work
        lines.append("## 2. Related Work")
        if context and context.get("references"):
            for ref in context["references"][:3]:
                lines.append(f"Author et al. [X] studied {ref}.")
        else:
            lines.append("Previous work has explored various aspects of this problem.")
        lines.append("")
        
        # Methodology
        lines.append("## 3. Methodology")
        lines.append("### 3.1 Problem Formulation")
        lines.append("Let us define the problem as follows...")
        lines.append("")
        
        lines.append("### 3.2 Proposed Approach")
        lines.append("Our approach consists of the following components...")
        lines.append("")
        
        # Experiments
        lines.append("## 4. Experiments")
        lines.append("### 4.1 Setup")
        lines.append("We evaluate our method on standard benchmarks...")
        lines.append("")
        
        lines.append("### 4.2 Results")
        lines.append("Table 1 shows the comparison results...")
        lines.append("")
        
        # Conclusion
        lines.append("## 5. Conclusion")
        lines.append(f"In this paper, we presented a study on {request.topic}.")
        lines.append("Future work will explore additional extensions.")
        lines.append("")
        
        # References
        lines.append("## References")
        if context and context.get("references"):
            for i, ref in enumerate(context["references"][:5], 1):
                lines.append(f"[{i}] {ref}")
        else:
            lines.append("[1] Author, A. et al. 'Title.' Venue, Year.")
        
        return lines
    
    def _write_technical(
        self,
        request: WritingRequest,
        guide: dict,
        context: Optional[dict],
    ) -> list[str]:
        """Write technical documentation style."""
        lines = []
        
        # Overview
        lines.append(f"# {request.topic}")
        lines.append("")
        lines.append(f"**版本**: 1.0")
        lines.append(f"**更新日期**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        
        # Overview
        lines.append("## 概述")
        lines.append(f"{request.topic}是一个用于...的工具/系统。")
        lines.append("")
        
        # Requirements
        lines.append("## 前置要求")
        lines.append("- Python 3.8+")
        lines.append("- 相关依赖包")
        lines.append("")
        
        # Installation
        lines.append("## 安装")
        lines.append("```bash")
        lines.append("pip install package-name")
        lines.append("```")
        lines.append("")
        
        # Quick Start
        lines.append("## 快速开始")
        lines.append("```python")
        lines.append("from package import Module")
        lines.append("")
        lines.append("module = Module()")
        lines.append("result = module.run()")
        lines.append("```")
        lines.append("")
        
        # Usage
        lines.append("## 详细用法")
        for i, point in enumerate(request.key_points[:3], 1):
            lines.append(f"### {i}. {point}")
            lines.append(f"关于{point}的详细说明...")
            lines.append("")
        
        # FAQ
        lines.append("## 常见问题")
        lines.append("**Q: 如何...？**")
        lines.append("A: 可以这样操作...")
        lines.append("")
        
        lines.append("**Q: 遇到错误怎么办？**")
        lines.append("A: 请检查以下几点...")
        
        return lines
    
    def _write_blog(
        self,
        request: WritingRequest,
        guide: dict,
        context: Optional[dict],
    ) -> list[str]:
        """Write blog post style."""
        lines = []
        
        # Catchy title
        lines.append(f"# {request.topic}：我的经验分享")
        lines.append("")
        
        # Personal intro
        lines.append(f"大家好，今天想和大家分享一下关于**{request.topic}**的一些心得。")
        lines.append("")
        
        # Story/Problem
        lines.append("## 遇到的问题")
        lines.append(f"前段时间，我遇到了一个问题...")
        lines.append("")
        
        # Solution
        lines.append("## 解决方案")
        for i, point in enumerate(request.key_points[:5], 1):
            lines.append(f"### 方法{i}: {point}")
            lines.append(f"具体来说，可以这样做...")
            lines.append("")
        
        # Tips
        lines.append("## 一些建议")
        lines.append("1. 建议一")
        lines.append("2. 建议二")
        lines.append("3. 建议三")
        lines.append("")
        
        # Conclusion
        lines.append("## 总结")
        lines.append(f"以上就是我关于{request.topic}的一些经验，希望对大家有帮助！")
        lines.append("")
        
        lines.append("---")
        lines.append("欢迎在评论区交流讨论！")
        
        return lines
    
    def _generate_tags(self, request: WritingRequest) -> list[str]:
        """Generate tags for content."""
        tags = [request.topic]
        tags.extend(request.key_points[:3])
        tags.append(request.style)
        tags.append(request.language)
        return list(set(tags))[:5]


# Singleton
_skill: Optional[WritingSkill] = None


def get_writing_skill() -> WritingSkill:
    """Get writing skill singleton."""
    global _skill
    if _skill is None:
        _skill = WritingSkill()
    return _skill


def write_content(
    topic: str,
    style: str = "wechat",
    key_points: Optional[list[str]] = None,
    context: Optional[dict] = None,
) -> WritingResult:
    """
    Convenience function for content writing.
    
    Args:
        topic: Main topic
        style: Writing style (wechat, official, academic, technical, blog)
        key_points: Key points to cover
        context: Additional context
        
    Returns:
        WritingResult
    """
    skill = get_writing_skill()
    request = WritingRequest(
        topic=topic,
        style=style,
        content_type="article",
        target_audience="general",
        key_points=key_points or [],
    )
    return skill.write(request, context)
