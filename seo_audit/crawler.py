"""A small, polite, standard-library-only web crawler.

Fetches pages starting from a seed URL, follows internal links breadth-first
up to configurable page/depth limits, records HTTP status + redirect chains,
and parses each HTML page into a Page. Also fetches robots.txt and sitemap.xml
so the technical checks have something to look at.
"""

from __future__ import annotations

import gzip
import time
import urllib.error
import urllib.request
import urllib.robotparser
import zlib
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

from . import __version__
from .htmlparse import parse_html
from .model import JsonLd, Page

USER_AGENT = f"website-seo-audit/{__version__} (+https://github.com/zxhydfzr/website-seo-audit)"
_MAX_READ = 5 * 1024 * 1024  # never read more than 5 MB of a single response

# Extensions we won't try to crawl as HTML pages (still link-checkable).
_ASSET_EXT = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif",
    ".css", ".js", ".json", ".xml", ".rss", ".pdf", ".zip", ".gz", ".tar",
    ".mp4", ".webm", ".mp3", ".wav", ".woff", ".woff2", ".ttf", ".eot",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".dmg", ".exe",
)


class FetchResult:
    def __init__(self) -> None:
        self.status: Optional[int] = None
        self.final_url: str = ""
        self.headers: Dict[str, str] = {}
        self.body: str = ""
        self.content_type: str = ""
        self.transfer_bytes: int = 0
        self.html_bytes: int = 0
        self.redirects: List[Tuple[int, str]] = []
        self.error: Optional[str] = None

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type.lower()


class _RedirectRecorder(urllib.request.HTTPRedirectHandler):
    """Captures the (code, url) hops of a redirect chain for one fetch."""

    def __init__(self) -> None:
        super().__init__()
        self.chain: List[Tuple[int, str]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize(url: str, base: Optional[str] = None) -> str:
    """Resolve against base, drop fragments, normalise scheme/host case and
    default ports. Keeps query strings and trailing slashes intact."""
    if base:
        url = urljoin(base, url)
    parts = urlparse(url)
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    host = host.lower()
    netloc = host
    if parts.port and not (
        (scheme == "http" and parts.port == 80) or (scheme == "https" and parts.port == 443)
    ):
        netloc = f"{host}:{parts.port}"
    return urlunparse((scheme, netloc, parts.path or "/", parts.params, parts.query, ""))


def registrable_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, root_url: str) -> bool:
    """Treat apex and www as the same site; other subdomains are external."""
    return registrable_host(url) == registrable_host(root_url) and registrable_host(url) != ""


def is_http(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def looks_like_asset(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(_ASSET_EXT)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _decode_body(raw: bytes, encoding: str, charset: Optional[str]) -> str:
    if "gzip" in encoding:
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
    elif "deflate" in encoding:
        try:
            raw = zlib.decompress(raw)
        except Exception:
            try:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                pass
    for enc in (charset, "utf-8", "latin-1"):
        if not enc:
            continue
        try:
            return raw.decode(enc, errors="replace")
        except (LookupError, Exception):
            continue
    return raw.decode("utf-8", errors="replace")


def fetch(url: str, timeout: float = 15.0, user_agent: str = USER_AGENT,
          method: str = "GET") -> FetchResult:
    res = FetchResult()
    recorder = _RedirectRecorder()
    opener = urllib.request.build_opener(recorder)
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        resp = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        res.status = e.code
        res.final_url = e.url or url
        res.redirects = recorder.chain
        res.content_type = e.headers.get("Content-Type", "") if e.headers else ""
        try:
            raw = e.read(_MAX_READ)
            res.transfer_bytes = len(raw)
            if res.is_html:
                res.body = _decode_body(raw, (e.headers.get("Content-Encoding", "") if e.headers else ""), None)
                res.html_bytes = len(res.body.encode("utf-8", "replace"))
        except Exception:
            pass
        return res
    except urllib.error.URLError as e:
        res.error = f"{type(e).__name__}: {getattr(e, 'reason', e)}"
        return res
    except Exception as e:  # noqa: BLE001 — network layer throws many things
        res.error = f"{type(e).__name__}: {e}"
        return res

    with resp:
        res.status = getattr(resp, "status", None) or resp.getcode()
        res.final_url = resp.geturl()
        res.redirects = recorder.chain
        res.headers = {k.lower(): v for k, v in resp.headers.items()}
        res.content_type = resp.headers.get("Content-Type", "")
        try:
            raw = resp.read(_MAX_READ)
        except Exception as e:  # noqa: BLE001
            res.error = f"read failed: {e}"
            return res
        res.transfer_bytes = len(raw)
        if res.is_html or "xml" in res.content_type.lower():
            charset = None
            ct = res.content_type.lower()
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].split(";")[0].strip()
            res.body = _decode_body(raw, res.headers.get("content-encoding", ""), charset)
            res.html_bytes = len(res.body.encode("utf-8", "replace"))
    return res


# ---------------------------------------------------------------------------
# robots.txt / sitemap
# ---------------------------------------------------------------------------

def load_robots(site_url: str, timeout: float, user_agent: str):
    """Returns (info_dict, RobotFileParser|None)."""
    robots_url = urljoin(site_url, "/robots.txt")
    info = {"exists": False, "url": robots_url, "blocks_all": False, "sitemaps": [], "error": None}
    fr = fetch(robots_url, timeout=timeout, user_agent=user_agent)
    rp = urllib.robotparser.RobotFileParser()
    if fr.error or fr.status is None:
        info["error"] = fr.error or "no response"
        rp.allow_all = True
        return info, rp
    if fr.status >= 400:
        info["error"] = f"HTTP {fr.status}"
        rp.allow_all = True
        return info, rp
    info["exists"] = True
    text = fr.body if fr.body else ""
    if not text:
        # robots.txt may not be flagged text/html; refetch decoded regardless.
        text = _fetch_text(robots_url, timeout, user_agent)
    lines = text.splitlines()
    rp.parse(lines)
    ua_star = False
    for line in lines:
        s = line.strip()
        low = s.lower()
        if low.startswith("user-agent:"):
            ua_star = s.split(":", 1)[1].strip() == "*"
        elif low.startswith("sitemap:"):
            info["sitemaps"].append(s.split(":", 1)[1].strip())
        elif ua_star and low.replace(" ", "") == "disallow:/":
            info["blocks_all"] = True
    return info, rp


def _fetch_text(url: str, timeout: float, user_agent: str) -> str:
    """Fetch a text resource (robots/sitemap) regardless of content-type."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(_MAX_READ)
            enc = resp.headers.get("Content-Encoding", "")
            return _decode_body(raw, enc, None)
    except Exception:
        return ""


def load_sitemap(site_url: str, robots_info: dict, timeout: float, user_agent: str) -> dict:
    """Find and lightly validate a sitemap. Prefers robots.txt Sitemap: lines,
    falls back to /sitemap.xml. Counts <loc> entries; follows a sitemap index
    one level to sum child URL counts (bounded)."""
    candidates = list(robots_info.get("sitemaps") or [])
    candidates.append(urljoin(site_url, "/sitemap.xml"))
    info = {"exists": False, "url": None, "valid": False, "url_count": 0, "error": None, "is_index": False}
    for cand in candidates:
        text = _fetch_text(cand, timeout, user_agent)
        if not text or "<" not in text:
            continue
        info["exists"] = True
        info["url"] = cand
        low = text.lower()
        info["valid"] = ("<urlset" in low) or ("<sitemapindex" in low)
        locs = _count_locs(text)
        if "<sitemapindex" in low:
            info["is_index"] = True
            total = 0
            child_urls = _extract_locs(text)[:20]  # bound the fan-out
            for child in child_urls:
                total += _count_locs(_fetch_text(child, timeout, user_agent))
            info["url_count"] = total or locs
        else:
            info["url_count"] = locs
        return info
    info["error"] = "not found"
    return info


def _count_locs(xml: str) -> int:
    return xml.lower().count("<loc>")


def _extract_locs(xml: str) -> List[str]:
    import re
    return [m.strip() for m in re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, flags=re.I | re.S)]


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

class Crawler:
    def __init__(self, start_url: str, max_pages: int = 50, max_depth: int = 3,
                 timeout: float = 15.0, delay: float = 0.3, user_agent: str = USER_AGENT,
                 respect_robots: bool = True, on_progress=None):
        self.start_url = normalize(start_url)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.delay = delay
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self.on_progress = on_progress
        self.robots_info: dict = {}
        self._rp = None

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots or self._rp is None:
            return True
        try:
            return self._rp.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def crawl(self):
        """Returns (pages, robots_info, rp). Populates each Page with parsed
        fields. Link status (for dead-link detection) is resolved separately."""
        self.robots_info, self._rp = load_robots(self.start_url, self.timeout, self.user_agent)

        pages: List[Page] = []
        seen: Set[str] = set()
        queue: List[Tuple[str, int]] = [(self.start_url, 0)]
        seen.add(self.start_url)

        while queue and len(pages) < self.max_pages:
            url, depth = queue.pop(0)
            if self.respect_robots and not self._allowed(url):
                continue
            if self.on_progress:
                self.on_progress(len(pages) + 1, self.max_pages, url)

            page = self._fetch_page(url, depth)
            pages.append(page)

            if page.is_html and page.ok and depth < self.max_depth:
                for link in page.internal_links:
                    if link not in seen and not looks_like_asset(link):
                        seen.add(link)
                        queue.append((link, depth + 1))
            if self.delay:
                time.sleep(self.delay)
        return pages, self.robots_info, self._rp

    def _fetch_page(self, url: str, depth: int) -> Page:
        fr = fetch(url, timeout=self.timeout, user_agent=self.user_agent)
        page = Page(
            url=url,
            depth=depth,
            status_code=fr.status,
            final_url=fr.final_url or url,
            redirect_chain=fr.redirects,
            content_type=fr.content_type,
            transfer_bytes=fr.transfer_bytes,
            html_bytes=fr.html_bytes,
            fetch_error=fr.error,
            is_html=fr.is_html,
        )
        if fr.is_html and fr.body:
            self._parse_onto(page, fr.body)
        return page

    def _parse_onto(self, page: Page, html: str) -> None:
        data = parse_html(html)
        page.title = data["title"]
        page.meta_description = data["meta_description"]
        page.meta_robots = data["meta_robots"]
        page.viewport = data["viewport"]
        page.canonical = data["canonical"]
        page.lang = data["lang"]
        page.charset = data["charset"]
        page.headings = data["headings"]
        page.h1s = data["h1s"]
        page.images = data["images"]
        page.og = data["og"]
        page.twitter = data["twitter"]
        page.word_count = data["word_count"]

        base = page.final_url or page.url
        page_is_https = urlparse(base).scheme == "https"

        for href, _rel in data["links"]:
            if href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
                continue
            absu = normalize(href, base)
            if not is_http(absu):
                continue
            if same_site(absu, self.start_url):
                page.internal_links.append(absu)
            else:
                page.external_links.append(absu)
        # de-dupe, preserve order
        page.internal_links = list(dict.fromkeys(page.internal_links))
        page.external_links = list(dict.fromkeys(page.external_links))

        # mixed content: http assets on an https page
        if page_is_https:
            for _kind, src in data["resources"]:
                absu = urljoin(base, src)
                if urlparse(absu).scheme == "http":
                    page.mixed_content.append(absu)
            page.mixed_content = list(dict.fromkeys(page.mixed_content))

        # parse JSON-LD blocks
        import json
        for raw in data["jsonld_raw"]:
            block = JsonLd(raw=raw)
            try:
                block.data = json.loads(raw)
            except Exception as e:  # noqa: BLE001
                block.parse_error = str(e)
            page.jsonld.append(block)


def resolve_link_statuses(pages: List[Page], timeout: float, user_agent: str,
                          limit: int = 300, delay: float = 0.1, on_progress=None):
    """Return ({url: status_or_None}, total_targets, checked) for every
    internal link target, so dead links can be flagged. Statuses of pages we
    already crawled are reused; only the remainder hit the network, bounded by
    ``limit`` so a big site can't blow up runtime."""
    known: Dict[str, Optional[int]] = {}
    for p in pages:
        known[p.url] = p.status_code
        if p.final_url:
            known[normalize(p.final_url)] = p.status_code

    targets: List[str] = []
    seen: Set[str] = set(known)
    for p in pages:
        for link in p.internal_links:
            if link not in seen:
                seen.add(link)
                targets.append(link)

    statuses: Dict[str, Optional[int]] = dict(known)
    checked = 0
    to_check = min(len(targets), limit)
    for url in targets:
        if checked >= limit:
            break
        if on_progress:
            on_progress(checked + 1, to_check, url)
        fr = fetch(url, timeout=timeout, user_agent=user_agent, method="HEAD")
        status = fr.status
        if status is None or status in (403, 405, 501):  # some servers dislike HEAD
            fr = fetch(url, timeout=timeout, user_agent=user_agent, method="GET")
            status = fr.status
        statuses[url] = status
        checked += 1
        if delay:
            time.sleep(delay)
    return statuses, len(targets), checked
