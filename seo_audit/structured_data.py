"""JSON-LD structured-data validation.

This is the part most crawl-based SEO tools skip. Search engines and AI answer
engines increasingly rely on Schema.org markup to understand and cite pages, so
we validate JSON-LD syntax and check that common types carry the fields Google
needs for rich results.
"""

from __future__ import annotations

import re
from typing import Any, List

from .model import NOTICE, WARNING, Issue, Page

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?([.+\-Z0-9:]*)?$")

# Recommended fields per Schema.org type (Google rich-result guidance, trimmed
# to the fields whose absence most often blocks eligibility).
REQUIRED = {
    "Article": ["headline", "image", "datePublished", "author"],
    "BlogPosting": ["headline", "image", "datePublished", "author"],
    "NewsArticle": ["headline", "image", "datePublished", "author"],
    "Product": ["name", "image", "offers"],
    "Organization": ["name", "url"],
    "BreadcrumbList": ["itemListElement"],
    "FAQPage": ["mainEntity"],
    "Recipe": ["name", "image", "recipeIngredient", "recipeInstructions"],
    "Event": ["name", "startDate", "location"],
    "LocalBusiness": ["name", "address"],
    "VideoObject": ["name", "thumbnailUrl", "uploadDate"],
    "HowTo": ["name", "step"],
}
_DATE_FIELDS = ("datePublished", "dateModified", "startDate", "endDate", "uploadDate")


def _entities(data: Any) -> List[dict]:
    """Flatten a JSON-LD payload (which may be a dict, a list, or use @graph)
    into the list of typed entity objects it contains."""
    out: List[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            if isinstance(node.get("@graph"), list):
                for n in node["@graph"]:
                    walk(n)
            if "@type" in node:
                out.append(node)

    walk(data)
    return out


def _has(entity: dict, field: str) -> bool:
    v = entity.get(field)
    if v is None:
        return False
    if isinstance(v, (list, dict, str)) and len(v) == 0:
        return False
    return True


def validate_page(page: Page) -> List[Issue]:
    """Return issues for the JSON-LD found on one page (empty if the markup is
    clean; page-with-no-markup is judged at the site level, not here)."""
    issues: List[Issue] = []
    for block in page.jsonld:
        if block.parse_error:
            issues.append(Issue(
                WARNING, "jsonld_invalid",
                "A structured-data (JSON-LD) block is not valid JSON, so search engines ignore it.",
                fix='Fix the JSON syntax inside the <script type="application/ld+json"> block.',
                url=page.url, detail=block.parse_error[:160],
            ))
            continue

        ents = _entities(block.data)
        if not ents:
            issues.append(Issue(
                WARNING, "jsonld_no_type",
                "A JSON-LD block has no @type, so search engines can't interpret it.",
                fix="Add an @type such as Article, Product, or Organization to the JSON-LD object.",
                url=page.url,
            ))
            continue

        for ent in ents:
            types = ent.get("@type")
            types = types if isinstance(types, list) else [types]
            for t in types:
                if t in REQUIRED:
                    missing = [f for f in REQUIRED[t] if not _has(ent, f)]
                    if missing:
                        issues.append(Issue(
                            WARNING, "jsonld_missing_fields",
                            f"{t} markup is missing recommended field(s): {', '.join(missing)}.",
                            fix=f"Add {', '.join(missing)} to the {t} JSON-LD to qualify for rich results.",
                            url=page.url, detail=f"@type={t}",
                        ))
            for df in _DATE_FIELDS:
                val = ent.get(df)
                if isinstance(val, str) and val and not _ISO_DATE.match(val.strip()):
                    issues.append(Issue(
                        NOTICE, "jsonld_date_format",
                        f"{df} in structured data is not an ISO-8601 date.",
                        fix=f"Use ISO-8601 for {df}, e.g. 2024-01-31 or 2024-01-31T09:00:00+00:00.",
                        url=page.url, detail=f"{df}={val[:40]}",
                    ))
    return issues
