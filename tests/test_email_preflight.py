import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


P = Path(__file__).resolve().parents[1] / "scripts" / "email_preflight.py"
S = importlib.util.spec_from_file_location("email_preflight", P)
M = importlib.util.module_from_spec(S)
sys.modules["email_preflight"] = M
S.loader.exec_module(M)


class Tests(unittest.TestCase):
    @patch.object(M, "mx_records", return_value=["10 mail.example.com."])
    def test_valid_public_email_with_mx_passes(self, _):
        ok, reason, records = M.check_email("editor@publisher.org")
        self.assertTrue(ok)
        self.assertEqual(reason, "mx_observed")
        self.assertTrue(records)

    def test_placeholder_is_rejected(self):
        self.assertFalse(M.check_email("test@example.org")[0])

    @patch.object(M, "mx_records", return_value=[])
    @patch.object(M, "address_records", return_value=["192.0.2.1"])
    def test_address_fallback_passes_when_mx_is_not_observed(self, _, __):
        ok, reason, _ = M.check_email("editor@publisher.org")
        self.assertTrue(ok)
        self.assertEqual(reason, "mail_domain_a_fallback_observed")


if __name__ == "__main__":
    unittest.main()
