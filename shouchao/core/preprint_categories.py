"""
Preprint category discovery and management.

Dynamically fetches category hierarchies from arXiv, bioRxiv, and medRxiv
instead of using hardcoded lists. Supports keyword-based category search
and browsing of platform-provided category trees.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CategoryNode:
    """A node in the category hierarchy."""
    id: str
    name: str
    full_name: str = ""
    children: list["CategoryNode"] = field(default_factory=list)
    parent_id: Optional[str] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "children": [c.to_dict() for c in self.children],
        }

    def flatten(self) -> list[dict]:
        """Flatten hierarchy to list of categories."""
        result = [{
            "id": self.id,
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
        }]
        for child in self.children:
            result.extend(child.flatten())
        return result


# ---------------------------------------------------------------------------
# arXiv Categories
# ---------------------------------------------------------------------------

def fetch_arxiv_categories() -> list[CategoryNode]:
    """Fetch full category hierarchy from arXiv.
    
    Uses the arXiv API to get all available categories with their
    hierarchical structure (parent -> subcategory).
    """
    import requests
    
    # arXiv provides a category listing page
    url = "https://arxiv.org/category_taxonomy"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return _parse_arxiv_categories(resp.text)
    except Exception as e:
        logger.warning(f"Failed to fetch arXiv categories: {e}")
        return _get_arxiv_fallback_categories()


def _parse_arxiv_categories(html: str) -> list[CategoryNode]:
    """Parse arXiv category page HTML.

    The arXiv taxonomy page uses accordion sections with h4 for category ID
    and p for description. Format:
    <h4>cs.AI <span>(Artificial Intelligence)</span></h4>
    <p>Description text...</p>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    categories = []
    seen_ids = set()

    # Find all h4 tags that contain category IDs (format: "cs.AI <span>(Name)</span>")
    for h4 in soup.find_all("h4"):
        h4_text = h4.get_text(strip=True)
        if not h4_text or "(" not in h4_text:
            continue

        # Extract category ID from the h4 (e.g., "cs.AI" from "cs.AI (Artificial Intelligence)")
        cat_id = h4_text.split("(")[0].strip()

        if not cat_id or "." not in cat_id or cat_id in seen_ids:
            continue

        # Extract name from span if present (format: "cs.AI <span>(Artificial Intelligence)</span>")
        span = h4.find("span")
        if span:
            name = span.get_text(strip=True).strip("()")
        else:
            name = cat_id.split(".")[-1] if "." in cat_id else cat_id

        # Get description - it's in the next sibling column's p tag
        # HTML structure: <div class="column is-one-fifth"><h4>cs.AI...</h4></div><div class="column"><p>Description...</p></div>
        description = ""
        parent_div = h4.find_parent("div")
        if parent_div:
            next_col = parent_div.find_next_sibling("div")
            if next_col:
                p = next_col.find("p")
                if p:
                    description = p.get_text(strip=True)

        # Parse hierarchy
        parent_id = cat_id.split(".")[0] if "." in cat_id else cat_id
        full_name = f"{parent_id} - {name}" if "." in cat_id else name

        categories.append(CategoryNode(
            id=cat_id,
            name=name,
            full_name=full_name,
            parent_id=parent_id,
            description=description,
        ))
        seen_ids.add(cat_id)

    # Also capture top-level group names (from accordion-head elements)
    for accordion_head in soup.find_all("h2", class_="accordion-head"):
        btn = accordion_head.find("button")
        if not btn:
            continue
        group_name = btn.get_text(strip=True)
        # Extract group ID from the button's aria-controls (e.g., "accordion-head-grp_cs")
        aria_controls = btn.get("aria-controls", "")
        if "grp_" in aria_controls:
            group_id = aria_controls.split("grp_")[-1]
            # Check if we already have this group as parent
            if not any(c.id == group_id for c in categories):
                categories.append(CategoryNode(
                    id=group_id,
                    name=group_name,
                    full_name=group_name,
                    description="",
                ))

    # Build hierarchy
    return _build_category_tree(categories)


def _build_category_tree(flat_categories: list[CategoryNode]) -> list[CategoryNode]:
    """Build hierarchical tree from flat list."""
    roots = []
    by_id = {c.id: c for c in flat_categories}
    
    for cat in flat_categories:
        if cat.parent_id and cat.parent_id in by_id:
            parent = by_id[cat.parent_id]
            parent.children.append(cat)
        elif not cat.parent_id:
            roots.append(cat)
    
    return roots


def _extract_category_name(description: str, sub_id: str) -> str:
    """Extract human-readable name from description."""
    # Try to get the first sentence or meaningful part
    if description:
        # Remove common prefixes
        desc = description.strip()
        if len(desc) > 100:
            desc = desc[:100].rsplit(".", 1)[0] + "."
        return desc
    return sub_id


def _get_parent_name(cat_id: str) -> str:
    """Get human-readable name for top-level category."""
    names = {
        "cs": "Computer Science",
        "math": "Mathematics",
        "physics": "Physics",
        "q-bio": "Quantitative Biology",
        "q-fin": "Quantitative Finance",
        "stat": "Statistics",
        "eess": "Electrical Engineering and Systems Science",
        "econ": "Economics",
        "astro-ph": "Astrophysics",
        "cond-mat": "Condensed Matter",
        "gr-qc": "General Relativity and Quantum Cosmology",
        "hep-ex": "High Energy Physics - Experimental",
        "hep-lat": "High Energy Physics - Lattice",
        "hep-ph": "High Energy Physics - Phenomenology",
        "hep-th": "High Energy Physics - Theory",
        "math-ph": "Mathematical Physics",
        "nlin": "Nonlinear Sciences",
        "nucl-ex": "Nuclear Experiment",
        "nucl-th": "Nuclear Theory",
    }
    return names.get(cat_id, cat_id)


def _get_arxiv_fallback_categories() -> list[CategoryNode]:
    """Fallback categories when API fails."""
    return [
        CategoryNode(id="cs", name="Computer Science", full_name="cs", children=[
            CategoryNode(id="cs.AI", name="Artificial Intelligence", full_name="cs - AI"),
            CategoryNode(id="cs.CL", name="Computation and Language", full_name="cs - CL"),
            CategoryNode(id="cs.CV", name="Computer Vision", full_name="cs - CV"),
            CategoryNode(id="cs.LG", name="Machine Learning", full_name="cs - LG"),
            CategoryNode(id="cs.SE", name="Software Engineering", full_name="cs - SE"),
            CategoryNode(id="cs.CR", name="Cryptography and Security", full_name="cs - CR"),
            CategoryNode(id="cs.DB", name="Databases", full_name="cs - DB"),
            CategoryNode(id="cs.IR", name="Information Retrieval", full_name="cs - IR"),
        ]),
        CategoryNode(id="math", name="Mathematics", full_name="math", children=[
            CategoryNode(id="math.ST", name="Statistics Theory", full_name="math - ST"),
            CategoryNode(id="math.OC", name="Optimization and Control", full_name="math - OC"),
        ]),
        CategoryNode(id="q-bio", name="Quantitative Biology", full_name="q-bio", children=[
            CategoryNode(id="q-bio.GN", name="Genomics", full_name="q-bio - GN"),
            CategoryNode(id="q-bio.BM", name="Biomolecules", full_name="q-bio - BM"),
        ]),
    ]


# ---------------------------------------------------------------------------
# bioRxiv Categories
# ---------------------------------------------------------------------------

def fetch_biorxiv_categories(
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> list[CategoryNode]:
    """Fetch categories from bioRxiv API with dynamic discovery.

    Tries to dynamically discover categories by sampling the API.
    Falls back to a comprehensive static list if API fails.

    Args:
        use_cache: Whether to use cached categories.
        force_refresh: Force refresh even if cached.

    Returns:
        List of CategoryNode objects for bioRxiv categories.
    """
    import requests

    # Check for cached categories
    cache_key = "biorxiv_categories"
    if use_cache and not force_refresh:
        cached = _get_cached_categories(cache_key)
        if cached:
            return cached

    # Try to dynamically discover categories from API
    discovered = _discover_biorxiv_categories_from_api()

    if discovered:
        # Cache the discovered categories
        _cache_categories(cache_key, discovered)
        return discovered

    # Fallback to comprehensive static list
    logger.info("Using fallback bioRxiv categories")
    return _get_biorxiv_fallback_categories()


def _discover_biorxiv_categories_from_api(
    proxy: Optional[dict] = None,
    sample_size: int = 500,
) -> Optional[list[CategoryNode]]:
    """Dynamically discover bioRxiv categories by sampling the API.

    Makes API calls to collect unique category values.

    Args:
        proxy: Optional proxy dict.
        sample_size: Number of articles to sample.

    Returns:
        List of CategoryNode objects or None if discovery fails.
    """
    import requests

    # Sample from different date ranges to get diverse categories
    # bioRxiv has papers from 2013 onwards, sample recent and older periods
    date_ranges = [
        ("2024-01-01", "2024-12-31"),  # 2024
        ("2023-01-01", "2023-12-31"),  # 2023
        ("2020-01-01", "2020-12-31"),  # 2020
    ]

    all_categories = set()

    for date_from, date_to in date_ranges:
        url = f"https://api.biorxiv.org/details/biorxiv/{date_from}/{date_to}/1"
        try:
            resp = requests.get(url, proxies=proxy, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            collection = data.get("collection", [])

            for item in collection[:100]:  # Sample 100 from each range
                cat = item.get("category", "").strip()
                if cat:
                    all_categories.add(cat)

            # Stop if we have enough categories
            if len(all_categories) > 30:
                break
        except Exception as e:
            logger.debug(f"bioRxiv API sample failed for {date_from}: {e}")
            continue

    if not all_categories:
        return None

    # Convert to CategoryNode list, sorted alphabetically
    result = [
        CategoryNode(
            id=cat.lower().replace(" ", "_"),
            name=cat,
            full_name=cat,
        )
        for cat in sorted(all_categories)
    ]
    return result


def _get_biorxiv_fallback_categories() -> list[CategoryNode]:
    """Comprehensive fallback list for bioRxiv categories."""
    return [
        CategoryNode(id="bioinformatics", name="Bioinformatics", full_name="Bioinformatics"),
        CategoryNode(id="bioengineering", name="Bioengineering", full_name="Bioengineering"),
        CategoryNode(id="biophysics", name="Biophysics", full_name="Biophysics"),
        CategoryNode(id="biotechnology", name="Biotechnology", full_name="Biotechnology"),
        CategoryNode(id="cancer_biology", name="Cancer Biology", full_name="Cancer Biology"),
        CategoryNode(id="cell_biology", name="Cell Biology", full_name="Cell Biology"),
        CategoryNode(id="developmental_biology", name="Developmental Biology", full_name="Developmental Biology"),
        CategoryNode(id="ecology", name="Ecology", full_name="Ecology"),
        CategoryNode(id="epidemiology", name="Epidemiology", full_name="Epidemiology"),
        CategoryNode(id="evolutionary_biology", name="Evolutionary Biology", full_name="Evolutionary Biology"),
        CategoryNode(id="genetics", name="Genetics", full_name="Genetics"),
        CategoryNode(id="genomics", name="Genomics", full_name="Genomics"),
        CategoryNode(id="immunology", name="Immunology", full_name="Immunology"),
        CategoryNode(id="microbiology", name="Microbiology", full_name="Microbiology"),
        CategoryNode(id="molecular_biology", name="Molecular Biology", full_name="Molecular Biology"),
        CategoryNode(id="neuroscience", name="Neuroscience", full_name="Neuroscience"),
        CategoryNode(id="pathology", name="Pathology", full_name="Pathology"),
        CategoryNode(id="pharmacology", name="Pharmacology", full_name="Pharmacology"),
        CategoryNode(id="physiology", name="Physiology", full_name="Physiology"),
        CategoryNode(id="plant_biology", name="Plant Biology", full_name="Plant Biology"),
        CategoryNode(id="scientific_communication", name="Scientific Communication", full_name="Scientific Communication"),
        CategoryNode(id="synthetic_biology", name="Synthetic Biology", full_name="Synthetic Biology"),
        CategoryNode(id="systems_biology", name="Systems Biology", full_name="Systems Biology"),
        CategoryNode(id="zoology", name="Zoology", full_name="Zoology"),
    ]


# ---------------------------------------------------------------------------
# medRxiv Categories
# ---------------------------------------------------------------------------

def fetch_medrxiv_categories(
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> list[CategoryNode]:
    """Fetch categories from medRxiv API with dynamic discovery.

    Tries to dynamically discover categories by sampling the API.
    Falls back to a comprehensive static list if API fails.

    Args:
        use_cache: Whether to use cached categories.
        force_refresh: Force refresh even if cached.

    Returns:
        List of CategoryNode objects for medRxiv categories.
    """
    import requests

    # Check for cached categories
    cache_key = "medrxiv_categories"
    if use_cache and not force_refresh:
        cached = _get_cached_categories(cache_key)
        if cached:
            return cached

    # Try to dynamically discover categories from API
    discovered = _discover_medrxiv_categories_from_api()

    if discovered:
        # Cache the discovered categories
        _cache_categories(cache_key, discovered)
        return discovered

    # Fallback to comprehensive static list
    logger.info("Using fallback medRxiv categories")
    return _get_medrxiv_fallback_categories()


def _discover_medrxiv_categories_from_api(
    proxy: Optional[dict] = None,
) -> Optional[list[CategoryNode]]:
    """Dynamically discover medRxiv categories by sampling the API.

    Args:
        proxy: Optional proxy dict.

    Returns:
        List of CategoryNode objects or None if discovery fails.
    """
    import requests

    # Sample from different date ranges to get diverse categories
    date_ranges = [
        ("2024-01-01", "2024-12-31"),
        ("2023-01-01", "2023-12-31"),
        ("2020-01-01", "2020-12-31"),
    ]

    all_categories = set()

    for date_from, date_to in date_ranges:
        url = f"https://api.biorxiv.org/details/medrxiv/{date_from}/{date_to}/1"
        try:
            resp = requests.get(url, proxies=proxy, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            collection = data.get("collection", [])

            for item in collection[:100]:
                cat = item.get("category", "").strip()
                if cat:
                    all_categories.add(cat)

            if len(all_categories) > 30:
                break
        except Exception as e:
            logger.debug(f"medRxiv API sample failed for {date_from}: {e}")
            continue

    if not all_categories:
        return None

    result = [
        CategoryNode(
            id=cat.lower().replace(" ", "_").replace("__", "_"),
            name=cat,
            full_name=cat,
        )
        for cat in sorted(all_categories)
    ]
    return result


def _get_medrxiv_fallback_categories() -> list[CategoryNode]:
    """Comprehensive fallback list for medRxiv categories."""
    return [
        CategoryNode(id="addiction_medicine", name="Addiction Medicine", full_name="Addiction Medicine"),
        CategoryNode(id="allergy_immunology", name="Allergy and Immunology", full_name="Allergy and Immunology"),
        CategoryNode(id="anesthesia", name="Anesthesia", full_name="Anesthesia"),
        CategoryNode(id="cardiovascular_medicine", name="Cardiovascular Medicine", full_name="Cardiovascular Medicine"),
        CategoryNode(id="dermatology", name="Dermatology", full_name="Dermatology"),
        CategoryNode(id="emergency_medicine", name="Emergency Medicine", full_name="Emergency Medicine"),
        CategoryNode(id="endocrinology", name="Endocrinology", full_name="Endocrinology"),
        CategoryNode(id="epidemiology", name="Epidemiology", full_name="Epidemiology"),
        CategoryNode(id="forensic_medicine", name="Forensic Medicine", full_name="Forensic Medicine"),
        CategoryNode(id="gastroenterology", name="Gastroenterology", full_name="Gastroenterology"),
        CategoryNode(id="genetic_genomic_medicine", name="Genetic and Genomic Medicine", full_name="Genetic and Genomic Medicine"),
        CategoryNode(id="geriatric_medicine", name="Geriatric Medicine", full_name="Geriatric Medicine"),
        CategoryNode(id="health_economics", name="Health Economics", full_name="Health Economics"),
        CategoryNode(id="health_informatics", name="Health Informatics", full_name="Health Informatics"),
        CategoryNode(id="health_policy", name="Health Policy", full_name="Health Policy"),
        CategoryNode(id="hematology", name="Hematology", full_name="Hematology"),
        CategoryNode(id="hiv_aids", name="HIV/AIDS", full_name="HIV/AIDS"),
        CategoryNode(id="infectious_diseases", name="Infectious Diseases", full_name="Infectious Diseases"),
        CategoryNode(id="intensive_care_critical_care_medicine", name="Intensive Care and Critical Care Medicine", full_name="Intensive Care and Critical Care Medicine"),
        CategoryNode(id="medical_education", name="Medical Education", full_name="Medical Education"),
        CategoryNode(id="mental_health", name="Mental Health", full_name="Mental Health"),
        CategoryNode(id="neurology", name="Neurology", full_name="Neurology"),
        CategoryNode(id="nursing", name="Nursing", full_name="Nursing"),
        CategoryNode(id="obstetrics_gynecology", name="Obstetrics and Gynecology", full_name="Obstetrics and Gynecology"),
        CategoryNode(id="oncology", name="Oncology", full_name="Oncology"),
        CategoryNode(id="ophthalmology", name="Ophthalmology", full_name="Ophthalmology"),
        CategoryNode(id="orthopedics", name="Orthopedics", full_name="Orthopedics"),
        CategoryNode(id="otolaryngology", name="Otolaryngology", full_name="Otolaryngology"),
        CategoryNode(id="palliative_medicine", name="Palliative Medicine", full_name="Palliative Medicine"),
        CategoryNode(id="pathology", name="Pathology", full_name="Pathology"),
        CategoryNode(id="pediatrics", name="Pediatrics", full_name="Pediatrics"),
        CategoryNode(id="pharmacology_therapeutics", name="Pharmacology and Therapeutics", full_name="Pharmacology and Therapeutics"),
        CategoryNode(id="primary_care", name="Primary Care", full_name="Primary Care"),
        CategoryNode(id="psychiatry_clinical_psychology", name="Psychiatry and Clinical Psychology", full_name="Psychiatry and Clinical Psychology"),
        CategoryNode(id="public_global_health", name="Public and Global Health", full_name="Public and Global Health"),
        CategoryNode(id="radiology_imaging", name="Radiology and Imaging", full_name="Radiology and Imaging"),
        CategoryNode(id="rehabilitation_medicine", name="Rehabilitation Medicine", full_name="Rehabilitation Medicine"),
        CategoryNode(id="respiratory_medicine", name="Respiratory Medicine", full_name="Respiratory Medicine"),
        CategoryNode(id="rheumatology", name="Rheumatology", full_name="Rheumatology"),
        CategoryNode(id="sport_medicine", name="Sports Medicine", full_name="Sports Medicine"),
        CategoryNode(id="surgery", name="Surgery", full_name="Surgery"),
        CategoryNode(id="toxicology", name="Toxicology", full_name="Toxicology"),
        CategoryNode(id="transplantation", name="Transplantation", full_name="Transplantation"),
        CategoryNode(id="urology", name="Urology", full_name="Urology"),
    ]


# ---------------------------------------------------------------------------
# Category Search
# ---------------------------------------------------------------------------

def search_categories(
    *,
    query: str,
    server: Optional[str] = None,
    top_k: int = 20,
) -> list[dict]:
    """Search categories by keyword across all servers.
    
    Args:
        query: Search query (keyword).
        server: Filter by server ("arxiv", "biorxiv", "medrxiv"). None = all.
        top_k: Maximum results.
        
    Returns:
        List of matching categories with server info.
    """
    query_lower = query.lower()
    query_terms = set(_tokenize(query_lower))
    
    results = []
    
    if server is None or server == "arxiv":
        arxiv_cats = fetch_arxiv_categories()
        for cat in _flatten_categories(arxiv_cats):
            score = _category_match_score(cat, query_terms)
            if score > 0:
                results.append({
                    "server": "arxiv",
                    "category": cat,
                    "score": score,
                })
    
    if server is None or server == "biorxiv":
        biorxiv_cats = fetch_biorxiv_categories()
        for cat in biorxiv_cats:
            score = _category_match_score(cat, query_terms)
            if score > 0:
                results.append({
                    "server": "biorxiv",
                    "category": cat.to_dict(),
                    "score": score,
                })
    
    if server is None or server == "medrxiv":
        medrxiv_cats = fetch_medrxiv_categories()
        for cat in medrxiv_cats:
            score = _category_match_score(cat, query_terms)
            if score > 0:
                results.append({
                    "server": "medrxiv",
                    "category": cat.to_dict(),
                    "score": score,
                })
    
    # Sort by score and return top_k
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _category_match_score(cat: dict, query_terms: set[str]) -> int:
    """Calculate match score between query and category."""
    cat_text = f"{cat.get('id', '')} {cat.get('name', '')} {cat.get('full_name', '')} {cat.get('description', '')}".lower()
    cat_terms = _tokenize(cat_text)
    
    # Count matching terms
    overlap = len(query_terms & cat_terms)
    
    # Boost for ID and name matches
    cat_id = cat.get("id", "").lower()
    cat_name = cat.get("name", "").lower()
    
    id_boost = sum(1 for term in query_terms if term in cat_id) * 3
    name_boost = sum(1 for term in query_terms if term in cat_name) * 2
    
    return overlap + id_boost + name_boost


def _tokenize(text: str) -> set[str]:
    """Simple tokenization."""
    return set(re.findall(r'\b\w+\b', text.lower()))


def _flatten_categories(categories: list[CategoryNode]) -> list[dict]:
    """Flatten category tree to list of dicts."""
    result = []
    for cat in categories:
        result.extend(cat.flatten())
    return result


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def get_all_categories(
    *,
    server: Optional[str] = None,
    flat: bool = False,
) -> dict:
    """Get all categories from specified server(s).
    
    Args:
        server: Filter by server. None = all.
        flat: If True, return flat list instead of hierarchy.
        
    Returns:
        Dict with server -> categories mapping.
    """
    result = {}
    
    if server is None or server == "arxiv":
        cats = fetch_arxiv_categories()
        result["arxiv"] = [c.to_dict() for c in cats] if not flat else _flatten_categories(cats)
    
    if server is None or server == "biorxiv":
        cats = fetch_biorxiv_categories()
        result["biorxiv"] = [c.to_dict() for c in cats] if not flat else _flatten_categories(cats)

    if server is None or server == "medrxiv":
        cats = fetch_medrxiv_categories()
        result["medrxiv"] = [c.to_dict() for c in cats] if not flat else _flatten_categories(cats)

    return result


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

_category_cache: dict = {}
_cache_loaded = False


def _get_cached_categories(key: str) -> Optional[list]:
    """Get cached categories if available."""
    global _category_cache, _cache_loaded
    return _category_cache.get(key)


def _cache_categories(key: str, categories: list) -> None:
    """Cache categories for future use."""
    global _category_cache
    _category_cache[key] = categories
