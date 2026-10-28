import importlib.util
import sys
import unittest
from pathlib import Path


P = Path(__file__).resolve().parents[1] / "scripts" / "rolling_campaign.py"
S = importlib.util.spec_from_file_location("rolling_campaign", P)
M = importlib.util.module_from_spec(S)
sys.modules["rolling_campaign"] = M
S.loader.exec_module(M)


class Tests(unittest.TestCase):
    def test_ready_definition_respects_budget_and_free_routes(self):
        self.assertTrue(M.is_handoff_ready({"status":"quoted","quote":{"amount_max":120},"risk_flags":[]},155)[0])
        self.assertFalse(M.is_handoff_ready({"status":"quoted","quote":{"amount_max":1000},"risk_flags":[]},155)[0])
        self.assertTrue(M.is_handoff_ready({"status":"replied","quote":None,"placement_terms":{"price_status":"free_editorial_route"},"risk_flags":[]},155)[0])
        self.assertFalse(M.is_handoff_ready({"status":"replied","quote":None,"placement_terms":{},"risk_flags":[]},155)[0])


if __name__ == "__main__":
    unittest.main()
