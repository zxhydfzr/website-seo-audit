<div align="center">

# 🔍 website-seo-audit

### Crawl any website and get a graded SEO report — in seconds, with zero setup.

**English** · [简体中文](README.zh-CN.md)

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#-why-its-different)
[![Agent Skill](https://img.shields.io/badge/agent-skill-8A2BE2.svg)](SKILL.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#-contributing)

</div>

A dependency-free SEO auditor you can run as a **command-line tool** _or_ install
as a **skill for your AI coding agent** (Claude Code, Codex, opencode, …). It
crawls a site, checks dozens of **on-page**, **technical**, and
**structured-data** signals, and hands you a scored report with a concrete fix
for every issue.

No API keys. No sign-up. No `pip install`. Just Python 3.8+ and the standard library.

```bash
python3 -m seo_audit https://example.com
```

---

## ✨ See it in action

```
# 🔍 SEO Audit — https://example.com
Score: 72/100 (C)  ·  🔴 2 critical · 🟡 8 warnings · 🟢 15 notices
Crawled 23 pages · 45 internal links checked

## 🔴 Critical (2)
### Broken internal links (3×)
Internal link returns HTTP 404: https://example.com/old-page
- Fix: Fix or remove the link, or restore the target page (add a redirect if it moved).

### Site not on HTTPS
- Fix: Install a TLS certificate and redirect all HTTP traffic to HTTPS.

## 🟡 Warnings (8)
### Missing meta description (6×)
### Duplicate titles
### Structured data missing fields — Article missing image, datePublished
...
```

👉 Full example: [`examples/sample-report.md`](examples/sample-report.md)

---

## 🚀 Quick start

```bash
git clone https://github.com/zxhydfzr/website-seo-audit.git
cd website-seo-audit
python3 -m seo_audit https://yoursite.com
```

That's it. No virtualenv, no packages to install.

Prefer a global command? Install with [pipx](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/zxhydfzr/website-seo-audit.git
seo-audit https://yoursite.com
```

---

## 🤖 Use it inside your AI agent

This repo ships a [`SKILL.md`](SKILL.md), so any agent that supports the open
[Agent Skills](https://code.claude.com/docs/en/skills) format can pick it up.
Then just say: **"audit the SEO of https://example.com"** and your agent runs the
tool and explains the results.

| Agent | Install |
|---|---|
| **Claude Code** | `git clone https://github.com/zxhydfzr/website-seo-audit ~/.claude/skills/website-seo-audit` |
| **Codex** | Clone into your project — the bundled [`AGENTS.md`](AGENTS.md) tells it how to run |
| **opencode / others** | Clone anywhere the agent can read files and point it at `SKILL.md` |

---

## 🔬 What it checks

<table>
<tr><td valign="top" width="33%">

**On-page**
- `<title>` — present / length / duplicate
- Meta description — present / length
- `<h1>` & heading hierarchy
- Canonical tag
- Mobile viewport
- `<html lang>`
- Image `alt` text
- Thin content (CJK-aware)
- Open Graph tags
- Mixed content on HTTPS

</td><td valign="top" width="33%">

**Technical**
- HTTPS
- `robots.txt`
- `sitemap.xml`
- Broken internal links (4xx/5xx)
- Duplicate titles / meta
- Near-orphan pages
- Redirect handling

</td><td valign="top" width="33%">

**Structured data** ⭐
- Valid JSON-LD syntax
- `@type` present
- Required Schema.org fields
  (Article, Product, Organization,
  BreadcrumbList, FAQ, Recipe,
  Event, …)
- ISO-8601 dates

</td></tr>
</table>

---

## ⭐ Why it's different

- **Structured-data aware.** Most quick SEO checkers stop at titles and headings.
  This one validates your **JSON-LD / Schema.org** markup — the signal search
  engines and **AI answer engines** use to understand and _cite_ your pages.
- **Zero dependencies.** Only the Python standard library, so it runs anywhere
  Python does — laptops, CI, containers, a locked-down server.
- **Agent-native.** Ships as a portable skill, so your AI assistant can run a full
  audit and walk you through the fixes conversationally.
- **Polite & safe.** Respects `robots.txt`, sends a real User-Agent, rate-limits
  itself, and only crawls the site you point it at.

---

## ⚙️ Options

| Option | Default | Meaning |
|---|---|---|
| `-1`, `--single` | off | Audit only the given URL (no crawl) |
| `--max-pages N` | 50 | Max pages to crawl |
| `--max-depth N` | 3 | Max crawl depth |
| `--json` | off | Machine-readable JSON output |
| `-o, --output FILE` | — | Write the report to a file |
| `--ignore-robots` | off | Crawl even if robots.txt disallows (your own sites) |
| `--no-link-check` | off | Skip broken-link detection (faster) |
| `-q, --quiet` | off | Suppress crawl progress |

The command exits non-zero when any **critical** issue is found, so you can gate CI:

```bash
seo-audit https://yoursite.com --json -o seo.json || echo "SEO regressions!"
```

## 📊 How the score works

Starts at 100 and deducts, with per-severity caps so a big site can't collapse on
notices alone: 🔴 −15 each · 🟡 −3 each · 🟢 −1 each.
Grades: **A** ≥90 · **B** ≥80 · **C** ≥70 · **D** ≥55 · **F** below.

## 🗺️ Roadmap

- [ ] Page-speed / Core Web Vitals signals
- [ ] hreflang & internationalization checks
- [ ] HTML report export
- [ ] Optional sitemap-seeded crawl (audit every listed URL)

Ideas and PRs welcome — see below.

## 🤝 Contributing

Issues and pull requests are very welcome. The codebase is small, typed, and
dependency-free by design; please keep it that way. Run the tests with:

```bash
python -m unittest discover -s tests
```

## 🙌 Credits

Check design informed by the open-source auditors
[python-seo-analyzer](https://github.com/sethblack/python-seo-analyzer) and
[seonaut](https://github.com/StJudeWasHere/seonaut), plus Google's rich-results
documentation. This project adds first-class structured-data validation and
zero-dependency, agent-installable packaging.

## 📄 License

[MIT](LICENSE) — free for personal and commercial use.

---

<div align="center">

**If this saved you time, a ⭐ helps others find it.**

Made for everyone who wants clean SEO without a dashboard login.

</div>
