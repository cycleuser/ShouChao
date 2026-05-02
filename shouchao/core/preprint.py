"""
Preprint server fetcher for ShouChao.

Fetches latest preprints from arXiv, bioRxiv, and medRxiv.
Supports daily fetching, keyword filtering, and incremental updates.
"""

import logging
import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class PreprintEntry:
    """A single preprint entry."""
    title: str
    url: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    published: str = ""
    updated: str = ""
    doi: str = ""
    pdf_url: str = ""
    source: str = ""  # "arxiv", "biorxiv", "medrxiv"
    language: str = "en"

    @property
    def date_str(self) -> str:
        """Extract YYYY-MM-DD from published date."""
        if not self.published:
            return datetime.now().strftime("%Y-%m-%d")
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(self.published[:19], fmt[:19])
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        return datetime.now().strftime("%Y-%m-%d")

    @property
    def content_hash(self) -> str:
        """Generate a hash for deduplication."""
        return hashlib.md5(self.url.encode()).hexdigest()[:12]

    def to_markdown(self) -> str:
        """Convert to markdown format with front matter."""
        meta = {
            "title": self.title,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "date": self.date_str,
            "published": self.published,
            "updated": self.updated,
            "authors": ", ".join(self.authors[:5]),
            "categories": ", ".join(self.categories),
            "source": self.source,
            "language": self.language,
            "doi": self.doi,
        }
        lines = ["---"]
        for k, v in meta.items():
            if v:
                lines.append(f'{k}: "{v}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        if self.authors:
            lines.append(f"**Authors:** {', '.join(self.authors[:5])}")
            lines.append("")
        if self.categories:
            lines.append(f"**Categories:** {', '.join(self.categories)}")
            lines.append("")
        lines.append("## Abstract")
        lines.append("")
        lines.append(self.abstract)
        lines.append("")
        if self.pdf_url:
            lines.append(f"[PDF]({self.pdf_url}) | [Source]({self.url})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# arXiv API
# ---------------------------------------------------------------------------

def fetch_arxiv(
    *,
    category: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    proxy: Optional[dict] = None,
) -> list[PreprintEntry]:
    """Fetch preprints from arXiv.

    Args:
        category: arXiv category (e.g., "cs.AI", "math.ST", "q-bio").
        keywords: List of keywords to search for.
        max_results: Maximum number of results.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        proxy: Optional proxy dict.

    Returns:
        List of PreprintEntry objects.
    """
    import requests
    from xml.etree import ElementTree

    base_url = "http://export.arxiv.org/api/query"
    params = {
        "sortBy": "lastUpdatedDate",
        "sortOrder": "descending",
        "max_results": min(max_results, 2000),  # arXiv limit
        "start": 0,
    }

    # Build search query
    query_parts = []
    if category:
        query_parts.append(f"cat:{category}")
    if keywords:
        kw_query = " AND ".join(f'all:"{kw}"' for kw in keywords)
        query_parts.append(f"({kw_query})")

    if date_from or date_to:
        date_range = _build_arxiv_date_range(date_from, date_to)
        if date_range:
            query_parts.append(date_range)

    if query_parts:
        params["search_query"] = " AND ".join(query_parts)

    try:
        resp = requests.get(base_url, params=params, proxies=proxy, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logger.error("arXiv fetch failed: %s", e)
        return []

    # Parse Atom XML
    entries = []
    try:
        root = ElementTree.fromstring(resp.content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        for entry_elem in root.findall("atom:entry", ns):
            title = _get_text(entry_elem, "atom:title", ns)
            summary = _get_text(entry_elem, "atom:summary", ns)
            published = _get_text(entry_elem, "atom:published", ns)
            updated = _get_text(entry_elem, "atom:updated", ns)

            # Extract authors
            authors = []
            for author_elem in entry_elem.findall("atom:author", ns):
                name = _get_text(author_elem, "atom:name", ns)
                if name:
                    authors.append(name)

            # Extract categories
            categories = []
            for cat_elem in entry_elem.findall("atom:category", ns):
                term = cat_elem.get("term", "")
                if term:
                    categories.append(term)

            # Extract links
            url = ""
            pdf_url = ""
            for link_elem in entry_elem.findall("atom:link", ns):
                link_type = link_elem.get("type", "")
                link_href = link_elem.get("href", "")
                link_rel = link_elem.get("rel", "")
                if link_rel == "alternate" or (not link_rel and "html" in link_type):
                    url = link_href
                elif "pdf" in link_type or link_rel == "related":
                    pdf_url = link_href

            # Extract arxiv-specific fields
            doi = _get_text(entry_elem, "arxiv:doi", ns)
            if not url and entry_elem.find("atom:id", ns) is not None:
                url = entry_elem.find("atom:id", ns).text or ""

            if not pdf_url and url:
                pdf_url = url.replace("abs", "pdf")

            entries.append(PreprintEntry(
                title=title.strip(),
                url=url,
                abstract=summary.strip(),
                authors=authors,
                categories=categories,
                published=published,
                updated=updated,
                doi=doi,
                pdf_url=pdf_url,
                source="arxiv",
            ))
    except ElementTree.ParseError as e:
        logger.error("arXiv XML parse error: %s", e)

    logger.info("Fetched %d preprints from arXiv", len(entries))
    return entries


def _build_arxiv_date_range(date_from: Optional[str], date_to: Optional[str]) -> str:
    """Build arXiv date range query."""
    parts = []
    if date_from:
        parts.append(f"submittedDate:[{date_from.replace('-', '')}0000 TO 999912312359]")
    if date_to:
        parts.append(f"submittedDate:[000001010000 TO {date_to.replace('-', '')}2359]")
    return " AND ".join(parts) if parts else ""


def _get_text(elem, tag: str, ns: dict) -> str:
    """Safely extract text from XML element."""
    el = elem.find(tag, ns)
    return el.text.strip() if el is not None and el.text else ""


# ---------------------------------------------------------------------------
# bioRxiv / medRxiv API
# ---------------------------------------------------------------------------

def fetch_biorxiv(
    *,
    category: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    server: str = "biorxiv",
    proxy: Optional[dict] = None,
) -> list[PreprintEntry]:
    """Fetch preprints from bioRxiv or medRxiv.

    Args:
        category: Subject area category.
        keywords: List of keywords to search.
        max_results: Maximum results.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        server: "biorxiv" or "medrxiv".
        proxy: Optional proxy dict.

    Returns:
        List of PreprintEntry objects.
    """
    import requests

    # bioRxiv/medRxiv API: https://api.biorxiv.org/
    # Format: https://api.biorxiv.org/details/{server}/{interval}/{limit}
    # interval: "2024-01-01/2024-01-02" or "2024-01-01/14" (14 days from date)

    if date_from and date_to:
        interval = f"{date_from}/{date_to}"
    elif date_from:
        interval = f"{date_from}/14"  # 14 days from date_from
    else:
        # Default: last 7 days
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        interval = f"{week_ago}/{today}"

    base_url = f"https://api.biorxiv.org/details/{server}/{interval}/{{}}"

    entries = []
    cursor = 0
    total_fetched = 0

    while total_fetched < max_results:
        url = base_url.format(cursor)
        try:
            resp = requests.get(url, proxies=proxy, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("%s fetch failed at cursor %d: %s", server, cursor, e)
            break

        collection = data.get("collection", [])
        if not collection:
            break

        for item in collection:
            if total_fetched >= max_results:
                break

            title = item.get("title", "").strip()
            abstract = item.get("abstract", "").strip()
            doi = item.get("doi", "")
            category_str = item.get("category", "")
            authors_str = item.get("authors", "")
            date_str = item.get("date", "")

            # Parse authors
            authors = [a.strip() for a in authors_str.split(";") if a.strip()] if authors_str else []

            # Build URLs
            url = f"https://www.{server}.org/content/{doi}" if doi else ""
            pdf_url = f"https://www.{server}.org/content/{doi}.full.pdf" if doi else ""

            # Filter by keywords
            if keywords:
                text = f"{title} {abstract}".lower()
                if not any(kw.lower() in text for kw in keywords):
                    continue

            # Filter by category
            if category and category_str.lower() != category.lower():
                continue

            entries.append(PreprintEntry(
                title=title,
                url=url,
                abstract=abstract,
                authors=authors,
                categories=[category_str] if category_str else [],
                published=date_str,
                updated=date_str,
                doi=doi,
                pdf_url=pdf_url,
                source=server,
            ))
            total_fetched += 1

        cursor += len(collection)
        if len(collection) < 100:  # API returns max 100 per page
            break
        time.sleep(0.5)  # Be polite to the API

    logger.info("Fetched %d preprints from %s", len(entries), server)
    return entries


# ---------------------------------------------------------------------------
# Combined fetcher
# ---------------------------------------------------------------------------

ARXIV_CATEGORIES = {
    "cs": ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.MA", "cs.SE", "cs.CR", "cs.DC", "cs.HC", "cs.IR"],
    "math": ["math.ST", "math.OC", "math.PR", "math.NA", "math.CO", "math.AG", "math.GT"],
    "physics": ["physics.data-an", "physics.comp-ph", "physics.bio-ph", "physics.med-ph"],
    "q-bio": ["q-bio.GN", "q-bio.BM", "q-bio.CB", "q-bio.MN", "q-bio.QM"],
    "stat": ["stat.ML", "stat.AP", "stat.ME", "stat.TH"],
    "eess": ["eess.SP", "eess.IV", "eess.SY", "eess.AS"],
}

BIORXIV_CATEGORIES = [
    "bioinformatics", "bioengineering", "biophysics", "biotechnology",
    "cell_biology", "developmental_biology", "ecology", "epidemiology",
    "evolutionary_biology", "genetics", "genomics", "microbiology",
    "molecular_biology", "neuroscience", "pathology", "pharmacology",
    "physiology", "plant_biology", "synthetic_biology", "systems_biology",
    "zoology",
]

MEDRXIV_CATEGORIES = [
    "addiction_medicine", "allergy_immunology", "anesthesia",
    "cardiovascular_medicine", "dermatology", "emergency_medicine",
    "endocrinology", "epidemiology", "forensic_medicine",
    "gastroenterology", "genetic_genomic_medicine", "geriatric_medicine",
    "health_informatics", "hematology", "hiv_aids", "infectious_diseases",
    "intensive_care_critical_care_medicine", "medical_education",
    "neurology", "nursing", "obstetrics_gynecology", "oncology",
    "ophthalmology", "orthopedics", "otolaryngology", "palliative_medicine",
    "pathology", "pediatrics", "pharmacology_therapeutics",
    "psychiatry_clinical_psychology", "public_global_health",
    "radiology_imaging", "rehabilitation_medicine",
    "respiratory_medicine", "rheumatology", "sport_medicine",
    "surgery", "toxicology", "transplantation", "urology",
]


def fetch_preprints(
    *,
    servers: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 100,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    proxy: Optional[dict] = None,
) -> list[PreprintEntry]:
    """Fetch preprints from multiple servers.

    Args:
        servers: List of servers ("arxiv", "biorxiv", "medrxiv"). Default: all.
        categories: List of categories to fetch.
        keywords: Keywords to filter by.
        max_results: Max results per server.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).
        proxy: Optional proxy dict.

    Returns:
        Combined list of PreprintEntry objects.
    """
    if servers is None:
        servers = ["arxiv", "biorxiv", "medrxiv"]

    all_entries = []

    for server in servers:
        if server == "arxiv":
            # Fetch from multiple arXiv categories
            cats = categories or ["cs.AI", "cs.LG", "cs.CL", "q-bio.GN", "q-bio.BM"]
            for cat in cats:
                entries = fetch_arxiv(
                    category=cat,
                    keywords=keywords,
                    max_results=max_results // len(cats),
                    date_from=date_from,
                    date_to=date_to,
                    proxy=proxy,
                )
                all_entries.extend(entries)
                time.sleep(3)  # arXiv rate limit

        elif server in ("biorxiv", "medrxiv"):
            entries = fetch_biorxiv(
                category=categories[0] if categories else None,
                keywords=keywords,
                max_results=max_results,
                date_from=date_from,
                date_to=date_to,
                server=server,
                proxy=proxy,
            )
            all_entries.extend(entries)

    # Deduplicate by URL
    seen = set()
    unique = []
    for entry in all_entries:
        if entry.url not in seen:
            seen.add(entry.url)
            unique.append(entry)

    logger.info("Total unique preprints fetched: %d", len(unique))
    return unique


# ---------------------------------------------------------------------------
# Storage integration
# ---------------------------------------------------------------------------

def save_preprints(
    entries: list[PreprintEntry],
    base_dir: Optional[Path] = None,
) -> list[dict]:
    """Save preprint entries to the article storage.

    Args:
        entries: List of PreprintEntry objects.
        base_dir: Base directory for storage.

    Returns:
        List of saved article info dicts.
    """
    from shouchao.core.storage import ArticleStorage

    storage = ArticleStorage(base_dir)
    saved = []

    for entry in entries:
        if storage.article_exists(
            entry.language, entry.source, entry.date_str, entry.title,
        ):
            continue

        content = entry.to_markdown()
        path = storage.save_article(
            entry.language, entry.source, entry.date_str, entry.title, content,
        )
        saved.append({
            "path": str(path),
            "title": entry.title,
            "source": entry.source,
            "language": entry.language,
            "date": entry.date_str,
            "url": entry.url,
            "categories": entry.categories,
        })

    logger.info("Saved %d preprints to storage", len(saved))
    return saved


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def search_preprints_keyword(
    *,
    query: str,
    entries: list[PreprintEntry],
    top_k: int = 10,
) -> list[tuple[float, PreprintEntry]]:
    """Search preprints by keyword matching.

    Returns list of (score, entry) tuples sorted by score descending.
    """
    query_lower = query.lower()
    query_terms = set(_tokenize(query_lower))

    results = []
    for entry in entries:
        text = f"{entry.title} {entry.abstract} {' '.join(entry.authors)} {' '.join(entry.categories)}".lower()
        text_terms = _tokenize(text)

        # Score based on term overlap
        overlap = len(query_terms & text_terms)
        if overlap == 0:
            continue

        # Boost for title matches
        title_lower = entry.title.lower()
        title_boost = sum(1 for term in query_terms if term in title_lower) * 2

        score = overlap + title_boost
        results.append((score, entry))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


def search_preprints_semantic(
    *,
    query: str,
    indexer,
    collection: str = "preprints",
    top_k: int = 10,
) -> list[dict]:
    """Search preprints using semantic search via the indexer.

    Args:
        query: Search query.
        indexer: NewsIndexer instance.
        collection: ChromaDB collection name.
        top_k: Number of results.

    Returns:
        List of search result dicts.
    """
    return indexer.search_news(query, collection=collection, top_k=top_k)


def rank_preprints_with_model(
    *,
    query: str,
    entries: list[PreprintEntry],
    ollama_client,
    top_k: int = 10,
) -> list[tuple[float, PreprintEntry]]:
    """Use local LLM to rank preprints by relevance.

    Args:
        query: Search query.
        entries: Candidate preprints.
        ollama_client: OllamaClient instance.
        top_k: Number of results.

    Returns:
        List of (score, entry) tuples.
    """
    if not entries:
        return []

    # Build prompt for batch ranking
    candidates_text = "\n\n".join([
        f"[{i}] {e.title}\n{e.abstract[:200]}"
        for i, e in enumerate(entries[:50])  # Limit to 50 for context
    ])

    prompt = f"""Given the search query: "{query}"

Rate the relevance of each paper on a scale of 0-10.
Respond with ONLY a JSON array of scores, one per paper in order.

{candidates_text}

JSON scores:"""

    try:
        response = ollama_client.chat(prompt, temperature=0.0)
        # Parse scores from response
        scores = _parse_scores(response)
        if len(scores) != min(len(entries), 50):
            raise ValueError("Score count mismatch")

        results = []
        for i, entry in enumerate(entries[:50]):
            score = scores[i] if i < len(scores) else 0
            results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]
    except Exception as e:
        logger.warning("Model ranking failed: %s", e)
        # Fallback to keyword search
        return search_preprints_keyword(query=query, entries=entries, top_k=top_k)


def _tokenize(text: str) -> set[str]:
    """Simple tokenization."""
    return set(re.findall(r'\b\w+\b', text.lower()))


def _parse_scores(response: str) -> list[int]:
    """Parse scores from LLM response."""
    import json
    # Try to extract JSON array
    match = re.search(r'\[[\d,\s]+\]', response)
    if match:
        return json.loads(match.group())
    # Fallback: extract all numbers
    return [int(x) for x in re.findall(r'\b\d+\b', response)]


# ---------------------------------------------------------------------------
# Daily fetch scheduler helper
# ---------------------------------------------------------------------------

def fetch_todays_preprints(
    *,
    servers: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    max_results: int = 200,
    proxy: Optional[dict] = None,
) -> dict:
    """Fetch today's preprints and save to storage.

    This is the main function for daily automated fetching.

    Args:
        servers: Servers to fetch from.
        categories: Categories to fetch.
        keywords: Keywords to filter.
        max_results: Max results per server.
        proxy: Optional proxy.

    Returns:
        Dict with fetch statistics.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("Fetching today's preprints (%s)", today)

    entries = fetch_preprints(
        servers=servers,
        categories=categories,
        keywords=keywords,
        max_results=max_results,
        date_from=today,
        date_to=today,
        proxy=proxy,
    )

    saved = save_preprints(entries)

    return {
        "date": today,
        "fetched": len(entries),
        "saved": len(saved),
        "by_source": _count_by_source(entries),
        "saved_paths": [s["path"] for s in saved],
    }


def _count_by_source(entries: list[PreprintEntry]) -> dict:
    """Count entries by source."""
    counts = {}
    for e in entries:
        counts[e.source] = counts.get(e.source, 0) + 1
    return counts
