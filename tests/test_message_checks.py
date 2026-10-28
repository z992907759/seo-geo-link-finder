import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "message_checks.py"
SPEC = importlib.util.spec_from_file_location("message_checks", MODULE_PATH)
checks = importlib.util.module_from_spec(SPEC)
sys.modules["message_checks"] = checks
SPEC.loader.exec_module(checks)


class MessageCheckTests(unittest.TestCase):
    def test_flags_client_url_and_ai_phrase(self):
        campaign = {"target_site": "https://client.example", "campaign_name": "Client campaign", "outreach": {"approved_signature": "Sample Sender", "sender_identity_confirmed": True}}
        messages = [{
            "domain": "publisher.com", "recipient": "editor@publisher.com", "subject": "Question",
            "body": "I hope this email finds you well. See https://client.example for more information. " * 3,
            "status": "ready_to_send", "recipient_fit": "high", "banned_phrase_check": "fail", "prohibited_disclosure_check": "fail",
        }]
        result = checks.validate_messages(campaign, messages)
        self.assertFalse(result["valid"])
        self.assertTrue(any("AI-style" in error for error in result["errors"]))
        self.assertTrue(any("disclosure" in error for error in result["errors"]))

    def test_clean_sector_only_copy(self):
        campaign = {"target_site": "https://client.example", "campaign_name": "Client campaign", "outreach": {"approved_signature": "Sample Sender", "sender_identity_confirmed": True}}
        messages = [{
            "domain": "publisher.com", "recipient": "editor@publisher.com", "subject": "Steel structure article",
            "body": "Hi editorial team, We work in steel structures and would like to ask whether you accept a practical article on large-span industrial buildings. The piece would focus on design decisions rather than promotion. If this is available, please send the current requirements, price, link policy, and normal publishing time. Thanks,\nSample Sender",
            "status": "ready_to_send", "recipient_fit": "high", "banned_phrase_check": "pass", "prohibited_disclosure_check": "pass", "signature_check": "pass",
        }]
        result = checks.validate_messages(campaign, messages)
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
