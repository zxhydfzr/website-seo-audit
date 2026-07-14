"""Offline tests — no network, deterministic. Run with:

    python -m unittest discover -s tests

They feed synthetic HTML through the parser and checks so the rule set can't
silently regress.
"""

import unittest

from seo_audit.crawler import Crawler, normalize, same_site
from seo_audit.htmlparse import parse_html
from seo_audit.model import Page
from seo_audit import checks, structured_data


GOOD_HTML = """<!doctype html><html lang="en"><head>
<title>A Perfectly Reasonable Title of About Forty Chars</title>
<meta name="description" content="A meta description that sits comfortably in the sweet spot of roughly one hundred and forty well-chosen characters overall.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://good.example/page">
<meta property="og:title" content="A"><meta property="og:image" content="https://good.example/o.png">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Article","headline":"H","image":"https://good.example/i.jpg","datePublished":"2024-01-31","author":{"@type":"Person","name":"Jane"}}
</script>
</head><body><h1>Only One H1</h1><h2>Sub</h2>
<p>%s</p>
<img src="/a.jpg" alt="described">
</body></html>""" % ("word " * 400)


class ParserTests(unittest.TestCase):
    def test_extracts_core_fields(self):
        d = parse_html(GOOD_HTML)
        self.assertEqual(d["h1s"], ["Only One H1"])
        self.assertEqual(d["lang"], "en")
        self.assertTrue(d["canonical"].endswith("/page"))
        self.assertEqual(len(d["jsonld_raw"]), 1)
        self.assertGreater(d["word_count"], 300)

    def test_missing_alt_is_none(self):
        d = parse_html('<img src="/x.jpg"><img src="/y.jpg" alt="ok">')
        self.assertIsNone(d["images"][0].alt)
        self.assertEqual(d["images"][1].alt, "ok")

    def test_cjk_word_count(self):
        d = parse_html("<p>" + "中文内容测试" * 20 + "</p>")
        self.assertGreater(d["word_count"], 30)


class CheckTests(unittest.TestCase):
    def _page(self, html, url="https://mysite.com/p"):
        p = Page(url=url, status_code=200, final_url=url, content_type="text/html", is_html=True)
        Crawler("https://mysite.com")._parse_onto(p, html)
        return p

    def test_clean_page_has_no_issues(self):
        p = self._page(GOOD_HTML, url="https://good.example/page")
        p.final_url = "https://good.example/page"
        codes = {i.code for i in checks.check_page(p)}
        self.assertEqual(codes, set(), f"unexpected issues: {codes}")

    def test_detects_common_problems(self):
        html = ('<html><head><title>x</title></head><body>'
                '<img src="/a.jpg"><a href="/in">i</a></body></html>')
        p = self._page(html)
        codes = {i.code for i in checks.check_page(p)}
        for expected in ("title_short", "meta_desc_missing", "h1_missing",
                         "viewport_missing", "canonical_missing", "img_alt_missing",
                         "lang_missing", "og_missing"):
            self.assertIn(expected, codes)

    def test_invalid_jsonld_flagged(self):
        p = self._page('<html><body><script type="application/ld+json">{bad}</script></body></html>')
        codes = {i.code for i in structured_data.validate_page(p)}
        self.assertIn("jsonld_invalid", codes)

    def test_missing_schema_fields_flagged(self):
        html = ('<html><body><script type="application/ld+json">'
                '{"@type":"Product","name":"Thing"}</script></body></html>')
        p = self._page(html)
        issues = structured_data.validate_page(p)
        self.assertTrue(any(i.code == "jsonld_missing_fields" for i in issues))


class UrlTests(unittest.TestCase):
    def test_normalize_drops_fragment_and_default_port(self):
        self.assertEqual(normalize("HTTP://Example.com:80/a#frag"), "http://example.com/a")

    def test_same_site_treats_www_as_apex(self):
        self.assertTrue(same_site("https://www.example.com/a", "https://example.com/"))
        self.assertFalse(same_site("https://other.com/a", "https://example.com/"))


if __name__ == "__main__":
    unittest.main()
