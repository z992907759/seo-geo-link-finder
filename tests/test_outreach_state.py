import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "outreach_state.py"
SPEC = importlib.util.spec_from_file_location("outreach_state", MODULE_PATH)
outreach = importlib.util.module_from_spec(SPEC)
sys.modules["outreach_state"] = outreach
SPEC.loader.exec_module(outreach)


class OutreachStateTests(unittest.TestCase):
    def setUp(self):
        self.campaign = {
            "campaign_name": "test",
            "target_site": "https://client.example",
            "outreach": {"daily_send_cap": 15, "follow_up_days": [5, 10], "max_follow_ups": 2, "monitoring_settings_confirmed": True},
        }
        self.shortlist = [{
            "domain": "publisher.com",
            "site_name": "Publisher",
            "contact_info": {
                "recommended_email": "editor@publisher.com",
                "source_urls": ["https://publisher.com/contact"],
            },
        }]

    def test_mailbox_must_match_and_have_capabilities(self):
        self.campaign["outreach"]["approved_sender_name"] = "Sample Sender"
        self.campaign["outreach"]["approved_signature"] = "Sample Sender"
        self.campaign["outreach"]["sender_identity_confirmed"] = True
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        with self.assertRaises(ValueError):
            outreach.confirm_mailbox(state, "other@example.com")
        outreach.confirm_mailbox(state, "sender@example.com", "2026-08-25T08:00:00+00:00")
        self.assertEqual(state["authorization"]["mode"], "automatic_outreach")
        self.assertTrue(state["authorization"]["initial_email"])

    def test_quote_extraction(self):
        quote = outreach.extract_quote("Our fee is $150 per article.")
        self.assertEqual(quote["amount_min"], 150)
        self.assertEqual(quote["amount_max"], 150)
        self.assertEqual(quote["currency"], "USD")
        self.assertEqual(outreach.classify_reply("The price is 80-120 EUR"), "quoted")
        self.assertEqual(outreach.classify_reply("You are welcome to submit articles for consideration. Attached are our editorial guidelines."), "replied")
        self.assertEqual(outreach.classify_reply("We've received your request and our team will review it."), "auto_reply")
        self.assertEqual(outreach.classify_reply("We do offer sponsored content on our magazine website."), "replied")
        self.assertEqual(outreach.classify_reply("You can find our contribution guidelines here."), "replied")
        self.assertEqual(outreach.classify_reply("We do not typically publish material like this."), "rejected")
        self.assertEqual(outreach.classify_reply("We're not in need of additional content right now."), "rejected")
        self.assertEqual(outreach.classify_reply("Please visit the Authors and Other Contributors section for contributor guidelines."), "replied")
        self.assertEqual(outreach.classify_reply("Delivery Status Notification (Delay): temporarily unable to deliver."), "auto_reply")
        self.assertEqual(outreach.classify_reply("There is no contributor fee and I'm happy to take a look."), "replied")
        self.assertEqual(outreach.classify_reply("I've attached our sponsored article rate sheet."), "replied")
        self.assertEqual(outreach.classify_reply("I can point you in the right direction for Sponsored Technical Content."), "replied")
        self.assertEqual(outreach.classify_reply("We do consider outside industry contributions. See our submission guidelines."), "replied")
        self.assertEqual(outreach.classify_reply("Contributions from industry are welcome and we would be happy to discuss publication requirements."), "replied")
        self.assertEqual(outreach.classify_reply("I handle sponsored article opportunities, with links where appropriate."), "replied")
        self.assertEqual(outreach.classify_reply("We have several options to reach our target group. Online articles are commonly used."), "replied")

    def test_placement_term_extraction(self):
        terms = outreach.extract_placement_terms(
            "We can publish a permanent sponsored article with a follow link in 5 business days."
        )
        self.assertEqual(terms["link_attribute"], "follow")
        self.assertEqual(terms["permanence"], "permanent")
        self.assertEqual(terms["turnaround"], "5 business days")
        referral = outreach.extract_placement_terms("Please contact Jane at sales@example.com for sponsorship opportunities.")
        self.assertEqual(referral["referral_email"], "sales@example.com")
        signature_only = outreach.extract_placement_terms("Thanks, Jane\nEmail: jane@example.com")
        self.assertNotIn("referral_email", signature_only)
        office_request = outreach.extract_placement_terms("Would you provide the office location where an order would originate?")
        self.assertNotIn("content_responsibility", office_request)
        self.assertEqual(office_request["required_fact"], "order_origin_office_location")
        self.assertEqual(office_request["next_action"], "awaiting_user_fact")
        limited = outreach.extract_placement_terms("The do-follow link is not permanent and remains for 1 year. Publishing takes 2-4 days. The article must be 1000+ words.")
        self.assertEqual(limited["permanence"], "not_permanent")
        self.assertEqual(limited["placement_duration"], "1 year")
        self.assertEqual(limited["turnaround"], "2-4 days")
        self.assertEqual(limited["min_words"], 1000)
        identity = outreach.extract_placement_terms("Please share your corporate email, company website, and company profile.")
        self.assertEqual(identity["required_fact"], "company_identity_corporate_email_website")
        self.assertEqual(identity["next_action"], "blocked_by_sector_only_disclosure_policy")
        represented = outreach.extract_placement_terms("Please tell me which company you would be representing.")
        self.assertEqual(represented["required_fact"], "company_identity")
        self.assertEqual(represented["next_action"], "blocked_by_sector_only_disclosure_policy")
        company_name = outreach.extract_placement_terms("What is your company name please?")
        self.assertEqual(company_name["required_fact"], "company_identity")
        free = outreach.extract_placement_terms("There are no fees involved or link policies.")
        self.assertEqual(free["price_status"], "free_editorial_route")
        self.assertEqual(free["link_policy"], "none_stated")
        waived = outreach.extract_placement_terms("APCs are fully waived for submissions received by the end of 2026.")
        self.assertEqual(waived["price_status"], "free_editorial_route")
        membership = outreach.extract_placement_terms("Are you an HBA member or does someone at your company have a membership?")
        self.assertEqual(membership["required_fact"], "publisher_membership_status")
        finished_article = outreach.extract_placement_terms("Please submit finished article for review.")
        self.assertEqual(finished_article["content_responsibility"], "client")

    def test_risk_flags_domain_and_credentials(self):
        flags = outreach.reply_risk_flags(
            "agent@gmail.com",
            "publisher.com",
            "Send your password and pay by Bitcoin immediately.",
            ["invoice.xlsm"],
        )
        self.assertIn("sender_domain_mismatch", flags)
        self.assertIn("credential_request", flags)
        self.assertIn("cryptocurrency_payment", flags)
        self.assertIn("risky_attachment", flags)

    def test_bounce_from_mailer_daemon_is_not_risk_hold(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-b", "sent-b", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(state, "thread-b", "bounce-1", "mailer-daemon@googlemail.com", "Delivery Status Notification: message not delivered", "2026-08-25T09:00:00+00:00")
        self.assertEqual(state["prospects"][0]["status"], "bounced")

    def test_delivery_delay_from_mailer_daemon_keeps_waiting(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-delay", "sent-delay", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(state, "thread-delay", "delay-1", "mailer-daemon@googlemail.com", "Delivery Status Notification (Delay): temporarily unable to deliver.", "2026-08-25T09:00:00+00:00")
        self.assertEqual(state["prospects"][0]["status"], "awaiting_reply")
        self.assertEqual(state["prospects"][0]["risk_flags"], [])

    def test_follow_up_is_idempotent_and_stops_after_reply(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")
        outreach.record_follow_up(state, "thread-1", "follow-1", "2026-08-30T08:00:00+00:00")
        outreach.record_follow_up(state, "thread-1", "follow-1", "2026-08-30T08:00:00+00:00")
        self.assertEqual(state["prospects"][0]["follow_up_count"], 1)
        outreach.ingest_reply(state, "thread-1", "reply-1", "editor@publisher.com", "We accept sponsored content.", "2026-08-30T09:00:00+00:00")
        with self.assertRaises(ValueError):
            outreach.record_follow_up(state, "thread-1", "follow-2", "2026-09-04T08:00:00+00:00")

    def test_reply_ingestion_is_idempotent_and_holds_risk(self):
        self.campaign["outreach"]["approved_sender_name"] = "Sample Sender"
        self.campaign["outreach"]["approved_signature"] = "Sample Sender"
        self.campaign["outreach"]["sender_identity_confirmed"] = True
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(
            state, "thread-1", "message-1", "sales@publisher.com",
            "Sponsored placement is $90.", "2026-08-25T09:00:00+00:00",
        )
        self.assertEqual(state["prospects"][0]["status"], "quoted")
        event_count = len(state["events"])
        outreach.ingest_reply(
            state, "thread-1", "message-1", "sales@publisher.com",
            "Sponsored placement is $90.", "2026-08-25T09:00:00+00:00",
        )
        self.assertEqual(len(state["events"]), event_count)

    def test_later_terms_preserve_existing_quote_and_merge_terms(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(state, "thread-1", "reply-1", "sales@publisher.com", "The fee is $90 with a follow link.", "2026-08-25T09:00:00+00:00")
        outreach.ingest_reply(state, "thread-1", "reply-2", "sales@publisher.com", "Yes, it remains permanent and usually goes live in 2 business days.", "2026-08-25T10:00:00+00:00")
        prospect = state["prospects"][0]
        self.assertEqual(prospect["status"], "quoted")
        self.assertEqual(prospect["quote"]["amount_min"], 90)
        self.assertEqual(prospect["placement_terms"]["link_attribute"], "follow")
        self.assertEqual(prospect["placement_terms"]["permanence"], "permanent")
        self.assertEqual(prospect["placement_terms"]["turnaround"], "2 business days")

    def test_later_unclassified_term_does_not_downgrade_positive_reply(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(state, "thread-1", "reply-1", "editor@publisher.com", "You can find our contribution guidelines here.", "2026-08-25T09:00:00+00:00")
        outreach.ingest_reply(state, "thread-1", "reply-2", "editor@publisher.com", "Any links included will remain in the article.", "2026-08-25T10:00:00+00:00")
        self.assertEqual(state["prospects"][0]["status"], "replied")

    def test_cannot_record_sent_before_mailbox_confirmation(self):
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        with self.assertRaises(ValueError):
            outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")

    def test_referral_switch_records_child_thread_and_blocks_duplicates(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        self.shortlist[0]["contact_info"]["email_assessments"] = [
            {"email": "editor@parentco.com", "fit": "high"},
        ]
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "parent-thread", "initial-1", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(
            state, "parent-thread", "reply-1", "editor@parentco.com",
            "Please contact Jane at sales@parentco.com for sponsorship opportunities.",
            "2026-08-25T09:00:00+00:00",
        )
        outreach.record_referral_outreach(
            state, "parent-thread", "sales@parentco.com", "referral-message",
            "referral-thread", "2026-08-25T09:05:00+00:00", "Jane Editor", "Sponsorship inquiry",
        )
        referral = state["prospects"][0]["referral_outreach"][0]
        self.assertEqual(referral["recipient"], "sales@parentco.com")
        self.assertEqual(referral["parent_thread_id"], "parent-thread")
        self.assertEqual(state["prospects"][0]["referral_status"], "awaiting_reply")
        outreach.ingest_reply(
            state, "referral-thread", "referral-reply", "sales@parentco.com",
            "Sponsored content is $125 and includes a permanent follow link.",
            "2026-08-25T10:00:00+00:00",
        )
        self.assertEqual(state["prospects"][0]["status"], "quoted")
        self.assertEqual(state["prospects"][0]["quote"]["amount_min"], 125)
        self.assertEqual(referral["status"], "quoted")
        with self.assertRaises(ValueError):
            outreach.record_referral_outreach(
                state, "parent-thread", "sales@parentco.com", "another-message",
                "another-thread", "2026-08-25T09:06:00+00:00",
            )

    def test_referral_rejects_unevidenced_domain(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        outreach.record_sent(state, "publisher.com", "parent-thread", "initial-1", "2026-08-25T08:00:00+00:00")
        outreach.ingest_reply(
            state, "parent-thread", "reply-1", "editor@publisher.com",
            "Please contact sales@unrelated.example for sponsorship opportunities.",
            "2026-08-25T09:00:00+00:00",
        )
        with self.assertRaises(ValueError):
            outreach.record_referral_outreach(
                state, "parent-thread", "sales@unrelated.example", "msg", "new-thread",
                "2026-08-25T09:05:00+00:00",
            )

    def test_send_paused_attaches_production_message_without_send_authorization(self):
        campaign = dict(self.campaign)
        campaign["outreach"] = {
            "mode": "send_paused", "approved_sender_name": "Sample Sender",
            "approved_signature": "Sample Sender", "sender_identity_confirmed": True,
        }
        state = outreach.initial_state(campaign, self.shortlist, "sender@example.com", True, True)
        outreach.attach_messages(state, [{
            "domain": "publisher.com", "recipient": "editor@publisher.com",
            "subject": "Steel structure article", "body": "Production body",
            "status": "ready_to_send", "banned_phrase_check": "pass",
            "prohibited_disclosure_check": "pass", "duplication_risk": "low",
        }])
        self.assertEqual(state["authorization"]["mode"], "send_paused")
        self.assertEqual(state["prospects"][0]["status"], "ready_to_send")
        with self.assertRaises(ValueError):
            outreach.record_sent(state, "publisher.com", "thread-1", "sent-1", "2026-08-25T08:00:00+00:00")

    def test_append_expansion_preserves_live_state_and_rejects_recipient_duplicates(self):
        self.campaign["outreach"].update({"approved_sender_name":"Sample Sender","approved_signature":"Sample Sender","sender_identity_confirmed":True})
        state = outreach.initial_state(self.campaign, self.shortlist, "sender@example.com", True, True)
        outreach.confirm_mailbox(state, "sender@example.com")
        shortlist = [{
            "domain":"newpublisher.com","site_name":"New Publisher",
            "contact_info":{"recommended_email":"ads@newpublisher.com","recommended_url":"https://newpublisher.com/advertise","email_assessments":[]},
        }]
        messages = [{
            "domain":"newpublisher.com","recipient":"ads@newpublisher.com","recipient_fit":"high",
            "recipient_fit_reason":"advertising contact","subject":"Question","body":"Body\nSample Sender",
            "status":"ready_to_send","banned_phrase_check":"pass","prohibited_disclosure_check":"pass",
            "signature_check":"pass","duplication_risk":"low",
        }]
        outreach.append_expansion(state, shortlist, messages)
        self.assertEqual(len(state["prospects"]), 2)
        self.assertEqual(state["prospects"][1]["status"], "ready_to_send")
        with self.assertRaises(ValueError):
            outreach.append_expansion(state, shortlist, messages)


if __name__ == "__main__":
    unittest.main()
