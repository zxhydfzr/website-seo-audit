---
name: website-seo-audit
description: >-
  Crawl any website and produce a graded SEO diagnosis — on-page (title, meta,
  headings, canonical, mobile viewport, image alt, thin content), technical
  (HTTPS, robots.txt, sitemap.xml, broken internal links, duplicate titles/meta,
  near-orphan pages), and structured data (JSON-LD / Schema.org validity and
  required fields). Zero config, no API keys, pure Python standard library. Use
  when the user wants to audit, diagnose, check, or review a website's SEO, find
  SEO problems, or asks "how is my site's SEO / 帮我诊断这个网站的SEO".
---

# Website SEO Audit （网站SEO诊断）

Diagnose any website's SEO by crawling it and checking dozens of on-page,
technical, and structured-data signals. No API keys, no setup, no third-party
packages — it runs on the Python standard library alone.

## When to use this skill

- The user asks to **audit / diagnose / check / review a website's SEO**.
- The user shares a URL and asks what's wrong with it for search.
- The user wants a before/after SEO comparison, or a report they can act on.

## How to run

From this skill's directory:

```bash
python3 -m seo_audit https://example.com
```

If you're calling it from another working directory, run it from the skill
folder (the package must be importable):

```bash
cd /path/to/website-seo-audit && python3 -m seo_audit https://example.com
```

Useful options:

| Option | Meaning |
|---|---|
| `-1`, `--single` | Audit only the given URL (no crawl) |
| `--max-pages N` | Max pages to crawl (default 50) |
| `--max-depth N` | Max crawl depth (default 3) |
| `--json` | Machine-readable JSON instead of Markdown |
| `-o FILE` | Write the report to a file |
| `--ignore-robots` | Crawl even if robots.txt disallows (use on sites you own) |
| `--no-link-check` | Skip broken-link detection (faster) |

The command prints a Markdown report to stdout and exits non-zero if any
**critical** issue was found (handy for CI).

## How to interpret and report back

1. Run the tool on the URL the user gave. Use the default crawl unless they only
   want a single page (`--single`) or a bigger sweep (`--max-pages`).
2. Read the Markdown report. **Lead with the score/grade and the issue counts.**
3. Walk through findings in order: 🔴 critical first, then 🟡 warnings, then the
   highest-value 🟢 notices. For each, state the problem and its concrete fix.
4. Offer next steps: re-run after fixes, crawl deeper, or export JSON.

Do not dump the whole raw report unless asked — summarize the score, the
critical/warning items, and what to fix first.

## What it checks

- **On-page:** title (presence/length/uniqueness), meta description, H1 &
  heading hierarchy, canonical, mobile viewport, `html lang`, image alt text,
  thin content, Open Graph, mixed content on HTTPS.
- **Technical:** HTTPS, robots.txt (missing / blocks-all / sitemap directive),
  sitemap.xml (presence/validity), broken internal links (HTTP 4xx/5xx),
  duplicate titles/meta across pages, pages with no internal links.
- **Structured data:** JSON-LD syntax validity and required Schema.org fields for
  Article, Product, Organization, BreadcrumbList, FAQ, Recipe, Event, and more —
  the signal most crawl-based tools ignore, and what AI answer engines read.

## Notes

- Requires **Python 3.8+**. No `pip install` needed.
- Respects `robots.txt` by default; pass `--ignore-robots` on your own sites.
- Stays on the same site (apex + `www`); external links are not followed.
