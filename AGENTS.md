# AGENTS.md — website-seo-audit

This repository is a self-contained **SEO audit tool** that also works as an
agent skill. If you are an AI coding agent (Codex, Claude Code, opencode, …) and
the user asks you to **audit / diagnose / check a website's SEO**, use this tool.

## Run it

```bash
python3 -m seo_audit <URL>
```

Run from the repository root so the `seo_audit` package is importable. Requires
Python 3.8+ and **no** third-party packages.

Common flags: `--single` (one page), `--max-pages N`, `--max-depth N`,
`--json`, `-o report.md`, `--ignore-robots` (for sites the user owns).

## Report back

1. Lead with the score/grade and the 🔴/🟡/🟢 counts.
2. Go through critical issues first, then warnings, then key notices — with the
   fix for each. Don't paste the whole raw report unless asked.
3. Offer to re-run after fixes or crawl deeper.

Full instructions and the check list are in [`SKILL.md`](SKILL.md).
