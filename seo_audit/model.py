"""Data model for the SEO audit.

Everything the crawler discovers about a page lands on :class:`Page`.
Every problem found by a check lands as an :class:`Issue`. The whole run is
collected into a :class:`Report`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Issue severities, ordered most -> least serious.
CRITICAL = "critical"   # 🔴 actively hurts indexing / rankings — fix now
WARNING = "warning"     # 🟡 clear SEO problem — fix soon
NOTICE = "notice"       # 🟢 minor / best-practice nudge

SEVERITY_ORDER = {CRITICAL: 0, WARNING: 1, NOTICE: 2}
SEVERITY_EMOJI = {CRITICAL: "🔴", WARNING: "🟡", NOTICE: "🟢"}


@dataclass
class ImageInfo:
    src: str
    alt: Optional[str] = None      # None = attribute missing; "" = present but empty
    width: Optional[str] = None
    height: Optional[str] = None


@dataclass
class JsonLd:
    raw: str
    data: Any = None               # parsed JSON (dict/list) or None on parse error
    parse_error: Optional[str] = None


@dataclass
class Page:
    """One fetched URL and everything extracted from it."""

    url: str
    depth: int = 0

    # transport
    status_code: Optional[int] = None
    final_url: str = ""            # after following redirects
    redirect_chain: List[Tuple[int, str]] = field(default_factory=list)
    content_type: str = ""
    transfer_bytes: int = 0        # bytes on the wire (post-compression)
    html_bytes: int = 0            # decoded HTML size
    fetch_error: Optional[str] = None
    is_html: bool = False

    # head / meta
    title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_robots: Optional[str] = None
    canonical: Optional[str] = None
    lang: Optional[str] = None
    viewport: Optional[str] = None
    charset: Optional[str] = None

    # body
    headings: List[Tuple[int, str]] = field(default_factory=list)  # (level, text)
    h1s: List[str] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    internal_links: List[str] = field(default_factory=list)        # normalized
    external_links: List[str] = field(default_factory=list)
    jsonld: List[JsonLd] = field(default_factory=list)
    og: Dict[str, str] = field(default_factory=dict)
    twitter: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    mixed_content: List[str] = field(default_factory=list)         # http:// assets on https page

    @property
    def ok(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300


@dataclass
class Issue:
    severity: str
    code: str                      # short stable slug, e.g. "title_missing"
    message: str                   # what's wrong
    fix: str = ""                  # how to fix it
    url: Optional[str] = None      # page URL, or None for a site-wide issue
    detail: str = ""               # extra context (values, counts, examples)


@dataclass
class Report:
    start_url: str
    site_url: str = ""             # scheme://host of the start URL
    pages: List[Page] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    robots: Dict[str, Any] = field(default_factory=dict)   # {exists,url,blocks_all,sitemaps,error}
    sitemap: Dict[str, Any] = field(default_factory=dict)  # {exists,url,url_count,valid,error}
    score: int = 100
    started_at: str = ""
    finished_at: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def counts(self) -> Dict[str, int]:
        c = {CRITICAL: 0, WARNING: 0, NOTICE: 0}
        for i in self.issues:
            c[i.severity] = c.get(i.severity, 0) + 1
        return c
