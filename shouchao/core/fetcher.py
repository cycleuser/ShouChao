"""
HTTP fetchers for ShouChao.

Multiple backends for fetching web pages with human-like behavior.
Adapted from Huan's fetcher architecture.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Chromium";v="131", "Google Chrome";v="131", '
                 '"Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "DNT": "1",
    "Cache-Control": "max-age=0",
}

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class BaseFetcher(ABC):
    """Abstract base for HTTP fetchers."""

    @abstractmethod
    def fetch(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch a URL. Returns (html_content, error_message)."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release resources."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Fetcher backend name."""
        pass


class RequestsFetcher(BaseFetcher):
    """Standard requests-based fetcher with browser-like headers."""

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30,
    ):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self._session = requests.Session()
        self._session.headers.update(BROWSER_HEADERS)
        self._session.headers["User-Agent"] = user_agent
        self._verify = verify_ssl
        self._timeout = timeout

        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

        retry = Retry(total=2, backoff_factor=0.5,
                      status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def fetch(self, url: str) -> tuple[Optional[str], Optional[str]]:
        try:
            resp = self._session.get(
                url, timeout=self._timeout, verify=self._verify
            )
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text, None
        except Exception as e:
            return None, str(e)

    def close(self) -> None:
        self._session.close()

    @property
    def name(self) -> str:
        return "requests"


class CurlCffiFetcher(BaseFetcher):
    """curl_cffi fetcher with TLS fingerprint impersonation."""

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30,
    ):
        try:
            from curl_cffi.requests import Session
        except ImportError:
            raise ImportError(
                "curl_cffi not installed. Run: pip install curl-cffi"
            )
        self._session = Session(impersonate="chrome")
        self._session.headers.update(BROWSER_HEADERS)
        self._session.headers["User-Agent"] = user_agent
        self._verify = verify_ssl
        self._timeout = timeout
        self._proxy = proxy

    def fetch(self, url: str) -> tuple[Optional[str], Optional[str]]:
        try:
            kwargs = {"timeout": self._timeout, "verify": self._verify}
            if self._proxy:
                kwargs["proxies"] = {"http": self._proxy, "https": self._proxy}
            resp = self._session.get(url, **kwargs)
            resp.raise_for_status()
            return resp.text, None
        except Exception as e:
            return None, str(e)

    def close(self) -> None:
        self._session.close()

    @property
    def name(self) -> str:
        return "curl_cffi"


class PlaywrightFetcher(BaseFetcher):
    """Playwright headless Chromium fetcher with JS rendering."""

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30,
    ):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "playwright not installed. Run: pip install playwright && "
                "playwright install chromium"
            )
        self._pw = sync_playwright().start()
        launch_args = {}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        if not verify_ssl:
            launch_args["ignore_https_errors"] = True
        self._browser = self._pw.chromium.launch(
            headless=True, **launch_args
        )
        self._context = self._browser.new_context(user_agent=user_agent)
        self._timeout = timeout * 1000  # ms

    def fetch(self, url: str) -> tuple[Optional[str], Optional[str]]:
        try:
            page = self._context.new_page()
            page.goto(url, wait_until="networkidle", timeout=self._timeout)
            page.wait_for_timeout(500)
            html = page.content()
            page.close()
            return html, None
        except Exception as e:
            return None, str(e)

    def close(self) -> None:
        try:
            self._context.close()
            self._browser.close()
            self._pw.stop()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return "playwright"


class DrissionPageFetcher(BaseFetcher):
    """DrissionPage fetcher using system Chrome with scroll support."""

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30,
        scroll_count: int = 5,
    ):
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
        except ImportError:
            raise ImportError(
                "DrissionPage not installed. Run: pip install DrissionPage"
            )
        opts = ChromiumOptions()
        opts.headless()
        opts.set_argument("--no-sandbox")
        opts.set_argument("--disable-gpu")
        if user_agent:
            opts.set_user_agent(user_agent)
        if proxy:
            opts.set_proxy(proxy)
        self._page = ChromiumPage(opts)
        self._timeout = timeout
        self._scroll_count = scroll_count

    def fetch(self, url: str) -> tuple[Optional[str], Optional[str]]:
        try:
            self._page.get(url, timeout=self._timeout)
            # Scroll to load lazy content
            for _ in range(self._scroll_count):
                self._page.scroll.down(800)
                time.sleep(0.3)
            html = self._page.html
            return html, None
        except Exception as e:
            return None, str(e)

    def close(self) -> None:
        try:
            self._page.quit()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return "drission"


def create_fetcher(
    fetcher_type: str = "requests",
    user_agent: str = DEFAULT_UA,
    verify_ssl: bool = True,
    proxy: Optional[str] = None,
    timeout: int = 30,
    scroll_count: int = 5,
) -> BaseFetcher:
    """Create a fetcher instance with fallback chain."""
    classes = {
        "requests": (RequestsFetcher, {}),
        "curl": (CurlCffiFetcher, {}),
        "browser": (DrissionPageFetcher, {"scroll_count": scroll_count}),
        "playwright": (PlaywrightFetcher, {}),
    }

    # Try requested type first, then fallback
    order = [fetcher_type] + [k for k in classes if k != fetcher_type]

    for ft in order:
        if ft not in classes:
            continue
        cls, extra = classes[ft]
        try:
            return cls(
                user_agent=user_agent,
                verify_ssl=verify_ssl,
                proxy=proxy,
                timeout=timeout,
                **extra,
            )
        except ImportError as e:
            if ft == fetcher_type:
                logger.warning("Fetcher '%s' unavailable: %s", ft, e)
            continue

    # RequestsFetcher should always work
    return RequestsFetcher(user_agent=user_agent, verify_ssl=verify_ssl,
                           proxy=proxy, timeout=timeout)


class RateLimiter:
    """Per-domain rate limiter."""

    def __init__(self, default_delay: float = 1.0):
        self._last_access: dict[str, float] = {}
        self._delay = default_delay

    def wait(self, url: str) -> None:
        """Wait if needed before accessing the domain."""
        domain = urlparse(url).netloc
        now = time.time()
        last = self._last_access.get(domain, 0)
        elapsed = now - last
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_access[domain] = time.time()
