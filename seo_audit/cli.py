"""Command-line entry point.

    python -m seo_audit https://example.com
"""

from __future__ import annotations

import argparse
import datetime
import sys
from urllib.parse import urlparse

from . import __version__
from .checks import grade, run_checks
from .crawler import USER_AGENT, Crawler, load_sitemap, normalize, resolve_link_statuses
from .model import CRITICAL, Report
from .report import render_json, render_markdown


def _with_scheme(url: str) -> str:
    if not urlparse(url).scheme:
        return "https://" + url
    return url


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def audit(url: str, max_pages: int = 50, max_depth: int = 3, timeout: float = 15.0,
          delay: float = 0.3, respect_robots: bool = True, check_links: bool = True,
          link_limit: int = 300, user_agent: str = USER_AGENT, progress=None,
          link_progress=None) -> Report:
    """Crawl and evaluate a site, returning a fully-populated Report."""
    start = normalize(_with_scheme(url))
    report = Report(start_url=start)
    parsed = urlparse(start)
    report.site_url = f"{parsed.scheme}://{parsed.netloc}"
    report.started_at = _now()

    crawler = Crawler(
        start, max_pages=max_pages, max_depth=max_depth, timeout=timeout, delay=delay,
        user_agent=user_agent, respect_robots=respect_robots, on_progress=progress,
    )
    pages, robots_info, _rp = crawler.crawl()
    report.pages = pages
    report.robots = robots_info
    report.sitemap = load_sitemap(report.site_url, robots_info, timeout, user_agent)

    links_total = links_checked = 0
    if check_links:
        statuses, links_total, links_checked = resolve_link_statuses(
            pages, timeout, user_agent, limit=link_limit, delay=min(delay, 0.15),
            on_progress=link_progress,
        )
    else:
        statuses = {p.url: p.status_code for p in pages}

    run_checks(report, statuses)
    report.finished_at = _now()
    report.stats = {
        "pages_crawled": len(pages),
        "internal_links_found": links_total,
        "links_checked": links_checked,
        "robots_txt": bool(robots_info.get("exists")),
        "sitemap": bool(report.sitemap.get("exists")),
    }
    return report


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seo-audit",
        description="网站SEO诊断 — crawl any website and report on-page, technical, "
                    "and structured-data SEO issues. No API keys required.",
    )
    p.add_argument("url", help="Website URL to audit (scheme optional, defaults to https).")
    p.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl (default: 50).")
    p.add_argument("--max-depth", type=int, default=3, help="Max crawl depth from the start URL (default: 3).")
    p.add_argument("-1", "--single", action="store_true", help="Audit only the given URL (no crawl).")
    p.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds (default: 15).")
    p.add_argument("--delay", type=float, default=0.3, help="Politeness delay between requests (default: 0.3s).")
    p.add_argument("--no-link-check", action="store_true", help="Skip broken-internal-link detection.")
    p.add_argument("--link-limit", type=int, default=300, help="Max extra link URLs to status-check (default: 300).")
    p.add_argument("--ignore-robots", action="store_true", help="Crawl even if robots.txt disallows (use on your own site).")
    p.add_argument("--json", action="store_true", help="Output JSON instead of Markdown.")
    p.add_argument("-o", "--output", help="Write report to a file instead of stdout.")
    p.add_argument("--user-agent", default=USER_AGENT, help="Override the crawler User-Agent.")
    p.add_argument("-q", "--quiet", action="store_true", help="Suppress crawl progress on stderr.")
    p.add_argument("--version", action="version", version=f"website-seo-audit {__version__}")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    max_pages = 1 if args.single else args.max_pages
    max_depth = 0 if args.single else args.max_depth

    def progress(i, total, url):
        if not args.quiet:
            sys.stderr.write(f"\r[{i}/{total}] crawling {url[:70]:<70}")
            sys.stderr.flush()

    def link_progress(i, total, url):
        if not args.quiet:
            sys.stderr.write(f"\r[{i}/{total}] checking links {url[:64]:<64}")
            sys.stderr.flush()

    try:
        report = audit(
            args.url, max_pages=max_pages, max_depth=max_depth, timeout=args.timeout,
            delay=args.delay, respect_robots=not args.ignore_robots,
            check_links=not args.no_link_check, link_limit=args.link_limit,
            user_agent=args.user_agent, progress=progress, link_progress=link_progress,
        )
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        return 130

    if not args.quiet:
        sys.stderr.write("\r" + " " * 90 + "\r")
        sys.stderr.flush()

    out = render_json(report) if args.json else render_markdown(report)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        sys.stderr.write(
            f"Report written to {args.output} — score {report.score}/100 ({grade(report.score)})\n"
        )
    else:
        print(out)

    # Non-zero exit if any critical issue, so CI pipelines can gate on it.
    return 1 if report.counts()[CRITICAL] else 0


if __name__ == "__main__":
    raise SystemExit(main())
