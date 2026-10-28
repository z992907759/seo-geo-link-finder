import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "site_checks.py"
SPEC = importlib.util.spec_from_file_location("site_checks", MODULE_PATH)
site_checks = importlib.util.module_from_spec(SPEC)
sys.modules["site_checks"] = site_checks
SPEC.loader.exec_module(site_checks)


class SiteChecksTests(unittest.TestCase):
    def test_link_attributes_and_indexability(self):
        html = """
        <html><head><link rel="canonical" href="https://example.com/post"></head><body>
        <a href="https://outside.example/a">follow</a>
        <a href="https://outside.example/b" rel="nofollow">nofollow</a>
        <a href="https://outside.example/c" rel="nofollow sponsored">sponsored</a>
        <a href="https://outside.example/d" rel="ugc nofollow">ugc</a>
        <a href="/internal">internal</a>
        </body></html>
        """
        result = site_checks.inspect_html(html, "https://example.com/post")
        self.assertTrue(result["technically_indexable"])
        self.assertEqual(result["follow_count"], 1)
        self.assertEqual(result["nofollow_count"], 1)
        self.assertEqual(result["sponsored_count"], 1)
        self.assertEqual(result["ugc_count"], 1)

    def test_noindex_is_blocked(self):
        result = site_checks.inspect_html(
            '<meta name="robots" content="noindex,follow">',
            "https://example.com/post",
        )
        self.assertFalse(result["technically_indexable"])

    def test_insufficient_sample_status(self):
        samples = [{
            "url": "https://example.com/post",
            "technically_indexable": True,
            "search_observation": "indexed",
            "follow_count": 2,
            "nofollow_count": 0,
            "sponsored_count": 0,
            "ugc_count": 0,
        }]
        result = site_checks.aggregate_check("example.com", {"traffic_source": "unavailable"}, samples, "2026-08-24")
        self.assertEqual(result["index_status"], "insufficient_samples")
        self.assertEqual(result["dominant_link_attribute"], "follow")
        self.assertEqual(result["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
