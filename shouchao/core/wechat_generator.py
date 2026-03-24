"""
WeChat Official Account Article Generator.

Generates articles optimized for WeChat Official Account platform.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .github_trends import RepoTrend, RepoAnalysis, WeChatArticle

logger = logging.getLogger(__name__)


class WeChatArticleGenerator:
    """
    Generate WeChat Official Account style articles.
    
    Style guidelines:
    - Catchy title with emojis
    - Clear structure with sections
    - Code examples
    - Images and screenshots
    - Call-to-action at end
    - Mobile-friendly formatting
    """
    
    def __init__(self):
        self.templates = {
            "title_patterns": [
                "🔥 GitHub 今日最热：{repo}，{stars}星！值得 star 的{tech}神器",
                "💻 这个{tech}项目太火了！{repo} 深度解析",
                "⭐️ GitHub Trending 榜首！{repo} 到底有多强？",
                "🚀 开发者必备！GitHub 热门项目 {repo} 完全指南",
                "🎯 发现宝藏项目：{repo}，{desc}",
            ],
            "intro_patterns": [
                "今天给大家介绍一个在 GitHub 上超级火的项目——**{repo}**。",
                "最近在 GitHub Trending 上发现了一个很棒的项目，必须分享给大家！",
                "作为一名开发者，今天看到一个非常值得一看的开源项目。",
            ],
        }
    
    def generate_single_repo_article(
        self,
        repo: RepoTrend,
        analysis: Optional[RepoAnalysis] = None,
        author: str = "ShouChao",
    ) -> WeChatArticle:
        """
        Generate article for a single repository.
        
        Args:
            repo: Trending repo data
            analysis: Detailed analysis (optional)
            author: Author name
            
        Returns:
            WeChatArticle object
        """
        # Generate title
        title = self._generate_title(repo, analysis)
        
        # Generate content
        content = self._generate_single_content(repo, analysis)
        
        # Generate summary
        summary = self._generate_summary(repo, analysis)
        
        # Calculate stats
        word_count = len(content)
        read_time = max(1, word_count // 300)  # 300 chars/min
        
        return WeChatArticle(
            title=title,
            author=author,
            content=content,
            summary=summary,
            tags=self._generate_tags(repo, analysis),
            word_count=word_count,
            read_time=read_time,
        )
    
    def generate_trending_roundup(
        self,
        repos: list[RepoTrend],
        analyses: dict[str, RepoAnalysis],
        author: str = "ShouChao",
        period: str = "今日",
    ) -> WeChatArticle:
        """
        Generate trending roundup article.
        
        Args:
            repos: List of trending repos
            analyses: Analysis dict by repo name
            author: Author name
            period: Time period (今日/本周/本月)
            
        Returns:
            WeChatArticle object
        """
        title = f"🔥 GitHub {period} Trending  Top {len(repos)} 开源项目推荐"
        
        content = self._generate_roundup_content(repos, analyses, period)
        summary = f"本期精选 {len(repos)} 个 GitHub 热门开源项目，涵盖{self._get_languages(repos)}等领域。"
        
        word_count = len(content)
        read_time = max(1, word_count // 300)
        
        return WeChatArticle(
            title=title,
            author=author,
            content=content,
            summary=summary,
            tags=["GitHub", "开源", "Trending", "技术推荐"],
            word_count=word_count,
            read_time=read_time,
        )
    
    def _generate_title(
        self,
        repo: RepoTrend,
        analysis: Optional[RepoAnalysis],
    ) -> str:
        """Generate catchy title."""
        tech = analysis.language if analysis else repo.language
        if not tech:
            tech = "技术"
        
        desc = analysis.description if analysis else repo.description
        if len(desc) > 20:
            desc = desc[:20] + "..."
        if not desc:
            desc = "优质项目"
        
        stars = f"{repo.stars // 1000}k+" if repo.stars >= 1000 else str(repo.stars)
        
        import random
        pattern = random.choice(self.templates["title_patterns"])
        
        return pattern.format(
            repo=repo.name,
            stars=stars,
            tech=tech,
            desc=desc,
        )
    
    def _generate_single_content(
        self,
        repo: RepoTrend,
        analysis: Optional[RepoAnalysis],
    ) -> str:
        """Generate article content."""
        lines = []
        
        # Header
        lines.append(f"# 🚀 {repo.name}")
        lines.append("")
        
        # Intro
        intro_pattern = self.templates["intro_patterns"][0]
        lines.append(intro_pattern.format(repo=repo.name))
        lines.append("")
        
        # Stats
        lines.append("## 📊 项目数据")
        lines.append("")
        lines.append(f"- ⭐ Stars: {repo.stars:,}")
        lines.append(f"- 🍴 Forks: {repo.forks:,}")
        lines.append(f"- 📈 今日新增: {repo.today_stars:,}")
        lines.append(f"- 💬 语言: {repo.language or 'Unknown'}")
        lines.append("")
        
        # Description
        if analysis and analysis.description:
            lines.append("## 📝 项目简介")
            lines.append("")
            lines.append(analysis.description)
            lines.append("")
        
        # Features
        if analysis and analysis.key_features:
            lines.append("## ✨ 主要特性")
            lines.append("")
            for feature in analysis.key_features[:5]:
                lines.append(f"- {feature}")
            lines.append("")
        
        # Tech Stack
        if analysis and analysis.tech_stack:
            lines.append("## 🛠 技术栈")
            lines.append("")
            lines.append(", ".join(analysis.tech_stack))
            lines.append("")
        
        # Use Cases
        if analysis and analysis.use_cases:
            lines.append("## 💡 使用场景")
            lines.append("")
            for use in analysis.use_cases[:3]:
                lines.append(f"- {use}")
            lines.append("")
        
        # Code Example
        if analysis and analysis.readme:
            code_block = self._extract_code_example(analysis.readme)
            if code_block:
                lines.append("## 💻 代码示例")
                lines.append("")
                lines.append("```python")
                lines.append(code_block)
                lines.append("```")
                lines.append("")
        
        # Links
        lines.append("## 🔗 相关链接")
        lines.append("")
        lines.append(f"- GitHub: {repo.url}")
        if analysis and analysis.homepage:
            lines.append(f"- 官网: {analysis.homepage}")
        lines.append("")
        
        # CTA
        lines.append("---")
        lines.append("")
        lines.append("**如果觉得项目不错，记得给个 Star 哦！** ⭐")
        lines.append("")
        lines.append("关注我，获取更多优质开源项目推荐！👀")
        
        return "\n".join(lines)
    
    def _generate_roundup_content(
        self,
        repos: list[RepoTrend],
        analyses: dict[str, RepoAnalysis],
        period: str,
    ) -> str:
        """Generate roundup article content."""
        lines = []
        
        # Header
        lines.append(f"# 🔥 GitHub {period} Trending | Top {len(repos)} 开源项目推荐")
        lines.append("")
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        
        # Intro
        lines.append("## 📋 本期概览")
        lines.append("")
        lines.append(f"本期精选了 **{len(repos)}** 个 GitHub 热门开源项目，")
        lines.append(f"涵盖 **{self._get_languages(repos)}** 等技术领域。")
        lines.append("")
        
        # Top repos
        for i, repo in enumerate(repos[:10], 1):
            analysis = analyses.get(repo.name)
            
            lines.append(f"## {i}. {repo.name}")
            lines.append("")
            lines.append(f"⭐ {repo.stars:,} | 🍴 {repo.forks:,} | 📈 +{repo.today_stars:,} 今日")
            lines.append("")
            
            if analysis and analysis.description:
                lines.append(f"> {analysis.description}")
                lines.append("")
            elif repo.description:
                lines.append(f"> {repo.description}")
                lines.append("")
            
            if analysis and analysis.tech_stack:
                lines.append(f"**技术栈**: {', '.join(analysis.tech_stack[:5])}")
                lines.append("")
            
            lines.append(f"🔗 [查看项目]({repo.url})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Summary table
        lines.append("## 📊 数据统计")
        lines.append("")
        lines.append("| 排名 | 项目 | 语言 | Stars | 今日 + |")
        lines.append("|------|------|------|-------|--------|")
        for i, repo in enumerate(repos[:10], 1):
            lang = analyses.get(repo.name, RepoAnalysis).language if repo.name in analyses else repo.language
            lines.append(f"| {i} | {repo.name} | {lang or '-'} | {repo.stars:,} | +{repo.today_stars:,} |")
        lines.append("")
        
        # CTA
        lines.append("## 🎯 结语")
        lines.append("")
        lines.append("以上就是本期推荐的热门开源项目！")
        lines.append("")
        lines.append("**你最喜欢哪个项目？欢迎在评论区留言讨论！** 💬")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("👉 **关注我，获取每日 GitHub Trending 推荐！**")
        
        return "\n".join(lines)
    
    def _generate_summary(
        self,
        repo: RepoTrend,
        analysis: Optional[RepoAnalysis],
    ) -> str:
        """Generate short summary."""
        desc = analysis.description if analysis else repo.description
        if not desc:
            desc = "GitHub 热门开源项目推荐"
        
        # Truncate for WeChat
        if len(desc) > 100:
            desc = desc[:97] + "..."
        
        return f"【{repo.name}】{desc}"
    
    def _generate_tags(
        self,
        repo: RepoTrend,
        analysis: Optional[RepoAnalysis],
    ) -> list[str]:
        """Generate tags."""
        tags = ["GitHub", "开源", repo.name.split("/")[-1]]
        
        if analysis:
            if analysis.language:
                tags.append(analysis.language)
            tags.extend(analysis.tech_stack[:3])
        
        return list(set(tags))[:5]
    
    def _get_languages(self, repos: list[RepoTrend]) -> str:
        """Get language summary."""
        langs = {}
        for repo in repos:
            lang = repo.language or "Other"
            langs[lang] = langs.get(lang, 0) + 1
        
        # Sort and format
        sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)
        return ", ".join([f"{l}({c})" for l, c in sorted_langs[:5]])
    
    def _extract_code_example(self, readme: str) -> str:
        """Extract code example from README."""
        import re
        
        # Find code blocks
        pattern = r"```(?:python|py|js|javascript|ts|typescript)?\n([\s\S]*?)```"
        matches = re.findall(pattern, readme, re.IGNORECASE)
        
        if matches:
            # Return first non-empty block
            for match in matches:
                if match.strip():
                    lines = match.strip().split("\n")
                    # Limit to 15 lines
                    return "\n".join(lines[:15])
        
        return ""
    
    def export_to_html(self, article: WeChatArticle) -> str:
        """
        Export article to HTML for WeChat.
        
        WeChat uses a specific HTML format with inline styles.
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 677px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            font-size: 24px;
            color: #07c160;
            border-bottom: 2px solid #07c160;
            padding-bottom: 10px;
        }}
        h2 {{
            font-size: 20px;
            color: #333;
            margin-top: 30px;
        }}
        p {{
            margin: 15px 0;
        }}
        ul, ol {{
            padding-left: 20px;
        }}
        li {{
            margin: 8px 0;
        }}
        blockquote {{
            border-left: 4px solid #07c160;
            padding-left: 15px;
            margin: 15px 0;
            color: #666;
        }}
        code {{
            background: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }}
        pre {{
            background: #f6f8fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            padding: 0;
            background: none;
        }}
        hr {{
            border: none;
            border-top: 1px solid #eaecef;
            margin: 30px 0;
        }}
        a {{
            color: #576b95;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <h1>{article.title}</h1>
    {self._markdown_to_html(article.content)}
</body>
</html>
"""
        article.html = html
        return html
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML."""
        import re
        
        html = markdown
        
        # Headers
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Links
        html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
        
        # Code blocks
        html = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code>\2</code></pre>', html)
        
        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Blockquotes
        html = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # List items
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'^\* (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Horizontal rule
        html = re.sub(r'^---$', r'<hr/>', html, flags=re.MULTILINE)
        
        # Paragraphs (simple approach)
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f'<p>{html}</p>'
        
        # Clean up
        html = html.replace('<p></p>', '')
        html = html.replace('<p><h', '<h')
        html = html.replace('</h1></p>', '</h1>')
        html = html.replace('</h2></p>', '</h2>')
        html = html.replace('</h3></p>', '</h3>')
        html = html.replace('<p><ul>', '<ul>')
        html = html.replace('</ul></p>', '</ul>')
        html = html.replace('<p><pre>', '<pre>')
        html = html.replace('</pre></p>', '</pre>')
        html = html.replace('<p><blockquote>', '<blockquote>')
        html = html.replace('</blockquote></p>', '</blockquote>')
        html = html.replace('<p><hr/></p>', '<hr/>')
        
        return html


# Singleton
_generator: Optional[WeChatArticleGenerator] = None


def get_generator() -> WeChatArticleGenerator:
    """Get article generator singleton."""
    global _generator
    if _generator is None:
        _generator = WeChatArticleGenerator()
    return _generator


def generate_wechat_article(
    repo: RepoTrend,
    analysis: Optional[RepoAnalysis] = None,
    author: str = "ShouChao",
) -> WeChatArticle:
    """Generate WeChat article for a repo."""
    return get_generator().generate_single_repo_article(repo, analysis, author)


def generate_trending_roundup_article(
    repos: list[RepoTrend],
    analyses: dict[str, RepoAnalysis],
    author: str = "ShouChao",
    period: str = "今日",
) -> WeChatArticle:
    """Generate trending roundup article."""
    return get_generator().generate_trending_roundup(repos, analyses, author, period)
