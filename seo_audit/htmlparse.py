"""Single-pass HTML extraction built on the stdlib html.parser.

We deliberately avoid third-party parsers (bs4/lxml) so the tool runs in any
Python 3.8+ environment with zero installation. html.parser is lenient enough
for real-world markup; we only need head metadata, headings, links, images and
JSON-LD blocks, not a perfect DOM.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple

from .model import ImageInfo

_WS = re.compile(r"\s+")
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_TEXT_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        # convert_charrefs decodes entities in normal text but NOT inside
        # script/style, which keeps JSON-LD payloads byte-accurate.
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self._in_title = False

        self.meta_description = None
        self.meta_robots = None
        self.viewport = None
        self.canonical = None
        self.lang = None
        self.charset = None
        self.has_html_tag = False

        self.og: Dict[str, str] = {}
        self.twitter: Dict[str, str] = {}

        self.headings: List[Tuple[int, str]] = []
        self._heading_level = None
        self._heading_parts: List[str] = []

        self.links: List[Tuple[str, str]] = []          # (href, rel)
        self.images: List[ImageInfo] = []
        self.resources: List[Tuple[str, str]] = []       # (kind, url) for mixed-content check

        self.jsonld_raw: List[str] = []
        self._in_ldjson = False
        self._ld_parts: List[str] = []

        self._skip_text = 0
        self._text_parts: List[str] = []

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _attrs(attrs):
        return {k.lower(): (v or "") for k, v in attrs}

    def _open(self, tag: str, attrs) -> None:
        a = self._attrs(attrs)
        if tag == "html":
            self.has_html_tag = True
            if a.get("lang") and not self.lang:
                self.lang = a["lang"].strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._meta(a)
        elif tag == "link":
            rel = a.get("rel", "").strip().lower()
            href = a.get("href", "").strip()
            if href and "canonical" in rel and not self.canonical:
                self.canonical = href
            if href and rel == "stylesheet":
                self.resources.append(("stylesheet", href))
        elif tag in _HEADING_TAGS:
            self._heading_level = int(tag[1])
            self._heading_parts = []
        elif tag == "a":
            href = a.get("href", "").strip()
            if href:
                self.links.append((href, a.get("rel", "").strip().lower()))
        elif tag == "img":
            src = a.get("src", "").strip() or a.get("data-src", "").strip()
            self.images.append(
                ImageInfo(
                    src=src,
                    alt=a["alt"] if "alt" in a else None,
                    width=a.get("width"),
                    height=a.get("height"),
                )
            )
            if src:
                self.resources.append(("img", src))
        elif tag == "script":
            if a.get("type", "").strip().lower() == "application/ld+json":
                self._in_ldjson = True
                self._ld_parts = []
            if a.get("src", "").strip():
                self.resources.append(("script", a["src"].strip()))
            self._skip_text += 1
        elif tag in _TEXT_SKIP_TAGS:
            self._skip_text += 1
        elif tag == "iframe" and a.get("src", "").strip():
            self.resources.append(("iframe", a["src"].strip()))
        elif tag == "source" and a.get("src", "").strip():
            self.resources.append(("source", a["src"].strip()))

    def _meta(self, a: Dict[str, str]) -> None:
        name = a.get("name", "").strip().lower()
        prop = a.get("property", "").strip().lower()
        content = a.get("content", "")
        if a.get("charset"):
            self.charset = a["charset"].strip()
        if a.get("http-equiv", "").strip().lower() == "content-type" and "charset=" in content.lower():
            self.charset = content.lower().split("charset=")[-1].strip()
        if name == "description" and self.meta_description is None:
            self.meta_description = content.strip()
        elif name == "robots" and self.meta_robots is None:
            self.meta_robots = content.strip()
        elif name == "viewport" and self.viewport is None:
            self.viewport = content.strip()
        if prop.startswith("og:"):
            self.og[prop] = content.strip()
        if name.startswith("twitter:"):
            self.twitter[name] = content.strip()

    def _close(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in _HEADING_TAGS and self._heading_level is not None:
            text = _WS.sub(" ", "".join(self._heading_parts)).strip()
            self.headings.append((self._heading_level, text))
            self._heading_level = None
            self._heading_parts = []
        elif tag == "script":
            if self._in_ldjson:
                self.jsonld_raw.append("".join(self._ld_parts))
                self._in_ldjson = False
            if self._skip_text > 0:
                self._skip_text -= 1
        elif tag in _TEXT_SKIP_TAGS and self._skip_text > 0:
            self._skip_text -= 1

    # -- HTMLParser hooks -------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        # e.g. <script src=.. /> — open then immediately close bookkeeping
        self._open(tag, attrs)
        if tag == "script":
            if self._in_ldjson:
                self.jsonld_raw.append("".join(self._ld_parts))
                self._in_ldjson = False
            if self._skip_text > 0:
                self._skip_text -= 1
        elif tag in _TEXT_SKIP_TAGS and self._skip_text > 0:
            self._skip_text -= 1

    def handle_endtag(self, tag):
        self._close(tag)

    def handle_data(self, data):
        if self._in_ldjson:
            self._ld_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._heading_level is not None:
            self._heading_parts.append(data)
        if self._skip_text == 0:
            self._text_parts.append(data)

    def text(self) -> str:
        return _WS.sub(" ", "".join(self._text_parts)).strip()


def parse_html(html: str) -> Dict[str, Any]:
    """Extract SEO-relevant signals from an HTML string.

    Returns a plain dict so the crawler can map fields onto a Page without a
    tight coupling to the parser internals.
    """
    p = _Extractor()
    try:
        p.feed(html)
        p.close()
    except Exception:
        # Malformed markup should degrade gracefully, never crash the crawl.
        pass

    title = _WS.sub(" ", "".join(p.title_parts)).strip() or None
    body_text = p.text()
    return {
        "title": title,
        "meta_description": p.meta_description,
        "meta_robots": p.meta_robots,
        "viewport": p.viewport,
        "canonical": p.canonical,
        "lang": p.lang,
        "charset": p.charset,
        "has_html_tag": p.has_html_tag,
        "headings": p.headings,
        "h1s": [t for lvl, t in p.headings if lvl == 1],
        "images": p.images,
        "links": p.links,
        "resources": p.resources,
        "jsonld_raw": p.jsonld_raw,
        "og": p.og,
        "twitter": p.twitter,
        "word_count": _word_count(body_text),
        "text": body_text,
    }


def _word_count(text: str) -> int:
    """Whitespace tokens for space-delimited languages; falls back to CJK
    character count so thin-content detection isn't fooled by Chinese/Japanese
    text that has no spaces."""
    if not text:
        return 0
    tokens = text.split()
    cjk = sum(1 for ch in text if "㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿")
    # A CJK "word" is ~1.5 chars; use whichever signal is larger.
    return max(len(tokens), int(cjk / 1.5))
