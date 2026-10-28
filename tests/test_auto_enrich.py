import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "auto_enrich.py"
SCRIPT_DIR = str(MODULE_PATH.parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
SPEC = importlib.util.spec_from_file_location("auto_enrich", MODULE_PATH)
auto_enrich = importlib.util.module_from_spec(SPEC)
sys.modules["auto_enrich"] = auto_enrich
SPEC.loader.exec_module(auto_enrich)


class AutoEnrichTests(unittest.TestCase):
    def test_article_filter(self):
        self.assertTrue(auto_enrich.is_article_url("https://example.com/2026/steel-warehouse-design-guide/", "example.com"))
        self.assertFalse(auto_enrich.is_article_url("https://example.com/about/", "example.com"))
        self.assertFalse(auto_enrich.is_article_url("https://other.com/2026/article/", "example.com"))

    def test_preferred_guest_pattern_ranks_first(self):
        guest = auto_enrich.rank_article_url("https://example.com/guest/steel-building-guide")
        regular = auto_enrich.rank_article_url("https://example.com/news/steel-building-guide")
        self.assertGreater(guest, regular)

    def test_non_article_utility_pages_are_rejected(self):
        self.assertFalse(auto_enrich.is_article_url("https://example.com/privacy-policy/", "example.com"))
        self.assertFalse(auto_enrich.is_article_url("https://example.com/account/login/", "example.com"))
        self.assertFalse(auto_enrich.is_article_url("https://example.com/newsletter/subscribe/", "example.com"))


if __name__ == "__main__":
    unittest.main()
