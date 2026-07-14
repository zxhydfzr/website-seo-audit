"""The SEO rule set: on-page checks (per page) and technical checks (site-wide).

Thresholds follow widely-used SEO guidance (Google documentation and the
open-source auditors python-seo-analyzer and seonaut). Each finding is an Issue
with a severity, a plain-language message, and a concrete fix.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlparse

from . import structured_data
from .model import CRITICAL, NOTICE, WARNING, Issue, Page, Report

# On-page thresholds
TITLE_MIN, TITLE_MAX = 30, 60
META_MIN, META_MAX = 70, 160
THIN_WORDS = 300
ALT_MAX = 100
BIG_PAGE_BYTES = 3 * 1024 * 1024


# ---------------------------------------------------------------------------
# Per-page checks
# ---------------------------------------------------------------------------

def check_page(page: Page) -> List[Issue]:
    issues: List[Issue] = []
    if not (page.is_html and page.ok):
        return issues  # transport-level problems are reported site-wide

    u = page.url

    # noindex — the page won't appear in search at all
    if page.meta_robots and "noindex" in page.meta_robots.lower():
        issues.append(Issue(
            WARNING, "noindex",
            "This page is set to noindex — search engines will not list it.",
            fix="Remove noindex from the meta robots tag if this page should rank.",
            url=u, detail=page.meta_robots,
        ))

    # Title
    if not page.title:
        issues.append(Issue(
            WARNING, "title_missing",
            "Page has no <title> — the single most important on-page SEO tag.",
            fix="Add a unique, descriptive <title> of about 50–60 characters.",
            url=u,
        ))
    else:
        n = len(page.title)
        if n < TITLE_MIN:
            issues.append(Issue(
                NOTICE, "title_short",
                f"Title is short ({n} chars) — you're leaving room unused.",
                fix=f"Aim for {TITLE_MIN}–{TITLE_MAX} characters with your key phrase near the front.",
                url=u, detail=repr(page.title),
            ))
        elif n > TITLE_MAX:
            issues.append(Issue(
                NOTICE, "title_long",
                f"Title is long ({n} chars) and may get truncated in results.",
                fix=f"Trim toward {TITLE_MAX} characters so it isn't cut off.",
                url=u, detail=repr(page.title),
            ))

    # Meta description
    if not page.meta_description:
        issues.append(Issue(
            WARNING, "meta_desc_missing",
            "No meta description — you lose control of the search-result snippet.",
            fix="Add a compelling 120–160 character meta description.",
            url=u,
        ))
    else:
        n = len(page.meta_description)
        if n < META_MIN:
            issues.append(Issue(
                NOTICE, "meta_desc_short",
                f"Meta description is short ({n} chars).",
                fix="Expand toward 120–160 characters to fill the snippet.",
                url=u,
            ))
        elif n > META_MAX:
            issues.append(Issue(
                NOTICE, "meta_desc_long",
                f"Meta description is long ({n} chars) and will be truncated.",
                fix=f"Keep it under {META_MAX} characters.",
                url=u,
            ))

    # H1
    if len(page.h1s) == 0:
        issues.append(Issue(
            WARNING, "h1_missing",
            "Page has no <h1> heading.",
            fix="Add exactly one <h1> that states the page's main topic.",
            url=u,
        ))
    elif len(page.h1s) > 1:
        issues.append(Issue(
            NOTICE, "h1_multiple",
            f"Page has {len(page.h1s)} <h1> headings; one primary H1 is clearest.",
            fix="Keep a single <h1>; demote the others to <h2>/<h3>.",
            url=u,
        ))

    # Heading hierarchy — skipped levels
    levels = [lvl for lvl, _ in page.headings]
    if levels:
        prev = levels[0]
        for lvl in levels[1:]:
            if lvl > prev + 1:
                issues.append(Issue(
                    NOTICE, "heading_skip",
                    f"Heading levels skip (H{prev} → H{lvl}), which breaks document structure.",
                    fix="Don't jump heading levels; go H2 → H3 → H4 in order.",
                    url=u,
                ))
                break
            prev = lvl

    # Canonical
    if not page.canonical:
        issues.append(Issue(
            NOTICE, "canonical_missing",
            "No canonical tag — duplicate/parameter URLs may split ranking signals.",
            fix='Add <link rel="canonical" href="..."> pointing to the preferred URL.',
            url=u,
        ))
    else:
        chost = urlparse(page.canonical).hostname
        phost = urlparse(page.final_url or page.url).hostname
        if chost and phost and chost.replace("www.", "") != phost.replace("www.", ""):
            issues.append(Issue(
                WARNING, "canonical_offsite",
                "Canonical URL points to a different domain — this de-indexes the page in favor of another site.",
                fix="Point the canonical at this site unless you truly intend to defer to another domain.",
                url=u, detail=page.canonical,
            ))

    # Viewport (mobile-friendliness — Google indexes mobile-first)
    if not page.viewport:
        issues.append(Issue(
            WARNING, "viewport_missing",
            "No viewport meta tag — the page may not be mobile-friendly.",
            fix='Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
            url=u,
        ))

    # html lang
    if not page.lang:
        issues.append(Issue(
            NOTICE, "lang_missing",
            "The <html> tag has no lang attribute.",
            fix='Set the page language, e.g. <html lang="en">.',
            url=u,
        ))

    # Images — alt text
    missing_alt = [img for img in page.images if img.alt is None or img.alt.strip() == ""]
    long_alt = [img for img in page.images if img.alt and len(img.alt) > ALT_MAX]
    if missing_alt:
        issues.append(Issue(
            WARNING, "img_alt_missing",
            f"{len(missing_alt)} of {len(page.images)} images have no alt text.",
            fix="Add descriptive alt text to every content image (empty alt only for decorative ones).",
            url=u, detail="; ".join(i.src[:60] for i in missing_alt[:5]),
        ))
    if long_alt:
        issues.append(Issue(
            NOTICE, "img_alt_long",
            f"{len(long_alt)} image(s) have alt text over {ALT_MAX} characters.",
            fix="Keep alt text concise; long alt reads like keyword stuffing.",
            url=u,
        ))

    # Thin content
    if 0 < page.word_count < THIN_WORDS:
        issues.append(Issue(
            NOTICE, "thin_content",
            f"Low word count (~{page.word_count} words) may read as thin content.",
            fix="Add substantive, useful content; avoid padding just to hit a number.",
            url=u,
        ))

    # Open Graph (social sharing previews)
    if not page.og.get("og:title") and not page.og.get("og:image"):
        issues.append(Issue(
            NOTICE, "og_missing",
            "No Open Graph tags — shared links won't show a rich preview.",
            fix="Add og:title, og:description and og:image for social sharing.",
            url=u,
        ))

    # Mixed content on HTTPS
    if page.mixed_content:
        issues.append(Issue(
            WARNING, "mixed_content",
            f"HTTPS page loads {len(page.mixed_content)} resource(s) over insecure HTTP.",
            fix="Serve every image/script/style over HTTPS to avoid mixed-content blocking.",
            url=u, detail="; ".join(page.mixed_content[:5]),
        ))

    # Oversized HTML
    if page.transfer_bytes > BIG_PAGE_BYTES:
        issues.append(Issue(
            NOTICE, "page_heavy",
            f"HTML transfer is large (~{page.transfer_bytes // 1024} KB), which slows loading.",
            fix="Reduce inline scripts/markup; enable compression and code-splitting.",
            url=u,
        ))

    # Structured data
    issues.extend(structured_data.validate_page(page))
    return issues


# ---------------------------------------------------------------------------
# Site-wide checks
# ---------------------------------------------------------------------------

def check_site(report: Report, link_status: Dict[str, Optional[int]]) -> List[Issue]:
    issues: List[Issue] = []
    pages = report.pages
    html_ok = [p for p in pages if p.is_html and p.ok]

    # HTTPS
    home = pages[0] if pages else None
    if home and urlparse(home.final_url or home.url).scheme == "http":
        issues.append(Issue(
            CRITICAL, "no_https",
            "The site is served over HTTP, not HTTPS.",
            fix="Install a TLS certificate and redirect all HTTP traffic to HTTPS.",
            url=None,
        ))

    # robots.txt
    r = report.robots
    if not r.get("exists"):
        issues.append(Issue(
            NOTICE, "robots_missing",
            "No robots.txt found.",
            fix="Add a robots.txt (even a permissive one) and reference your sitemap in it.",
            url=None,
        ))
    else:
        if r.get("blocks_all"):
            issues.append(Issue(
                CRITICAL, "robots_blocks_all",
                "robots.txt disallows all crawlers (Disallow: /) — the whole site is blocked from search.",
                fix="Remove the blanket Disallow: / unless the site is meant to be hidden.",
                url=None,
            ))
        if not r.get("sitemaps"):
            issues.append(Issue(
                NOTICE, "robots_no_sitemap",
                "robots.txt does not declare a Sitemap.",
                fix="Add a 'Sitemap: https://.../sitemap.xml' line to robots.txt.",
                url=None,
            ))

    # sitemap.xml
    s = report.sitemap
    if not s.get("exists"):
        issues.append(Issue(
            WARNING, "sitemap_missing",
            "No sitemap.xml found.",
            fix="Generate an XML sitemap and submit it in Google Search Console.",
            url=None,
        ))
    elif not s.get("valid"):
        issues.append(Issue(
            WARNING, "sitemap_invalid",
            "sitemap.xml exists but doesn't look like a valid <urlset>/<sitemapindex>.",
            fix="Fix the sitemap XML so search engines can parse it.",
            url=None, detail=s.get("url") or "",
        ))

    # Duplicate titles / meta descriptions
    issues += _dupes(html_ok, "title", "title", "Duplicate <title>",
                     "Give each page a unique title so they don't compete.")
    issues += _dupes(html_ok, "meta_description", "meta", "Duplicate meta description",
                     "Write a unique meta description per page.")

    # Broken internal links
    issues += _broken_links(pages, link_status)

    # Low-inlink / near-orphan pages
    issues += _low_inlinks(html_ok, report.start_url)

    # Structured-data coverage
    no_sd = [p for p in html_ok if not p.jsonld]
    if html_ok and len(no_sd) >= max(2, int(len(html_ok) * 0.6)):
        issues.append(Issue(
            NOTICE, "structured_data_coverage",
            f"{len(no_sd)} of {len(html_ok)} crawled pages have no structured data (JSON-LD).",
            fix="Add Schema.org JSON-LD (Article, Product, Organization, BreadcrumbList) to help search and AI engines understand and cite your pages.",
            url=None,
        ))

    return issues


def _dupes(pages: List[Page], attr: str, code_suffix: str, title: str, fix: str) -> List[Issue]:
    groups: Dict[str, List[str]] = {}
    for p in pages:
        val = getattr(p, attr)
        if val:
            groups.setdefault(val.strip(), []).append(p.url)
    out: List[Issue] = []
    for val, urls in groups.items():
        if len(urls) > 1:
            out.append(Issue(
                WARNING, f"dup_{code_suffix}",
                f"{title} used on {len(urls)} pages.",
                fix=fix,
                url=None,
                detail=f"“{val[:60]}” → " + ", ".join(urls[:4]) + (" …" if len(urls) > 4 else ""),
            ))
    return out


def _broken_links(pages: List[Page], link_status: Dict[str, Optional[int]]) -> List[Issue]:
    # Which pages point at each target?
    sources: Dict[str, List[str]] = {}
    for p in pages:
        for link in p.internal_links:
            sources.setdefault(link, []).append(p.url)

    out: List[Issue] = []
    for target, status in link_status.items():
        if status is not None and status >= 400:
            srcs = sources.get(target, [])
            out.append(Issue(
                CRITICAL, "broken_link",
                f"Internal link returns HTTP {status}: {target}",
                fix="Fix or remove the link, or restore the target page (add a redirect if it moved).",
                url=srcs[0] if srcs else None,
                detail=("linked from " + ", ".join(srcs[:3])) if srcs else "",
            ))
    return out


def _low_inlinks(pages: List[Page], start_url: str) -> List[Issue]:
    inlinks: Dict[str, int] = {p.url: 0 for p in pages}
    urlset = set(inlinks)
    for p in pages:
        for link in set(p.internal_links):
            if link in urlset and link != p.url:
                inlinks[link] += 1
    orphans = [u for u, c in inlinks.items() if c == 0 and u != start_url]
    if orphans:
        return [Issue(
            NOTICE, "low_inlinks",
            f"{len(orphans)} crawled page(s) have no internal links pointing to them.",
            fix="Link to important pages from related content so users and crawlers can reach them.",
            url=None,
            detail=", ".join(orphans[:5]),
        )]
    return []


# ---------------------------------------------------------------------------
# Orchestration + scoring
# ---------------------------------------------------------------------------

def run_checks(report: Report, link_status: Dict[str, Optional[int]]) -> None:
    for p in report.pages:
        for issue in check_page(p):
            report.add(issue)
    for issue in check_site(report, link_status):
        report.add(issue)

    _score(report)
    # stable, useful ordering: severity, then whether it's site-wide, then code
    from .model import SEVERITY_ORDER
    report.issues.sort(key=lambda i: (SEVERITY_ORDER.get(i.severity, 9), i.url or "", i.code))


def _score(report: Report) -> None:
    c = report.counts()
    crit = min(55, c[CRITICAL] * 15)
    warn = min(35, c[WARNING] * 3)
    notice = min(12, c[NOTICE] * 1)
    report.score = max(0, 100 - crit - warn - notice)


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 55:
        return "D"
    return "F"
