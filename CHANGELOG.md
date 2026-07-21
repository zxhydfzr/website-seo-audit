# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-14

### Added
- Initial public release.
- Dependency-free SEO auditor (Python standard library only) — runs as a CLI
  (`python3 -m seo_audit <url>` / `seo-audit`) and as an installable AI agent
  skill via `SKILL.md` (Claude Code, Codex, opencode).
- **On-page checks:** `<title>` presence/length/duplicates, meta description,
  `<h1>` and heading hierarchy, canonical tag, mobile viewport, `<html lang>`,
  image `alt` text, thin content (CJK-aware), Open Graph tags, mixed content on HTTPS.
- **Technical checks:** HTTPS, `robots.txt`, `sitemap.xml`, broken internal links
  (4xx/5xx), duplicate titles/meta, near-orphan pages, redirect handling.
- **Structured-data checks:** JSON-LD syntax validation, `@type` presence, required
  Schema.org fields (Article, Product, Organization, BreadcrumbList, FAQ, Recipe,
  Event, …), ISO-8601 date validation.
- Graded report (A–F scoring with per-severity caps), Markdown and `--json` output,
  and a non-zero exit code on critical issues for CI gating.
- Politeness by default: respects `robots.txt`, sends a real User-Agent, and
  rate-limits itself.
- Published to PyPI: `pip install website-seo-audit`.

### Notes
- Roadmap: page-speed / Core Web Vitals signals, hreflang & i18n checks, HTML report
  export, and optional sitemap-seeded crawling.

[1.0.0]: https://github.com/zxhydfzr/website-seo-audit/releases/tag/v1.0.0
