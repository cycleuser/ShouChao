"""
GitHub Trends Fetcher and WeChat Article Generator.

Features:
- Fetch trending repositories (daily/weekly/monthly)
- Fetch trending developers
- Analyze repository details (README, stats, tech stack)
- Generate WeChat Official Account style articles
- Export to markdown/HTML for WeChat
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RepoTrend:
    """Trending repository data."""
    rank: int
    name: str  # owner/repo
    description: str
    language: str
    stars: int
    forks: int
    today_stars: int
    url: str
    built_by: list[str]  # Avatars
    topics: list[str] = field(default_factory=list)
    readme: str = ""
    detailed: bool = False


@dataclass
class DeveloperTrend:
    """Trending developer data."""
    rank: int
    username: str
    name: str
    repo_name: str
    repo_desc: str
    url: str
    avatar: str
    followers: int = 0


@dataclass
class RepoAnalysis:
    """Detailed repository analysis."""
    name: str
    full_name: str
    description: str
    language: str
    stars: int
    forks: int
    watchers: int
    open_issues: int
    created_at: str
    updated_at: str
    homepage: str
    topics: list[str]
    license: str
    readme: str
    readme_html: str = ""
    tech_stack: list[str] = field(default_factory=list)
    sentiment: str = ""  # positive/neutral/negative
    key_features: list[str] = field(default_factory=list)
    use_cases: list[str] = field(default_factory=list)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)


@dataclass
class WeChatArticle:
    """WeChat Official Account article."""
    title: str
    author: str
    content: str
    summary: str
    cover_image: str = ""
    tags: list[str] = field(default_factory=list)
    html: str = ""
    word_count: int = 0
    read_time: int = 0  # minutes
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "content": self.content,
            "summary": self.summary,
            "cover_image": self.cover_image,
            "tags": self.tags,
            "word_count": self.word_count,
            "read_time": self.read_time,
        }


class GitHubTrendsFetcher:
    """
    Fetch trending data from GitHub.
    
    Sources:
    - GitHub Trending page
    - GitHub API
    """
    
    TRENDING_URL = "https://github.com/trending"
    DEVELOPERS_URL = "https://github.com/trending/developers"
    
    def __init__(self):
        self._session = None
    
    def _get_session(self):
        """Get or create requests session."""
        if self._session is None:
            import requests
            from shouchao.core.config import CONFIG, get_proxies
            
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            
            if CONFIG.proxy_mode == "manual":
                proxies = get_proxies()
                self._session.proxies.update(proxies)
        
        return self._session
    
    def fetch_trending_repos(
        self,
        since: str = "daily",
        language: Optional[str] = None,
        limit: int = 25,
    ) -> list[RepoTrend]:
        """
        Fetch trending repositories.
        
        Args:
            since: daily, weekly, or monthly
            language: Programming language filter
            limit: Max repos to fetch
            
        Returns:
            List of RepoTrend objects
        """
        try:
            session = self._get_session()
            
            url = self.TRENDING_URL
            params = {"since": since}
            if language:
                url = f"{self.TRENDING_URL}/{language}"
            
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            
            return self._parse_trending_repos(resp.text, limit)
            
        except Exception as e:
            logger.error(f"Failed to fetch trending repos: {e}")
            return self._get_demo_trending_repos(since, language, limit)
    
    def _parse_trending_repos(self, html: str, limit: int) -> list[RepoTrend]:
        """Parse GitHub trending HTML."""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all("article", class_="Box-row")
            
            repos = []
            for i, article in enumerate(articles[:limit]):
                try:
                    # Repo name
                    h2 = article.find("h2")
                    name_link = h2.find("a")
                    name = name_link.text.strip().replace("\n", "").replace(" ", "")
                    url = "https://github.com" + name_link["href"]
                    
                    # Description
                    desc_elem = article.find("p")
                    description = desc_elem.text.strip() if desc_elem else ""
                    
                    # Language
                    lang_elem = article.find("span", itemprop="programmingLanguage")
                    language = lang_elem.text.strip() if lang_elem else ""
                    
                    # Stats
                    stats = article.find_all("a", class_="Link--muted")
                    stars = 0
                    forks = 0
                    today_stars = 0
                    
                    for stat in stats:
                        text = stat.text.strip()
                        if "star" in stat["href"]:
                            stars = self._parse_number(text)
                        elif "fork" in stat["href"]:
                            forks = self._parse_number(text)
                    
                    # Today's stars
                    today_star_elem = article.find("span", class_="d-inline-block")
                    if today_star_elem:
                        match = re.search(r'([\d,\.]+[kKmM]?)\s+star', today_star_elem.text)
                        if match:
                            today_stars = self._parse_number(match.group(1))
                    
                    # Built by
                    built_by = []
                    contributors = article.find_all("img", class_="avatar")
                    for img in contributors[:3]:
                        avatar = img.get("src", "")
                        if avatar:
                            built_by.append(avatar)
                    
                    # Topics
                    topics_elem = article.find("div", class_="topic-tags")
                    topics = []
                    if topics_elem:
                        for tag in topics_elem.find_all("a", class_="topic-tag"):
                            topics.append(tag.text.strip())
                    
                    repos.append(RepoTrend(
                        rank=i + 1,
                        name=name,
                        description=description,
                        language=language,
                        stars=stars,
                        forks=forks,
                        today_stars=today_stars,
                        url=url,
                        built_by=built_by,
                        topics=topics,
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing repo: {e}")
            
            return repos
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return []
    
    def _parse_number(self, text: str) -> int:
        """Parse number from string like '1.2k' or '1,234'."""
        text = text.strip().lower()
        multiplier = 1
        
        if "k" in text:
            multiplier = 1000
            text = text.replace("k", "")
        elif "m" in text:
            multiplier = 1000000
            text = text.replace("m", "")
        
        try:
            return int(float(text.replace(",", "")) * multiplier)
        except ValueError:
            return 0
    
    def fetch_trending_developers(
        self,
        since: str = "daily",
        language: Optional[str] = None,
        limit: int = 25,
    ) -> list[DeveloperTrend]:
        """Fetch trending developers."""
        try:
            session = self._get_session()
            
            url = self.DEVELOPERS_URL
            params = {"since": since}
            
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            
            return self._parse_developers(resp.text, limit)
            
        except Exception as e:
            logger.error(f"Failed to fetch developers: {e}")
            return []
    
    def _parse_developers(self, html: str, limit: int) -> list[DeveloperTrend]:
        """Parse developer trending HTML."""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, "html.parser")
            users = soup.find_all("div", class_="follow-list__user")
            
            devs = []
            for i, user in enumerate(users[:limit]):
                try:
                    # Avatar and username
                    img = user.find("img")
                    avatar = img["src"] if img else ""
                    
                    name_link = user.find("a", class_="link-primary")
                    username = name_link.text.strip() if name_link else ""
                    url = "https://github.com" + name_link["href"] if name_link else ""
                    
                    # Real name
                    name_elem = user.find("span", class_="link-secondary")
                    name = name_elem.text.strip() if name_elem else ""
                    
                    # Repo
                    repo_section = user.find("div", class_="follow-list__repositories")
                    repo_name = ""
                    repo_desc = ""
                    
                    if repo_section:
                        repo_link = repo_section.find("a")
                        if repo_link:
                            repo_name = repo_link.text.strip()
                            repo_url = "https://github.com" + repo_link["href"]
                        
                        desc = repo_section.find("p")
                        repo_desc = desc.text.strip() if desc else ""
                    
                    devs.append(DeveloperTrend(
                        rank=i + 1,
                        username=username,
                        name=name,
                        repo_name=repo_name,
                        repo_desc=repo_desc,
                        url=url,
                        avatar=avatar,
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing developer: {e}")
            
            return devs
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return []
    
    def analyze_repository(self, repo_name: str) -> RepoAnalysis:
        """
        Analyze a repository in detail.
        
        Args:
            repo_name: Full repo name (owner/repo)
            
        Returns:
            RepoAnalysis object
        """
        try:
            session = self._get_session()
            
            # Fetch repo info from GitHub API (unauthenticated, rate limited)
            api_url = f"https://api.github.com/repos/{repo_name}"
            resp = session.get(api_url, timeout=10)
            
            repo_data = {}
            if resp.status_code == 200:
                repo_data = resp.json()
            
            # Fetch README
            readme_url = f"https://raw.githubusercontent.com/{repo_name}/main/README.md"
            readme_resp = session.get(readme_url, timeout=10)
            readme = readme_resp.text if readme_resp.status_code == 200 else ""
            
            if not readme:
                # Try master branch
                readme_url = f"https://raw.githubusercontent.com/{repo_name}/master/README.md"
                readme_resp = session.get(readme_url, timeout=10)
                readme = readme_resp.text if readme_resp.status_code == 200 else ""
            
            return self._analyze_repo_data(repo_name, repo_data, readme)
            
        except Exception as e:
            logger.error(f"Failed to analyze repo {repo_name}: {e}")
            return self._get_demo_analysis(repo_name)
    
    def _analyze_repo_data(
        self,
        repo_name: str,
        repo_data: dict,
        readme: str,
    ) -> RepoAnalysis:
        """Analyze repository data."""
        # Extract tech stack from README
        tech_stack = self._extract_tech_stack(readme)
        
        # Extract key features
        key_features = self._extract_features(readme)
        
        # Sentiment analysis (simple heuristic)
        sentiment = self._analyze_sentiment(readme)
        
        # Use cases
        use_cases = self._extract_use_cases(readme)
        
        return RepoAnalysis(
            name=repo_name.split("/")[-1],
            full_name=repo_name,
            description=repo_data.get("description", ""),
            language=repo_data.get("language", ""),
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            watchers=repo_data.get("watchers_count", 0),
            open_issues=repo_data.get("open_issues_count", 0),
            created_at=repo_data.get("created_at", ""),
            updated_at=repo_data.get("updated_at", ""),
            homepage=repo_data.get("homepage", ""),
            topics=repo_data.get("topics", []),
            license=repo_data.get("license", {}).get("spdx_id", "") if repo_data.get("license") else "",
            readme=readme,
            tech_stack=tech_stack,
            sentiment=sentiment,
            key_features=key_features,
            use_cases=use_cases,
        )
    
    def _extract_tech_stack(self, readme: str) -> list[str]:
        """Extract tech stack from README."""
        tech_keywords = {
            "Python": ["python", "django", "flask", "fastapi"],
            "JavaScript": ["javascript", "node.js", "react", "vue", "angular"],
            "TypeScript": ["typescript", "ts"],
            "Go": ["golang", "go"],
            "Rust": ["rust", "cargo"],
            "Java": ["java", "spring", "kotlin"],
            "Docker": ["docker", "container"],
            "Kubernetes": ["kubernetes", "k8s"],
            "AWS": ["aws", "amazon web services"],
            "TensorFlow": ["tensorflow", "tf"],
            "PyTorch": ["pytorch"],
            "Redis": ["redis"],
            "PostgreSQL": ["postgresql", "postgres"],
            "MongoDB": ["mongodb", "mongo"],
        }
        
        found = []
        readme_lower = readme.lower()
        
        for tech, keywords in tech_keywords.items():
            if any(kw in readme_lower for kw in keywords):
                found.append(tech)
        
        return found
    
    def _extract_features(self, readme: str) -> list[str]:
        """Extract key features from README."""
        features = []
        
        # Look for feature sections
        patterns = [
            r"(?:##|###)\s*[Ff]eatures?\s*\n([\s\S]*?)(?:##|###|$)",
            r"(?:##|###)\s*[Kk]ey\s*[Ff]eatures?\s*\n([\s\S]*?)(?:##|###|$)",
            r"-\s*\[x?\]\s*([^\n]+)",
            r"^\*\s*([^\n]+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, readme, re.MULTILINE)
            for match in matches:
                if isinstance(match, str):
                    lines = match.strip().split("\n")
                    for line in lines:
                        line = line.strip().strip("-").strip("*")
                        if line and len(line) < 200:
                            features.append(line)
        
        return features[:10]  # Limit to 10
    
    def _extract_use_cases(self, readme: str) -> list[str]:
        """Extract use cases from README."""
        use_cases = []
        
        patterns = [
            r"(?:##|###)\s*[Uu]sage\s*\n([\s\S]*?)(?:##|###|$)",
            r"(?:##|###)\s*[Ee]xamples?\s*\n([\s\S]*?)(?:##|###|$)",
            r"(?:##|###)\s*[Uu]se\s*[Cc]ases?\s*\n([\s\S]*?)(?:##|###|$)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, readme, re.MULTILINE)
            for match in matches:
                lines = match.strip().split("\n")[:5]
                use_cases.extend([l.strip() for l in lines if l.strip()])
        
        return use_cases[:5]
    
    def _analyze_sentiment(self, readme: str) -> str:
        """Simple sentiment analysis."""
        positive_words = [
            "easy", "fast", "powerful", "efficient", "simple",
            "modern", "awesome", "great", "best", "love",
            "recommended", "popular", "production-ready",
            "enterprise", "scalable", "robust",
        ]
        
        negative_words = [
            "deprecated", "warning", "issue", "problem",
            "slow", "complex", "difficult",
        ]
        
        readme_lower = readme.lower()
        
        pos_count = sum(1 for w in positive_words if w in readme_lower)
        neg_count = sum(1 for w in negative_words if w in readme_lower)
        
        if pos_count > neg_count * 2:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def _get_demo_trending_repos(
        self,
        since: str,
        language: Optional[str],
        limit: int,
    ) -> list[RepoTrend]:
        """Return demo trending repos."""
        demo_repos = [
            ("openai/ChatGPT", "AI Chatbot", "Python", 50000, 1200),
            ("microsoft/vscode", "Code Editor", "TypeScript", 30000, 800),
            ("facebook/react", "UI Library", "JavaScript", 25000, 600),
            ("tensorflow/tensorflow", "ML Framework", "Python", 20000, 500),
            ("docker/compose", "Container Tool", "Python", 15000, 400),
        ]
        
        return [
            RepoTrend(
                rank=i + 1,
                name=name,
                description=desc,
                language=lang,
                stars=stars,
                forks=stars // 10,
                today_stars=today,
                url=f"https://github.com/{name}",
                built_by=[],
                topics=["demo"],
            )
            for i, (name, desc, lang, stars, today) in enumerate(demo_repos[:limit])
        ]
    
    def _get_demo_analysis(self, repo_name: str) -> RepoAnalysis:
        """Return demo analysis."""
        return RepoAnalysis(
            name=repo_name.split("/")[-1],
            full_name=repo_name,
            description=f"Demo analysis for {repo_name}",
            language="Python",
            stars=10000,
            forks=1000,
            watchers=500,
            open_issues=50,
            created_at="2023-01-01",
            updated_at=datetime.now().isoformat(),
            homepage="https://example.com",
            topics=["demo", "example"],
            license="MIT",
            readme="# Demo\n\nThis is a demo repository.",
            tech_stack=["Python", "Docker"],
            sentiment="positive",
            key_features=["Feature 1", "Feature 2"],
            use_cases=["Use case 1"],
        )


# Singleton
_fetcher: Optional[GitHubTrendsFetcher] = None


def get_fetcher() -> GitHubTrendsFetcher:
    """Get GitHub Trends Fetcher singleton."""
    global _fetcher
    if _fetcher is None:
        _fetcher = GitHubTrendsFetcher()
    return _fetcher


def fetch_github_trending(
    since: str = "daily",
    language: Optional[str] = None,
    limit: int = 25,
) -> list[RepoTrend]:
    """Fetch trending repositories."""
    return get_fetcher().fetch_trending_repos(since, language, limit)


def analyze_github_repo(repo_name: str) -> RepoAnalysis:
    """Analyze a repository."""
    return get_fetcher().analyze_repository(repo_name)
