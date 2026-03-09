"""
HTML-to-Markdown conversion pipeline for ShouChao.

Adapted from Huan's content extraction and conversion approach.
Extracts metadata, cleans boilerplate, and converts to clean markdown.
"""

import re
import hashlib
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def extract_metadata(soup, url: str) -> dict:
    """Extract metadata from HTML using multiple strategies.

    Priority: JSON-LD > Open Graph > meta tags > HTML tags.
    """
    meta = {"url": url, "fetched_at": datetime.now().isoformat()}

    # --- Standard meta tags ---
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        content = tag.get("content", "")
        if not content:
            continue

        if name in ("author", "article:author"):
            meta.setdefault("author", content)
        elif name == "description":
            meta.setdefault("description", content)
        elif name == "keywords":
            meta.setdefault("keywords", [k.strip() for k in content.split(",")])
        elif name in ("article:published_time", "publishedtime",
                       "publish_date", "date"):
            meta.setdefault("published", content)
        elif name in ("article:modified_time", "last-modified"):
            meta.setdefault("modified", content)
        elif name == "og:title":
            meta["title"] = content
        elif name == "og:description":
            meta.setdefault("description", content)
        elif name == "og:image":
            meta.setdefault("image", content)
        elif name == "og:site_name":
            meta.setdefault("site_name", content)
        elif name == "og:type":
            meta.setdefault("type", content)
        elif name in ("twitter:title",):
            meta.setdefault("title", content)

    # --- <title> tag ---
    title_tag = soup.find("title")
    if title_tag:
        meta.setdefault("title", title_tag.get_text(strip=True))

    # --- <time> tags ---
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        meta.setdefault("published", time_tag["datetime"])

    # --- <html lang> ---
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        meta.setdefault("language", html_tag["lang"][:2].lower())

    # --- Canonical URL ---
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        meta["canonical_url"] = canonical["href"]

    # --- JSON-LD (highest priority override) ---
    import json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0] if data else {}
            schema_type = data.get("@type", "")
            if schema_type in ("Article", "BlogPosting", "NewsArticle",
                               "TechArticle", "WebPage", "ScholarlyArticle",
                               "ReportageNewsArticle"):
                if data.get("headline"):
                    meta["title"] = data["headline"]
                if data.get("description"):
                    meta["description"] = data["description"]
                if data.get("datePublished"):
                    meta["published"] = data["datePublished"]
                if data.get("dateModified"):
                    meta["modified"] = data["dateModified"]
                # Author
                author = data.get("author")
                if isinstance(author, str):
                    meta["author"] = author
                elif isinstance(author, dict):
                    meta["author"] = author.get("name", "")
                elif isinstance(author, list) and author:
                    names = [a.get("name", str(a)) if isinstance(a, dict)
                             else str(a) for a in author]
                    meta["author"] = ", ".join(names)
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    return meta


def format_front_matter(meta: dict) -> str:
    """Format metadata dict as YAML front matter."""
    lines = ["---"]
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            val = str(value)
            if any(c in val for c in (':', '"', "'", "\n", "#", "{", "}")):
                val = val.replace('"', '\\"')
                lines.append(f'{key}: "{val}"')
            else:
                lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


def strip_boilerplate(soup) -> None:
    """Remove non-content elements in-place."""
    for tag_name in ("script", "style", "noscript", "iframe", "svg"):
        for tag in soup.find_all(tag_name):
            tag.decompose()
    # Remove common nav/footer/sidebar elements
    for selector in (
        "nav", "footer", "header",
        '[role="navigation"]', '[role="banner"]',
        '[class*="sidebar"]', '[class*="advertisement"]',
        '[class*="cookie"]', '[class*="popup"]',
        '[class*="social-share"]', '[class*="related-"]',
        '[id*="sidebar"]', '[id*="footer"]', '[id*="nav"]',
        '[id*="cookie"]', '[id*="popup"]',
    ):
        for el in soup.select(selector):
            el.decompose()


def heuristic_extract(soup):
    """Find main content area using semantic HTML and heuristics."""
    # Try semantic elements first
    for selector in ("article", "main", '[role="main"]'):
        el = soup.select_one(selector)
        if el:
            return el

    # Try common content class/id patterns
    for pattern in ("content", "article", "post-body", "entry-content",
                    "story-body", "article-body", "post-content"):
        el = soup.select_one(f'[class*="{pattern}"]')
        if el:
            return el
        el = soup.select_one(f'[id*="{pattern}"]')
        if el:
            return el

    # Fall back to body
    return soup.find("body") or soup


def preprocess_tables(soup) -> None:
    """Normalize tables for better markdown output."""
    for table in soup.find_all("table"):
        # Flatten nested tables
        for nested in table.find_all("table"):
            nested.unwrap()
        # Handle colspan
        for td in table.find_all(["td", "th"]):
            colspan = int(td.get("colspan", 1))
            if colspan > 1:
                td.attrs.pop("colspan", None)
                parent = td.parent
                if parent:
                    for _ in range(colspan - 1):
                        from bs4 import Tag
                        new_td = Tag(name=td.name)
                        new_td.string = ""
                        td.insert_after(new_td)


def preprocess_code_blocks(soup) -> None:
    """Detect code block languages and inject markers."""
    lang_patterns = [
        (r"language-(\w+)", 1), (r"lang-(\w+)", 1),
        (r"hljs-?(\w+)", 1), (r"highlight-(\w+)", 1),
    ]
    for pre in soup.find_all("pre"):
        code = pre.find("code")
        target = code if code else pre
        classes = " ".join(target.get("class", []))
        detected = None
        for pattern, group in lang_patterns:
            m = re.search(pattern, classes)
            if m:
                detected = m.group(group)
                break
        if detected:
            marker = f"__CODELANG_{detected}__\n"
            if target.string:
                target.string = marker + target.string
            elif target.contents:
                from bs4 import NavigableString
                target.insert(0, NavigableString(marker))


def html_to_markdown(
    html: str,
    url: str,
    metadata_enabled: bool = True,
    extractor: str = "readability",
) -> tuple[str, dict]:
    """Convert HTML to markdown with metadata.

    Args:
        html: Raw HTML string
        url: Source URL
        metadata_enabled: Include YAML front matter
        extractor: "readability", "heuristic", or "full"

    Returns:
        (markdown_text, metadata_dict)
    """
    from bs4 import BeautifulSoup
    import html2text

    soup = BeautifulSoup(html, "html.parser")

    # Extract metadata from full page
    meta = extract_metadata(soup, url) if metadata_enabled else {"url": url}

    # Content extraction
    readable_title = None
    if extractor == "readability":
        try:
            from readability import Document
            doc = Document(html)
            content_html = doc.summary()
            readable_title = doc.short_title()
            content_soup = BeautifulSoup(content_html, "html.parser")
        except ImportError:
            logger.debug("readability-lxml not available, using heuristic")
            strip_boilerplate(soup)
            content_soup = heuristic_extract(soup)
        except Exception:
            strip_boilerplate(soup)
            content_soup = heuristic_extract(soup)
    elif extractor == "heuristic":
        strip_boilerplate(soup)
        content_soup = heuristic_extract(soup)
    else:  # full
        strip_boilerplate(soup)
        content_soup = soup.find("body") or soup

    # Preprocessing
    preprocess_tables(content_soup)
    preprocess_code_blocks(content_soup)

    # Title
    title = readable_title or meta.get("title", "")

    # Convert to markdown
    h = html2text.HTML2Text()
    h.body_width = 0
    h.unicode_snob = True
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_tables = False
    h.protect_links = True
    h.wrap_links = False
    h.single_line_break = False

    md_body = h.handle(str(content_soup))

    # Post-processing
    # Clean angle brackets in links
    md_body = re.sub(r"\]\(<([^>]+)>\)", r"](\1)", md_body)
    # Code language markers
    md_body = re.sub(
        r"```\n__CODELANG_(\w+)__\n",
        r"```\1\n",
        md_body,
    )
    # Clean excessive blank lines
    md_body = re.sub(r"\n{4,}", "\n\n\n", md_body)

    # Word count and token estimation
    words = len(md_body.split())
    tokens = int(words * 1.3)
    meta["word_count"] = words
    meta["estimated_tokens"] = tokens

    # Content hash for dedup
    meta["content_hash"] = hashlib.md5(md_body.encode()).hexdigest()[:12]

    # Assemble final markdown
    parts = []
    if metadata_enabled:
        parts.append(format_front_matter(meta))
        parts.append("")

    if title and f"# {title}" not in md_body[:200]:
        parts.append(f"# {title}")
        parts.append("")

    parts.append(f"> Source: <{url}>")
    parts.append("")
    parts.append(md_body.strip())
    parts.append("")

    return "\n".join(parts), meta
