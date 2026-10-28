import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pipeline.py"
SPEC = importlib.util.spec_from_file_location("pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
sys.modules["pipeline"] = pipeline
SPEC.loader.exec_module(pipeline)

EMPTY_QUALITY_CHECKS = {
    "traffic_source": "unavailable",
    "index_status": "not_checked",
    "dominant_link_attribute": "not_observed",
    "sample_size": 0,
    "sample_urls": [],
}


class PipelineTests(unittest.TestCase):
    def test_parse_price(self):
        self.assertEqual(pipeline.parse_price(50), 50)
        self.assertEqual(pipeline.parse_price("$70 advance"), 70)
        self.assertEqual(pipeline.parse_price("150$"), 150)
        self.assertIsNone(pipeline.parse_price(""))

    def test_normalize_domain(self):
        self.assertEqual(pipeline.normalize_domain("https://WWW.Example.com/"), "example.com")
        self.assertEqual(pipeline.normalize_domain("example.com（流量下滑）"), "example.com")

    def test_missing_components_are_rescaled(self):
        score, confidence, coverage = pipeline.weighted_score(
            {"topical_relevance": 5, "editorial_quality": 4}, pipeline.SEO_WEIGHTS
        )
        self.assertEqual(score, 95)
        self.assertEqual(confidence, "low")
        self.assertEqual(coverage, 40)

    def test_prior_purchase_is_flagged_not_excluded(self):
        campaign = {
            "campaign_name": "test",
            "target_site": "https://target.example",
            "target_markets": ["US"],
            "languages": ["English"],
            "target_price_usd": 100,
            "max_price_usd": 150,
            "focus": "balanced",
        }
        components_seo = {key: 4 for key in pipeline.SEO_WEIGHTS}
        components_geo = {key: 4 for key in pipeline.GEO_WEIGHTS}
        candidate = {
            "domain": "example.com",
            "site_name": "Example",
            "country_region": "US",
            "language": "English",
            "industry": "Construction",
            "pool": "editorial",
            "discovery_method": "search",
            "discovery_query": "construction magazine",
            "evidence_url": "https://example.com/new-page",
            "relevance_reason": "Relevant construction coverage.",
            "cooperation_evidence": "No public cooperation page found.",
            "seo_components": components_seo,
            "geo_components": components_geo,
            "quality_checks": dict(EMPTY_QUALITY_CHECKS),
            "risk_flags": [],
            "hard_exclude_reason": "",
            "last_verified": "2026-08-24",
        }
        history = [{"domain": "https://www.example.com/", "price_usd": 120, "placement_url": "https://example.com/old-page"}]
        result = pipeline.process(campaign, [candidate], history, 30)
        self.assertEqual(len(result["shortlist"]), 1)
        self.assertTrue(result["shortlist"][0]["purchased_before"])
        self.assertEqual(result["shortlist"][0]["price_basis"], "same_domain_history")

    def test_exact_historical_page_is_excluded(self):
        campaign = {
            "campaign_name": "test",
            "target_site": "https://target.example",
            "target_markets": ["US"],
            "languages": ["English"],
            "target_price_usd": 100,
            "max_price_usd": 150,
            "focus": "balanced",
        }
        candidate = {
            "domain": "example.com",
            "site_name": "Example",
            "country_region": "US",
            "language": "English",
            "industry": "Construction",
            "pool": "editorial",
            "discovery_method": "search",
            "discovery_query": "construction magazine",
            "evidence_url": "https://www.example.com/page/",
            "relevance_reason": "Relevant.",
            "cooperation_evidence": "Unknown.",
            "seo_components": {key: 3 for key in pipeline.SEO_WEIGHTS},
            "geo_components": {key: 3 for key in pipeline.GEO_WEIGHTS},
            "quality_checks": dict(EMPTY_QUALITY_CHECKS),
            "risk_flags": [],
            "hard_exclude_reason": "",
            "last_verified": "2026-08-24",
        }
        history = [{"domain": "example.com", "price_usd": 100, "placement_url": "https://example.com/page"}]
        result = pipeline.process(campaign, [candidate], history, 30)
        self.assertEqual(result["shortlist"], [])
        self.assertEqual(result["excluded"][0]["exclusion_reason"], "exact historical placement URL")


if __name__ == "__main__":
    unittest.main()
