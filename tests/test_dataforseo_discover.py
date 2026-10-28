import importlib.util
import sys
import unittest
from pathlib import Path


P = Path(__file__).resolve().parents[1] / "scripts" / "dataforseo_discover.py"
S = importlib.util.spec_from_file_location("dataforseo_discover", P)
M = importlib.util.module_from_spec(S); sys.modules["dataforseo_discover"] = M; S.loader.exec_module(M)


class Tests(unittest.TestCase):
    def test_domain_normalization_and_exclusion(self):
        self.assertEqual(M.normalize_domain("https://www.Example.com/post"), "example.com")
        self.assertTrue(M.excluded("youtube.com", "target.com"))
        self.assertTrue(M.excluded("target.com", "target.com"))
        self.assertFalse(M.excluded("publisher.com", "target.com"))


if __name__ == "__main__": unittest.main()
