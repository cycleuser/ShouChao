"""
News source registry for ShouChao.

Defines NewsSource dataclass and SOURCE_REGISTRY covering 10 languages
with major news outlets from around the world.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

CATEGORY_TAGS = frozenset([
    "politics", "economy", "technology", "science",
    "health", "environment", "culture", "sports",
])


class SourceType(Enum):
    """Type of news source."""
    RSS = "rss"
    WEB = "web"


@dataclass
class NewsSource:
    """A single news source definition."""
    name: str
    language: str
    url: str
    source_type: SourceType = SourceType.WEB
    category: list = field(default_factory=lambda: ["politics", "economy"])
    rss_url: Optional[str] = None
    fetcher_hint: str = "requests"
    article_selector: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "language": self.language,
            "url": self.url,
            "source_type": self.source_type.value,
            "category": self.category,
            "rss_url": self.rss_url,
            "fetcher_hint": self.fetcher_hint,
            "article_selector": self.article_selector,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NewsSource":
        data = dict(data)
        if "source_type" in data:
            data["source_type"] = SourceType(data["source_type"])
        return cls(**data)


# ---------------------------------------------------------------------------
# SOURCE_REGISTRY: curated news sources grouped by language code
# ---------------------------------------------------------------------------

SOURCE_REGISTRY: dict[str, list[NewsSource]] = {
    # ---- Chinese (zh) ----
    "zh": [
        NewsSource("新华网", "zh", "https://www.xinhuanet.com",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.xinhuanet.com/rss/politics.xml"),
        NewsSource("人民日报", "zh", "https://www.people.com.cn",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("财新网", "zh", "https://www.caixin.com",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("澎湃新闻", "zh", "https://www.thepaper.cn",
                   SourceType.WEB, ["politics", "economy", "culture"]),
        NewsSource("南华早报", "zh", "https://www.scmp.com",
                   SourceType.RSS, ["politics", "economy", "technology"],
                   rss_url="https://www.scmp.com/rss/91/feed"),
        NewsSource("环球时报", "zh", "https://www.globaltimes.cn",
                   SourceType.WEB, ["politics"]),
        NewsSource("中国日报", "zh", "https://www.chinadaily.com.cn",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.chinadaily.com.cn/rss/china_rss.xml"),
        NewsSource("第一财经", "zh", "https://www.yicai.com",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("新浪新闻", "zh", "https://news.sina.com.cn",
                   SourceType.WEB, ["politics", "economy", "culture"]),
        NewsSource("界面新闻", "zh", "https://www.jiemian.com",
                   SourceType.WEB, ["economy", "technology"]),
    ],

    # ---- English (en) ----
    "en": [
        NewsSource("Reuters", "en", "https://www.reuters.com",
                   SourceType.RSS, ["politics", "economy", "technology"],
                   rss_url="https://www.reuters.com/rssFeed/worldNews"),
        NewsSource("BBC News", "en", "https://www.bbc.com/news",
                   SourceType.RSS, ["politics", "economy", "science"],
                   rss_url="https://feeds.bbci.co.uk/news/rss.xml"),
        NewsSource("AP News", "en", "https://apnews.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Bloomberg", "en", "https://www.bloomberg.com",
                   SourceType.WEB, ["economy", "technology"],
                   fetcher_hint="curl"),
        NewsSource("The Guardian", "en", "https://www.theguardian.com",
                   SourceType.RSS, ["politics", "environment", "culture"],
                   rss_url="https://www.theguardian.com/world/rss"),
        NewsSource("Al Jazeera", "en", "https://www.aljazeera.com",
                   SourceType.RSS, ["politics"],
                   rss_url="https://www.aljazeera.com/xml/rss/all.xml"),
        NewsSource("NPR", "en", "https://www.npr.org",
                   SourceType.RSS, ["politics", "culture", "science"],
                   rss_url="https://feeds.npr.org/1001/rss.xml"),
        NewsSource("The Economist", "en", "https://www.economist.com",
                   SourceType.WEB, ["economy", "politics"],
                   fetcher_hint="curl"),
        NewsSource("CNN", "en", "https://edition.cnn.com",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="http://rss.cnn.com/rss/edition_world.rss"),
        NewsSource("Financial Times", "en", "https://www.ft.com",
                   SourceType.WEB, ["economy", "technology"],
                   fetcher_hint="curl"),
        NewsSource("The New York Times", "en", "https://www.nytimes.com",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
        NewsSource("TechCrunch", "en", "https://techcrunch.com",
                   SourceType.RSS, ["technology"],
                   rss_url="https://techcrunch.com/feed/"),
    ],

    # ---- Japanese (ja) ----
    "ja": [
        NewsSource("NHK", "ja", "https://www3.nhk.or.jp/news/",
                   SourceType.RSS, ["politics", "economy", "science"],
                   rss_url="https://www3.nhk.or.jp/rss/news/cat0.xml"),
        NewsSource("朝日新聞", "ja", "https://www.asahi.com",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://www.asahi.com/rss/asahi/newsheadlines.rdf"),
        NewsSource("日本経済新聞", "ja", "https://www.nikkei.com",
                   SourceType.WEB, ["economy", "technology"],
                   fetcher_hint="curl"),
        NewsSource("毎日新聞", "ja", "https://mainichi.jp",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://mainichi.jp/rss/etc/mainichi-flash.rss"),
        NewsSource("読売新聞", "ja", "https://www.yomiuri.co.jp",
                   SourceType.WEB, ["politics", "economy", "sports"]),
        NewsSource("産経新聞", "ja", "https://www.sankei.com",
                   SourceType.WEB, ["politics"]),
        NewsSource("共同通信", "ja", "https://www.47news.jp",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("東洋経済", "ja", "https://toyokeizai.net",
                   SourceType.WEB, ["economy", "technology"]),
    ],

    # ---- French (fr) ----
    "fr": [
        NewsSource("Le Monde", "fr", "https://www.lemonde.fr",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://www.lemonde.fr/rss/une.xml"),
        NewsSource("France 24", "fr", "https://www.france24.com/fr/",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.france24.com/fr/rss"),
        NewsSource("Le Figaro", "fr", "https://www.lefigaro.fr",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.lefigaro.fr/rss/figaro_actualites.xml"),
        NewsSource("AFP", "fr", "https://www.afp.com/fr",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Libération", "fr", "https://www.liberation.fr",
                   SourceType.WEB, ["politics", "culture"]),
        NewsSource("Les Échos", "fr", "https://www.lesechos.fr",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("RFI", "fr", "https://www.rfi.fr/fr/",
                   SourceType.RSS, ["politics"],
                   rss_url="https://www.rfi.fr/fr/rss"),
        NewsSource("Le Point", "fr", "https://www.lepoint.fr",
                   SourceType.WEB, ["politics", "economy"]),
    ],

    # ---- Russian (ru) ----
    "ru": [
        NewsSource("ТАСС", "ru", "https://tass.ru",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://tass.ru/rss/v2.xml"),
        NewsSource("РИА Новости", "ru", "https://ria.ru",
                   SourceType.RSS, ["politics", "economy", "science"],
                   rss_url="https://ria.ru/export/rss2/index.xml"),
        NewsSource("Коммерсантъ", "ru", "https://www.kommersant.ru",
                   SourceType.RSS, ["economy", "politics"],
                   rss_url="https://www.kommersant.ru/RSS/main.xml"),
        NewsSource("Ведомости", "ru", "https://www.vedomosti.ru",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("RT", "ru", "https://russian.rt.com",
                   SourceType.RSS, ["politics"],
                   rss_url="https://russian.rt.com/rss"),
        NewsSource("Lenta.ru", "ru", "https://lenta.ru",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://lenta.ru/rss"),
        NewsSource("Interfax", "ru", "https://www.interfax.ru",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Газета.ru", "ru", "https://www.gazeta.ru",
                   SourceType.WEB, ["politics", "economy", "science"]),
    ],

    # ---- German (de) ----
    "de": [
        NewsSource("Deutsche Welle", "de", "https://www.dw.com/de/",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://rss.dw.com/xml/rss-de-all"),
        NewsSource("Der Spiegel", "de", "https://www.spiegel.de",
                   SourceType.RSS, ["politics", "economy", "science"],
                   rss_url="https://www.spiegel.de/schlagzeilen/tops/index.rss"),
        NewsSource("FAZ", "de", "https://www.faz.net",
                   SourceType.RSS, ["economy", "politics"],
                   rss_url="https://www.faz.net/rss/aktuell/"),
        NewsSource("Die Zeit", "de", "https://www.zeit.de",
                   SourceType.RSS, ["politics", "culture"],
                   rss_url="https://newsfeed.zeit.de/index"),
        NewsSource("Süddeutsche Zeitung", "de", "https://www.sueddeutsche.de",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Handelsblatt", "de", "https://www.handelsblatt.com",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("Tagesschau", "de", "https://www.tagesschau.de",
                   SourceType.RSS, ["politics"],
                   rss_url="https://www.tagesschau.de/xml/rss2/"),
        NewsSource("n-tv", "de", "https://www.n-tv.de",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.n-tv.de/rss"),
    ],

    # ---- Italian (it) ----
    "it": [
        NewsSource("ANSA", "it", "https://www.ansa.it",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.ansa.it/sito/ansait_rss.xml"),
        NewsSource("Corriere della Sera", "it", "https://www.corriere.it",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://xml2.corriereobjects.it/rss/homepage.xml"),
        NewsSource("La Repubblica", "it", "https://www.repubblica.it",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.repubblica.it/rss/homepage/rss2.0.xml"),
        NewsSource("Il Sole 24 Ore", "it", "https://www.ilsole24ore.com",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("La Stampa", "it", "https://www.lastampa.it",
                   SourceType.WEB, ["politics", "culture"]),
        NewsSource("AGI", "it", "https://www.agi.it",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Sky TG24", "it", "https://tg24.sky.it",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://tg24.sky.it/rss/tg24_it.xml"),
        NewsSource("Il Post", "it", "https://www.ilpost.it",
                   SourceType.RSS, ["politics", "culture"],
                   rss_url="https://www.ilpost.it/feed/"),
    ],

    # ---- Spanish (es) ----
    "es": [
        NewsSource("El País", "es", "https://elpais.com",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
        NewsSource("EFE", "es", "https://www.efe.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("El Mundo", "es", "https://www.elmundo.es",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"),
        NewsSource("ABC", "es", "https://www.abc.es",
                   SourceType.RSS, ["politics", "culture"],
                   rss_url="https://www.abc.es/rss/feeds/abc_ultima.xml"),
        NewsSource("La Vanguardia", "es", "https://www.lavanguardia.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Cinco Días", "es", "https://cincodias.elpais.com",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("Europa Press", "es", "https://www.europapress.es",
                   SourceType.WEB, ["politics"]),
        NewsSource("RTVE", "es", "https://www.rtve.es",
                   SourceType.RSS, ["politics", "culture", "sports"],
                   rss_url="https://www.rtve.es/api/noticias.xml"),
    ],

    # ---- Portuguese (pt) ----
    "pt": [
        NewsSource("Folha de S.Paulo", "pt", "https://www.folha.uol.com.br",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://feeds.folha.uol.com.br/folha/emcimadahora/rss091.xml"),
        NewsSource("Agência Brasil", "pt", "https://agenciabrasil.ebc.com.br",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"),
        NewsSource("Público", "pt", "https://www.publico.pt",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://feeds.feedburner.com/PublicoRSS"),
        NewsSource("Globo", "pt", "https://g1.globo.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("Estadão", "pt", "https://www.estadao.com.br",
                   SourceType.WEB, ["economy", "politics"]),
        NewsSource("Lusa", "pt", "https://www.lusa.pt",
                   SourceType.WEB, ["politics"]),
        NewsSource("RTP", "pt", "https://www.rtp.pt/noticias",
                   SourceType.WEB, ["politics", "economy", "culture"]),
        NewsSource("UOL", "pt", "https://noticias.uol.com.br",
                   SourceType.WEB, ["politics", "economy"]),
    ],

    # ---- Korean (ko) ----
    "ko": [
        NewsSource("연합뉴스", "ko", "https://www.yna.co.kr",
                   SourceType.RSS, ["politics", "economy"],
                   rss_url="https://www.yna.co.kr/rss/news.xml"),
        NewsSource("조선일보", "ko", "https://www.chosun.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("KBS", "ko", "https://news.kbs.co.kr",
                   SourceType.RSS, ["politics", "economy", "culture"],
                   rss_url="https://news.kbs.co.kr/news/RssService.do"),
        NewsSource("중앙일보", "ko", "https://www.joongang.co.kr",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("한겨레", "ko", "https://www.hani.co.kr",
                   SourceType.RSS, ["politics", "culture"],
                   rss_url="https://www.hani.co.kr/rss/"),
        NewsSource("동아일보", "ko", "https://www.donga.com",
                   SourceType.WEB, ["politics", "economy"]),
        NewsSource("매일경제", "ko", "https://www.mk.co.kr",
                   SourceType.WEB, ["economy", "technology"]),
        NewsSource("한국경제", "ko", "https://www.hankyung.com",
                   SourceType.WEB, ["economy", "technology"]),
    ],
}


def get_sources(
    language: str = None,
    category: str = None,
    source_type: SourceType = None,
) -> list[NewsSource]:
    """Filter and return news sources."""
    results = []
    langs = [language] if language else list(SOURCE_REGISTRY.keys())
    for lang in langs:
        for src in SOURCE_REGISTRY.get(lang, []):
            if not src.enabled:
                continue
            if source_type and src.source_type != source_type:
                continue
            if category and category not in src.category:
                continue
            results.append(src)
    # Include custom sources
    for src in _custom_sources:
        if not src.enabled:
            continue
        if language and src.language != language:
            continue
        if source_type and src.source_type != source_type:
            continue
        if category and category not in src.category:
            continue
        results.append(src)
    return results


def get_rss_sources(language: str = None) -> list[NewsSource]:
    """Get all RSS-capable sources."""
    return get_sources(language=language, source_type=SourceType.RSS)


def get_web_sources(language: str = None) -> list[NewsSource]:
    """Get all web scraping sources."""
    return get_sources(language=language, source_type=SourceType.WEB)


# ---------------------------------------------------------------------------
# Custom sources (user-added, persisted to JSON)
# ---------------------------------------------------------------------------

_custom_sources: list[NewsSource] = []


def register_source(source: NewsSource) -> None:
    """Add a custom news source at runtime."""
    _custom_sources.append(source)


def load_custom_sources() -> list[NewsSource]:
    """Load user-added sources from JSON file."""
    global _custom_sources
    from shouchao.core.config import CUSTOM_SOURCES_FILE
    if CUSTOM_SOURCES_FILE.exists():
        try:
            data = json.loads(CUSTOM_SOURCES_FILE.read_text(encoding="utf-8"))
            _custom_sources = [NewsSource.from_dict(d) for d in data]
            logger.debug("Loaded %d custom sources", len(_custom_sources))
        except Exception as e:
            logger.warning("Failed to load custom sources: %s", e)
    return _custom_sources


def save_custom_sources() -> None:
    """Persist custom sources to JSON file."""
    from shouchao.core.config import CUSTOM_SOURCES_FILE, DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = [s.to_dict() for s in _custom_sources]
        CUSTOM_SOURCES_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to save custom sources: %s", e)
