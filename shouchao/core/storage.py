"""
Article storage manager for ShouChao.

Manages the file hierarchy: {data_dir}/news/{lang}/{site}/{date}/{title}.md
"""

import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Characters not allowed in filenames
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_UNDERSCORE = re.compile(r"_{2,}")


def _sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use as a filename."""
    name = name.strip()
    name = _UNSAFE_CHARS.sub("_", name)
    name = _MULTI_UNDERSCORE.sub("_", name)
    name = name.strip("_. ")
    if len(name) > max_length:
        name = name[:max_length].rstrip("_. ")
    return name or "untitled"


def _sanitize_dir_name(name: str) -> str:
    """Sanitize a name for use as a directory component."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff"
                  r"\uac00-\ud7af\u0400-\u04ff\u00c0-\u024f\-_]", "_", name)
    name = _MULTI_UNDERSCORE.sub("_", name)
    return name.strip("_") or "unknown"


class ArticleStorage:
    """Manages news article file storage."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            from shouchao.core.config import NEWS_DIR
            base_dir = NEWS_DIR
        self.base_dir = Path(base_dir)

    def _build_path(
        self, language: str, website: str, date: str, title: str,
    ) -> Path:
        """Build the file path for an article."""
        lang_dir = language.lower()[:2]
        site_dir = _sanitize_dir_name(website)
        date_dir = date  # Expected YYYY-MM-DD
        filename = _sanitize_filename(title) + ".md"
        return self.base_dir / lang_dir / site_dir / date_dir / filename

    def save_article(
        self,
        language: str,
        website: str,
        date: str,
        title: str,
        content: str,
    ) -> Path:
        """Save an article as a markdown file.

        Returns:
            Path to the saved file.
        """
        path = self._build_path(language, website, date, title)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.debug("Saved article: %s", path)
        return path

    def article_exists(
        self, language: str, website: str, date: str, title: str,
    ) -> bool:
        """Check if an article file already exists."""
        return self._build_path(language, website, date, title).exists()

    def get_article(self, path: str | Path) -> str:
        """Read article content from file."""
        return Path(path).read_text(encoding="utf-8")

    def list_articles(
        self,
        language: str = None,
        website: str = None,
        date_from: str = None,
        date_to: str = None,
    ) -> list[dict]:
        """List articles with metadata.

        Returns list of dicts: {path, language, website, date, title, ...}
        """
        results = []
        if not self.base_dir.exists():
            return results

        # Determine language dirs to scan
        if language:
            lang_dirs = [self.base_dir / language.lower()[:2]]
        else:
            lang_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]

        for lang_dir in lang_dirs:
            if not lang_dir.exists():
                continue
            lang = lang_dir.name

            # Determine site dirs
            if website:
                site_dirs = [lang_dir / _sanitize_dir_name(website)]
            else:
                site_dirs = [d for d in lang_dir.iterdir() if d.is_dir()]

            for site_dir in site_dirs:
                if not site_dir.exists():
                    continue
                site = site_dir.name

                for date_dir in sorted(site_dir.iterdir(), reverse=True):
                    if not date_dir.is_dir():
                        continue
                    date_str = date_dir.name

                    # Date filtering
                    if date_from and date_str < date_from:
                        continue
                    if date_to and date_str > date_to:
                        continue

                    for md_file in sorted(date_dir.glob("*.md")):
                        info = {
                            "path": str(md_file),
                            "language": lang,
                            "website": site,
                            "date": date_str,
                            "title": md_file.stem,
                        }
                        # Parse YAML front matter for extra metadata
                        try:
                            text = md_file.read_text(encoding="utf-8")
                            fm = _parse_front_matter(text)
                            if fm:
                                info.update(fm)
                        except Exception:
                            pass
                        results.append(info)

        return results

    def count_articles(self) -> dict:
        """Get article counts by language and website.

        Returns: {"total": N, "by_language": {lang: N}, "by_website": {site: N}}
        """
        stats = {"total": 0, "by_language": {}, "by_website": {}}
        if not self.base_dir.exists():
            return stats

        for lang_dir in self.base_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            lang_count = 0
            for site_dir in lang_dir.iterdir():
                if not site_dir.is_dir():
                    continue
                site_count = sum(
                    1
                    for date_dir in site_dir.iterdir()
                    if date_dir.is_dir()
                    for _ in date_dir.glob("*.md")
                )
                lang_count += site_count
                key = f"{lang_dir.name}/{site_dir.name}"
                stats["by_website"][key] = site_count
            stats["by_language"][lang_dir.name] = lang_count
            stats["total"] += lang_count

        return stats

    def delete_old_articles(self, days: int = 90) -> int:
        """Remove articles older than N days. Returns count deleted."""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        deleted = 0
        if not self.base_dir.exists():
            return 0

        for lang_dir in self.base_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            for site_dir in lang_dir.iterdir():
                if not site_dir.is_dir():
                    continue
                for date_dir in list(site_dir.iterdir()):
                    if date_dir.is_dir() and date_dir.name < cutoff:
                        import shutil
                        shutil.rmtree(date_dir, ignore_errors=True)
                        deleted += 1
        return deleted


def _parse_front_matter(text: str) -> Optional[dict]:
    """Parse YAML front matter from markdown text."""
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end < 0:
        return None
    block = text[3:end].strip()
    result = {}
    for line in block.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"')
        if val:
            result[key] = val
    return result
