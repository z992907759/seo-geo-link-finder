#!/usr/bin/env python3
"""Deterministic state and safety helpers for Gmail backlink outreach."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+)$", re.I)
PRICE_RE = re.compile(
    r"(?:(?P<symbol>[$€£])\s*(?P<first>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?:-|–|—|to)\s*(?P<second>\d[\d,]*(?:\.\d+)?))?"
    r"|(?P<code_first>\d[\d,]*(?:\.\d+)?)\s*(?P<code>USD|EUR|GBP|AUD|CAD))",
    re.I,
)

NEGATIVE_PATTERNS = (
    "not interested", "don't accept", "do not accept", "no guest posts",
    "not accepting", "we don't offer", "we do not offer", "do not typically publish", "not a fit", "decline", "not in need",
)
AUTO_REPLY_PATTERNS = (
    "automatic reply", "auto reply", "out of office", "away from the office",
    "thank you for contacting", "we have received your message", "we've received your request",
    "we’ve received your request", "registered it in our system", "our team will review it",
    "delivery status notification (delay)", "temporarily unable to deliver", "未完成递送",
)
BOUNCE_PATTERNS = (
    "delivery status notification", "message not delivered", "delivery failed",
    "undeliverable", "mailbox unavailable", "address not found",
)
UNSUBSCRIBE_PATTERNS = (
    "remove me", "do not contact", "don't contact", "unsubscribe",
    "stop emailing", "stop contacting",
)
POSITIVE_PATTERNS = (
    "we accept", "available", "interested", "send details", "send us",
    "guest post", "sponsored post", "advertorial", "media kit", "welcome to submit",
    "submit articles", "for consideration", "editorial guidelines", "sponsorship opportunities",
    "contribution guidelines", "contributor guidelines", "authors and other contributors", "no contributor fee", "happy to take a look", "sponsored content", "do offer sponsored", "please connect with", "please contact",
    "sponsored technical content", "rate sheet", "point you in the right direction",
    "sounds great", "no fees involved", "feel free to send", "sponsored magazine article",
    "submit your paper", "please send your article",
    "submission guidelines", "we do consider outside industry contributions",
    "contributions from industry are welcome", "we would be happy to discuss",
    "we look forward to receiving your manuscript",
    "apcs are fully waived", "apc is fully waived",
    "sponsored article opportunities", "with links where appropriate",
    "several options to reach", "online articles are commonly used",
)
PAYMENT_RISK_PATTERNS = {
    "cryptocurrency_payment": ("bitcoin", "crypto payment", "usdt", "ethereum"),
    "gift_card_payment": ("gift card", "itunes card", "google play card"),
    "informal_transfer": ("western union", "moneygram", "friends and family"),
    "changed_payment_details": ("new bank account", "changed bank account", "updated bank details"),
}
CREDENTIAL_RISK_PATTERNS = {
    "credential_request": (
        "password", "verification code", "one-time code", "otp", "api key",
        "login access", "send your cookie", "remote access",
    ),
}
URGENCY_RISK_PATTERNS = {
    "unusual_urgency": (
        "pay immediately", "within one hour", "keep this confidential",
        "do not tell", "final warning",
    ),
}
RISKY_EXTENSIONS = (".exe", ".dmg", ".pkg", ".js", ".scr", ".bat", ".cmd", ".xlsm", ".docm", ".zip", ".rar", ".7z")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def normalize_email(value: Any) -> str:
    email = str(value or "").strip().lower().strip("<>.,;:")
    return email if EMAIL_RE.match(email) else ""


def normalize_domain(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").rstrip(".")
    return host[4:] if host.startswith("www.") else host


def email_domain(email: str) -> str:
    match = EMAIL_RE.match(normalize_email(email))
    return match.group(1).lower() if match else ""


def domains_related(sender_domain: str, publisher_domain: str) -> bool:
    sender = normalize_domain(sender_domain)
    publisher = normalize_domain(publisher_domain)
    if not sender or not publisher:
        return False
    return sender == publisher or sender.endswith(f".{publisher}") or publisher.endswith(f".{sender}")


def extract_quote(text: str) -> dict[str, Any] | None:
    matches = list(PRICE_RE.finditer(text or ""))
    if not matches:
        return None
    match = matches[0]
    symbol = match.group("symbol")
    currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(symbol, (match.group("code") or "").upper())
    first = match.group("first") or match.group("code_first")
    second = match.group("second") or first
    low, high = sorted((float(first.replace(",", "")), float(second.replace(",", ""))))
    return {
        "amount_min": low,
        "amount_max": high,
        "currency": currency,
        "is_range": low != high,
        "raw": match.group(0).strip(),
    }


def classify_reply(text: str) -> str:
    lowered = (text or "").lower()
    if any(term in lowered for term in ("delivery status notification (delay)", "temporarily unable to deliver", "未完成递送")):
        return "auto_reply"
    if any(term in lowered for term in BOUNCE_PATTERNS):
        return "bounced"
    if any(term in lowered for term in UNSUBSCRIBE_PATTERNS):
        return "unsubscribed"
    if any(term in lowered for term in AUTO_REPLY_PATTERNS):
        return "auto_reply"
    if any(term in lowered for term in NEGATIVE_PATTERNS):
        return "rejected"
    if any(term in lowered for term in (
        "do not think we are a good match", "don't think we are a good match",
        "not a good match for the content",
    )):
        return "rejected"
    if extract_quote(text):
        return "quoted"
    if any(term in lowered for term in (
        "company name", "who you are", "name of your company", "company website",
        "send any editorial enquiries", "editorial enquiries to",
    )):
        return "replied"
    if any(term in lowered for term in POSITIVE_PATTERNS):
        return "replied"
    return "unrelated"


def extract_placement_terms(text: str) -> dict[str, Any]:
    lowered = (text or "").lower()
    terms: dict[str, Any] = {}
    if re.search(r"\b(?:no[- ]?follow)\b", lowered):
        terms["link_attribute"] = "nofollow"
    elif re.search(r"\b(?:do[- ]?follow|follow link)\b", lowered):
        terms["link_attribute"] = "follow"
    if re.search(r"\bnot\s+permanent\b|\bnon[- ]permanent\b", lowered):
        terms["permanence"] = "not_permanent"
    elif re.search(r"\bpermanent(?:ly)?\b", lowered):
        terms["permanence"] = "permanent"
    duration_range = re.search(r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*(business\s+)?(day|week|month)s?\b", lowered)
    duration = duration_range or re.search(r"\b(\d+)\s*(business\s+)?(day|week|month)s?\b", lowered)
    if duration:
        terms["turnaround"] = duration.group(0)
    placement_duration = re.search(r"\b(?:link|placement).{0,40}?\bfor\s+(\d+)\s*(year|month)s?\b", lowered)
    if placement_duration:
        terms["placement_duration"] = f"{placement_duration.group(1)} {placement_duration.group(2)}"
    words = re.search(r"\b(\d{3,4})\+?\s+words\b", lowered)
    if words:
        terms["min_words"] = int(words.group(1))
    if any(value in lowered for value in ("we will write", "we write the article", "written by us")):
        terms["content_responsibility"] = "publisher"
    elif re.search(r"\b(?:you provide|send|submit)\s+(?:the\s+|an\s+|your\s+|finished\s+)?(?:article|draft|content|manuscript)\b", lowered):
        terms["content_responsibility"] = "client"
    referral_match = re.search(
        r"\b(?:please\s+)?(?:contact|connect\s+with|reach\s+out\s+to|speak\s+with|get\s+in\s+touch\s+with)\b"
        r".{0,160}?\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b",
        text or "", flags=re.I | re.S,
    )
    if referral_match:
        terms["referral_email"] = normalize_email(referral_match.group(1))
    if any(value in lowered for value in ("where are you located", "office location", "order would originate")):
        terms["required_fact"] = "order_origin_office_location"
        terms["next_action"] = "awaiting_user_fact"
    if "company website" in lowered and ("corporate email" in lowered or "company profile" in lowered or "which company" in lowered):
        terms["required_fact"] = "company_identity_corporate_email_website"
        terms["next_action"] = "blocked_by_sector_only_disclosure_policy"
    if "company you would be representing" in lowered or "company you represent" in lowered or "company name" in lowered:
        terms["required_fact"] = "company_identity"
        terms["next_action"] = "blocked_by_sector_only_disclosure_policy"
    if "payment is required in advance" in lowered or "payment required in advance" in lowered:
        terms["payment_timing"] = "advance_after_editorial_approval"
    if "paypal" in lowered:
        terms["payment_method"] = "PayPal_invoice"
    if "editorial review and approval" in lowered:
        terms["editorial_review_required"] = True
    if any(value in lowered for value in (
        "no fees involved", "no contributor fee", "no publication fee",
        "apcs are fully waived", "apc is fully waived", "no apc",
    )):
        terms["price_status"] = "free_editorial_route"
    if "no link policies" in lowered or "no link policy" in lowered or re.search(r"\bno\b.{0,30}\blink polic(?:y|ies)\b", lowered):
        terms["link_policy"] = "none_stated"
    if "are you an hba member" in lowered or "company have a membership" in lowered:
        terms["required_fact"] = "publisher_membership_status"
        terms["next_action"] = "awaiting_user_fact"
    return terms


def reply_risk_flags(
    reply_from: str,
    publisher_domain: str,
    text: str,
    attachments: list[str] | None = None,
    allowed_reply_domains: list[str] | None = None,
) -> list[str]:
    flags: list[str] = []
    sender_domain = email_domain(reply_from)
    allowed = [publisher_domain, *(allowed_reply_domains or [])]
    if not any(domains_related(sender_domain, domain) for domain in allowed):
        flags.append("sender_domain_mismatch")

    lowered = (text or "").lower()
    for mapping in (PAYMENT_RISK_PATTERNS, CREDENTIAL_RISK_PATTERNS, URGENCY_RISK_PATTERNS):
        for flag, terms in mapping.items():
            if any(term in lowered for term in terms):
                flags.append(flag)

    for name in attachments or []:
        clean = str(name).lower().split("?", 1)[0]
        if clean.endswith(RISKY_EXTENSIONS):
            flags.append("risky_attachment")
            break
    return list(dict.fromkeys(flags))


def initial_state(
    campaign: dict[str, Any],
    shortlist: list[dict[str, Any]],
    detected_email: str,
    send_capability: bool,
    thread_read_capability: bool,
) -> dict[str, Any]:
    outreach = campaign.get("outreach") or {}
    requested_mode = outreach.get("mode")
    initial_mode = "send_paused" if requested_mode == "send_paused" else "disabled"
    prospects = []
    for row in shortlist:
        contact = row.get("contact_info") or {}
        recipient = normalize_email(contact.get("recommended_email"))
        source_urls = contact.get("source_urls") or []
        has_other_channel = bool(
            contact.get("forms") or contact.get("submission_pages") or
            contact.get("advertising_pages") or contact.get("linkedin_pages") or
            contact.get("whatsapp_links")
        )
        status = "ready" if recipient and source_urls else "other_channel" if has_other_channel else "other_channel"
        allowed_reply_domains = []
        for assessment in contact.get("email_assessments") or []:
            if assessment.get("fit") not in {"high", "medium"}:
                continue
            domain_value = email_domain(assessment.get("email") or "")
            if domain_value and domain_value not in allowed_reply_domains:
                allowed_reply_domains.append(domain_value)
        prospects.append({
            "domain": normalize_domain(row.get("normalized_domain") or row.get("domain")),
            "site_name": row.get("site_name") or "",
            "recipient": recipient,
            "contact_source_url": source_urls[0] if recipient and source_urls else "",
            "status": status,
            "thread_id": "",
            "message_id": "",
            "sent_at": "",
            "last_reply_at": "",
            "reply_from": "",
            "reply_excerpt": "",
            "follow_up_count": 0,
            "clarification_count": 0,
            "clarification_message_ids": [],
            "reply_classification": "",
            "quote": None,
            "placement_terms": {},
            "risk_flags": [],
            "processed_reply_message_ids": [],
            "allowed_reply_domains": allowed_reply_domains,
            "referral_outreach": [],
        })
    return {
        "version": 1,
        "campaign_name": campaign.get("campaign_name") or "",
        "mailbox": {
            "detected_email": normalize_email(detected_email),
            "confirmed_email": "",
            "confirmed_at": "",
            "send_capability": bool(send_capability),
            "thread_read_capability": bool(thread_read_capability),
            "send_as_alias": "",
            "spf": "unknown",
            "dkim": "unknown",
            "dmarc": "unknown",
        },
        "sender_identity": {
            "display_name": outreach.get("approved_sender_name") or outreach.get("sender_display_name") or "",
            "signature": outreach.get("approved_signature") or "",
            "confirmed": bool(outreach.get("sender_identity_confirmed")),
            "confirmed_at": outreach.get("sender_identity_confirmed_at") or "",
        },
        "authorization": {
            "mode": initial_mode,
            "authorized_at": "",
            "target_site": campaign.get("target_site") or "",
            "initial_email": False,
            "follow_ups": False,
            "read_replies": False,
            "factual_clarifications": False,
        },
        "settings": {
            "daily_send_cap": int(outreach.get("daily_send_cap", 20)),
            "monitoring_timezone": outreach.get("monitoring_timezone", "Asia/Shanghai"),
            "reply_check_times": outreach.get("reply_check_times", ["09:00", "16:00"]),
            "reply_check_days": outreach.get("reply_check_days", ["MO", "TU", "WE", "TH", "FR"]),
            "follow_up_days": outreach.get("follow_up_days", [5, 10]),
            "max_follow_ups": int(outreach.get("max_follow_ups", 2)),
            "monitoring_duration_days": int(outreach.get("monitoring_duration_days", 30)),
            "monitoring_settings_confirmed": bool(outreach.get("monitoring_settings_confirmed")),
            "monitoring_settings_confirmed_at": outreach.get("monitoring_settings_confirmed_at") or "",
            "scheduled_task_id": "",
            "scheduled_task_created_at": "",
        },
        "prospects": prospects,
        "events": [{"type": "mailbox_detected", "at": now_iso(), "email": normalize_email(detected_email)}],
    }


def attach_messages(state: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    if state.get("authorization", {}).get("mode") != "send_paused":
        raise ValueError("production messages can be attached only while sending is paused")
    if not state.get("sender_identity", {}).get("confirmed"):
        raise ValueError("sender display name and signature must be confirmed before composition")
    attached = 0
    for message in messages:
        domain = normalize_domain(message.get("domain"))
        prospect = next((row for row in state["prospects"] if row.get("domain") == domain), None)
        if prospect is None:
            raise ValueError(f"message has no matching prospect: {domain}")
        if normalize_email(message.get("recipient")) != prospect.get("recipient"):
            raise ValueError(f"message recipient does not match sourced contact: {domain}")
        status = message.get("status")
        if status != "ready_to_send":
            raise ValueError(f"invalid prepared-message status for {domain}: {status}")
        prospect.update({
            "status": status,
            "subject": message.get("subject") or "",
            "body": message.get("body") or "",
            "template_family": message.get("template_family") or "",
            "personalization_evidence": message.get("personalization_evidence") or "",
            "message_evidence_url": message.get("evidence_url") or "",
            "recipient_fit": message.get("recipient_fit") or "",
            "recipient_fit_reason": message.get("recipient_fit_reason") or "",
            "banned_phrase_check": message.get("banned_phrase_check") or "",
            "prohibited_disclosure_check": message.get("prohibited_disclosure_check") or "",
            "duplication_risk": message.get("duplication_risk") or "",
            "message_notes": message.get("notes") or "",
        })
        attached += 1
    state["events"].append({"type": "production_messages_prepared", "at": now_iso(), "count": attached, "sending": "paused"})
    return state


def append_expansion(
    state: dict[str, Any], shortlist: list[dict[str, Any]], messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Append an authorized, recipient-qualified campaign expansion without resetting live threads."""
    if state.get("authorization", {}).get("mode") != "automatic_outreach":
        raise ValueError("automatic outreach must already be authorized before appending an expansion")
    if not state.get("sender_identity", {}).get("confirmed"):
        raise ValueError("sender identity and signature are not confirmed")
    by_domain = {normalize_domain(row.get("normalized_domain") or row.get("domain")): row for row in shortlist}
    message_by_domain = {normalize_domain(row.get("domain")): row for row in messages}
    if set(by_domain) != set(message_by_domain):
        raise ValueError("expansion shortlist and production-message domains must match exactly")

    existing_domains = {row.get("domain") for row in state.get("prospects", [])}
    existing_recipients = {
        normalize_email(row.get("recipient")) for row in state.get("prospects", [])
        if normalize_email(row.get("recipient"))
    }
    existing_recipients.update(
        normalize_email(referral.get("recipient"))
        for row in state.get("prospects", []) for referral in row.get("referral_outreach", [])
        if normalize_email(referral.get("recipient"))
    )
    batch_recipients: set[str] = set()
    appended = 0
    for domain, row in by_domain.items():
        if domain in existing_domains:
            raise ValueError(f"expansion domain was already contacted or queued: {domain}")
        message = message_by_domain[domain]
        contact = row.get("contact_info") or {}
        recipient = normalize_email(message.get("recipient"))
        source_url = contact.get("recommended_url") or ""
        if message.get("status") != "ready_to_send" or message.get("recipient_fit") not in {"high", "medium"}:
            raise ValueError(f"production recipient gate failed: {domain}")
        if recipient != normalize_email(contact.get("recommended_email")) or not source_url:
            raise ValueError(f"message recipient lacks matching public contact evidence: {domain}")
        if recipient in existing_recipients or recipient in batch_recipients:
            raise ValueError(f"expansion recipient was already contacted or duplicated: {recipient}")
        batch_recipients.add(recipient)
        allowed_reply_domains = [domain, email_domain(recipient)]
        for assessment in contact.get("email_assessments") or []:
            if assessment.get("fit") not in {"high", "medium"}:
                continue
            assessed_domain = email_domain(assessment.get("email") or "")
            if assessed_domain:
                allowed_reply_domains.append(assessed_domain)
        state["prospects"].append({
            "domain": domain,
            "site_name": row.get("site_name") or "",
            "recipient": recipient,
            "contact_source_url": source_url,
            "status": "ready_to_send",
            "thread_id": "",
            "message_id": "",
            "sent_at": "",
            "last_reply_at": "",
            "reply_from": "",
            "reply_excerpt": "",
            "follow_up_count": 0,
            "clarification_count": 0,
            "clarification_message_ids": [],
            "reply_classification": "",
            "quote": None,
            "placement_terms": {},
            "risk_flags": [],
            "processed_reply_message_ids": [],
            "allowed_reply_domains": list(dict.fromkeys(normalize_domain(value) for value in allowed_reply_domains if value)),
            "referral_outreach": [],
            "subject": message.get("subject") or "",
            "body": message.get("body") or "",
            "template_family": message.get("template_family") or "",
            "personalization_evidence": message.get("personalization_evidence") or "",
            "message_evidence_url": message.get("evidence_url") or "",
            "recipient_fit": message.get("recipient_fit") or "",
            "recipient_fit_reason": message.get("recipient_fit_reason") or "",
            "banned_phrase_check": message.get("banned_phrase_check") or "",
            "prohibited_disclosure_check": message.get("prohibited_disclosure_check") or "",
            "signature_check": message.get("signature_check") or "",
            "duplication_risk": message.get("duplication_risk") or "",
            "message_notes": "Authorized campaign expansion; ready for Gmail delivery.",
        })
        appended += 1
    state["events"].append({"type": "campaign_expansion_prepared", "at": now_iso(), "count": appended})
    return state


def confirm_mailbox(state: dict[str, Any], confirmed_email: str, at: str | None = None) -> dict[str, Any]:
    email = normalize_email(confirmed_email)
    mailbox = state["mailbox"]
    if email != mailbox.get("detected_email"):
        raise ValueError("confirmed mailbox does not match the detected Gmail mailbox")
    if not mailbox.get("send_capability") or not mailbox.get("thread_read_capability"):
        raise ValueError("Gmail send and thread read/search capabilities are both required")
    if not state.get("sender_identity", {}).get("confirmed"):
        raise ValueError("sender display name and signature must be confirmed before enabling outreach")
    if not state.get("settings", {}).get("monitoring_settings_confirmed"):
        raise ValueError("monitoring and follow-up settings must be confirmed before enabling outreach")
    timestamp = at or now_iso()
    mailbox["confirmed_email"] = email
    mailbox["confirmed_at"] = timestamp
    state["authorization"].update({
        "mode": "automatic_outreach",
        "authorized_at": timestamp,
        "initial_email": True,
        "follow_ups": True,
        "read_replies": True,
        "factual_clarifications": True,
    })
    state["events"].append({"type": "automatic_outreach_authorized", "at": timestamp, "email": email})
    return state


def record_sent(
    state: dict[str, Any],
    domain: str,
    thread_id: str,
    message_id: str,
    sent_at: str,
) -> dict[str, Any]:
    if state.get("authorization", {}).get("mode") != "automatic_outreach":
        raise ValueError("automatic outreach is not authorized for this campaign")
    normalized = normalize_domain(domain)
    prospect = next((row for row in state["prospects"] if row.get("domain") == normalized), None)
    if prospect is None:
        raise ValueError(f"unknown prospect domain: {domain}")
    if prospect.get("status") not in {"ready", "ready_to_send"}:
        raise ValueError(f"prospect is not ready to send: {prospect.get('status')}")
    if not prospect.get("recipient") or not prospect.get("contact_source_url"):
        raise ValueError("prospect lacks a sourced public business email")
    prospect.update({
        "status": "awaiting_reply",
        "thread_id": thread_id,
        "message_id": message_id,
        "sent_at": sent_at,
    })
    state["events"].append({
        "type": "initial_email_sent",
        "at": sent_at,
        "domain": normalized,
        "thread_id": thread_id,
        "message_id": message_id,
    })
    return state


def record_clarification(
    state: dict[str, Any], thread_id: str, message_id: str, sent_at: str,
) -> dict[str, Any]:
    prospect = next((row for row in state["prospects"] if row.get("thread_id") == thread_id), None)
    if prospect is None:
        raise ValueError(f"unknown Gmail thread: {thread_id}")
    if prospect.get("clarification_count", 0) >= 1:
        raise ValueError("factual clarification has already been sent for this thread")
    prospect["clarification_count"] = 1
    prospect.setdefault("clarification_message_ids", []).append(message_id)
    prospect["last_outbound_at"] = sent_at
    state["events"].append({"type": "factual_clarification_sent", "at": sent_at, "thread_id": thread_id, "message_id": message_id})
    return state


def record_follow_up(
    state: dict[str, Any], thread_id: str, message_id: str, sent_at: str,
) -> dict[str, Any]:
    """Record one idempotent follow-up on an unanswered original or referral thread."""
    record: dict[str, Any] | None = next(
        (row for row in state["prospects"] if row.get("thread_id") == thread_id), None,
    )
    parent: dict[str, Any] | None = record
    if record is None:
        for row in state["prospects"]:
            referral = next(
                (item for item in row.get("referral_outreach", []) if item.get("thread_id") == thread_id),
                None,
            )
            if referral is not None:
                record = referral
                parent = row
                break
    if record is None or parent is None:
        raise ValueError(f"unknown Gmail thread: {thread_id}")
    if record.get("status") != "awaiting_reply":
        raise ValueError(f"follow-up blocked for terminal or replied status: {record.get('status')}")
    ids = record.setdefault("follow_up_message_ids", [])
    if message_id in ids:
        return state
    maximum = int(state.get("settings", {}).get("max_follow_ups", 2))
    count = int(record.get("follow_up_count", 0))
    if count >= maximum:
        raise ValueError("maximum follow-up count reached")
    record["follow_up_count"] = count + 1
    ids.append(message_id)
    record["last_outbound_at"] = sent_at
    state["events"].append({
        "type": "follow_up_sent",
        "at": sent_at,
        "thread_id": thread_id,
        "message_id": message_id,
        "parent_thread_id": parent.get("thread_id") if record is not parent else "",
        "follow_up_number": record["follow_up_count"],
    })
    return state


def record_referral_outreach(
    state: dict[str, Any],
    parent_thread_id: str,
    referral_email: str,
    message_id: str,
    thread_id: str,
    sent_at: str,
    referred_by: str = "",
    subject: str = "",
) -> dict[str, Any]:
    """Record one new-thread outreach to a contact explicitly supplied in a reply."""
    if state.get("authorization", {}).get("mode") != "automatic_outreach":
        raise ValueError("automatic outreach is not authorized for this campaign")
    prospect = next((row for row in state["prospects"] if row.get("thread_id") == parent_thread_id), None)
    if prospect is None:
        raise ValueError(f"unknown parent Gmail thread: {parent_thread_id}")
    if prospect.get("risk_flags"):
        raise ValueError("referral outreach is blocked while the parent reply is on risk hold")

    normalized_email = normalize_email(referral_email)
    expected_email = normalize_email((prospect.get("placement_terms") or {}).get("referral_email"))
    if not normalized_email or normalized_email != expected_email:
        raise ValueError("referral email must exactly match the address extracted from the publisher reply")

    allowed_domains = [prospect.get("domain"), *(prospect.get("allowed_reply_domains") or [])]
    if not any(domains_related(email_domain(normalized_email), domain) for domain in allowed_domains):
        raise ValueError("referral email domain is not an evidenced publisher or parent-company domain")

    referrals = prospect.setdefault("referral_outreach", [])
    existing = next((row for row in referrals if normalize_email(row.get("recipient")) == normalized_email), None)
    if existing:
        if existing.get("message_id") == message_id and existing.get("thread_id") == thread_id:
            return state
        raise ValueError("this referral contact has already been contacted")

    referrals.append({
        "recipient": normalized_email,
        "referred_by": referred_by.strip(),
        "parent_thread_id": parent_thread_id,
        "message_id": message_id,
        "thread_id": thread_id,
        "subject": subject,
        "sent_at": sent_at,
        "status": "awaiting_reply",
        "processed_reply_message_ids": [],
    })
    prospect["referral_status"] = "awaiting_reply"
    prospect["referral_contact"] = normalized_email
    state["events"].append({
        "type": "referral_outreach_sent",
        "at": sent_at,
        "domain": prospect.get("domain"),
        "parent_thread_id": parent_thread_id,
        "thread_id": thread_id,
        "message_id": message_id,
        "recipient": normalized_email,
        "referred_by": referred_by.strip(),
    })
    return state


def ingest_reply(
    state: dict[str, Any],
    thread_id: str,
    message_id: str,
    reply_from: str,
    body: str,
    received_at: str,
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    prospect = next((row for row in state["prospects"] if row.get("thread_id") == thread_id), None)
    reply_record: dict[str, Any] | None = prospect
    is_referral = False
    if prospect is None:
        for row in state["prospects"]:
            referral = next((item for item in row.get("referral_outreach", []) if item.get("thread_id") == thread_id), None)
            if referral is not None:
                prospect = row
                reply_record = referral
                is_referral = True
                break
    if prospect is None or reply_record is None:
        raise ValueError(f"unknown Gmail thread: {thread_id}")
    if message_id in reply_record.setdefault("processed_reply_message_ids", []):
        return state

    previous_status = reply_record.get("status") or ""
    classification = classify_reply(body)
    normalized_sender = normalize_email(reply_from)
    system_delivery_notice = "mailer-daemon" in normalized_sender
    flags = [] if classification == "bounced" or (classification == "auto_reply" and system_delivery_notice) else reply_risk_flags(reply_from, prospect["domain"], body, attachments, prospect.get("allowed_reply_domains") or [])
    status = "risk_hold" if flags else classification
    extracted_quote = extract_quote(body)
    extracted_terms = extract_placement_terms(body)
    previous_quote = reply_record.get("quote") or (prospect.get("quote") if is_referral else None)
    effective_quote = extracted_quote or previous_quote
    previous_terms = dict(prospect.get("placement_terms") or {}) if is_referral else {}
    previous_terms.update(reply_record.get("placement_terms") or {})
    merged_terms = {**previous_terms, **extracted_terms}
    if not flags and classification == "auto_reply":
        status = "quoted" if effective_quote else "awaiting_reply"
    elif not flags and effective_quote and classification in {"replied", "unrelated"}:
        status = "quoted"
    elif not flags and classification == "unrelated" and previous_status in {"replied", "quoted"}:
        status = previous_status
    reply_record.update({
        "status": status,
        "last_reply_at": received_at,
        "reply_from": normalize_email(reply_from),
        "reply_excerpt": " ".join((body or "").split())[:500],
        "reply_classification": classification,
        "quote": effective_quote,
        "placement_terms": merged_terms,
        "risk_flags": list(dict.fromkeys([*reply_record.get("risk_flags", []), *flags])),
    })
    reply_record["processed_reply_message_ids"].append(message_id)
    if is_referral:
        prospect.update({
            "status": status,
            "referral_status": status,
            "last_reply_at": received_at,
            "reply_from": normalize_email(reply_from),
            "reply_excerpt": reply_record["reply_excerpt"],
            "reply_classification": classification,
            "quote": effective_quote,
            "placement_terms": merged_terms,
            "risk_flags": list(dict.fromkeys([*prospect.get("risk_flags", []), *flags])),
        })
    state["events"].append({
        "type": "reply_ingested",
        "at": received_at,
        "thread_id": thread_id,
        "message_id": message_id,
        "parent_thread_id": prospect.get("thread_id") if is_referral else "",
        "referral_reply": is_referral,
        "classification": classification,
        "status": status,
        "risk_flags": flags,
    })
    return state


def summarize(state: dict[str, Any]) -> dict[str, int]:
    counts = Counter(row.get("status") or "unknown" for row in state.get("prospects", []))
    return dict(sorted(counts.items()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--campaign", required=True)
    init.add_argument("--shortlist", required=True)
    init.add_argument("--detected-email", required=True)
    init.add_argument("--send-capability", action="store_true")
    init.add_argument("--thread-read-capability", action="store_true")
    init.add_argument("--output", required=True)

    confirm = commands.add_parser("confirm-mailbox")
    confirm.add_argument("--state", required=True)
    confirm.add_argument("--email", required=True)

    sent = commands.add_parser("record-sent")
    sent.add_argument("--state", required=True)
    sent.add_argument("--domain", required=True)
    sent.add_argument("--thread-id", required=True)
    sent.add_argument("--message-id", required=True)
    sent.add_argument("--sent-at", required=True)

    reply = commands.add_parser("ingest-reply")
    reply.add_argument("--state", required=True)
    reply.add_argument("--thread-id", required=True)
    reply.add_argument("--message-id", required=True)
    reply.add_argument("--reply-from", required=True)
    reply.add_argument("--body", required=True)
    reply.add_argument("--received-at", required=True)
    reply.add_argument("--attachment", action="append", default=[])

    attach = commands.add_parser("attach-messages")
    attach.add_argument("--state", required=True)
    attach.add_argument("--messages", required=True)

    expansion = commands.add_parser("append-expansion")
    expansion.add_argument("--state", required=True)
    expansion.add_argument("--shortlist", required=True)
    expansion.add_argument("--messages", required=True)

    batch_reply = commands.add_parser("ingest-replies-file")
    batch_reply.add_argument("--state", required=True)
    batch_reply.add_argument("--input", required=True)

    clarification = commands.add_parser("record-clarification")
    clarification.add_argument("--state", required=True)
    clarification.add_argument("--thread-id", required=True)
    clarification.add_argument("--message-id", required=True)
    clarification.add_argument("--sent-at", required=True)

    follow_up = commands.add_parser("record-follow-up")
    follow_up.add_argument("--state", required=True)
    follow_up.add_argument("--thread-id", required=True)
    follow_up.add_argument("--message-id", required=True)
    follow_up.add_argument("--sent-at", required=True)

    referral = commands.add_parser("record-referral-outreach")
    referral.add_argument("--state", required=True)
    referral.add_argument("--parent-thread-id", required=True)
    referral.add_argument("--referral-email", required=True)
    referral.add_argument("--message-id", required=True)
    referral.add_argument("--thread-id", required=True)
    referral.add_argument("--sent-at", required=True)
    referral.add_argument("--referred-by", default="")
    referral.add_argument("--subject", default="")

    summary = commands.add_parser("summary")
    summary.add_argument("--state", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "init":
        campaign = read_json(args.campaign)
        shortlist_data = read_json(args.shortlist)
        shortlist = shortlist_data.get("shortlist", shortlist_data) if isinstance(shortlist_data, dict) else shortlist_data
        state = initial_state(campaign, shortlist, args.detected_email, args.send_capability, args.thread_read_capability)
        write_json(args.output, state)
        print(json.dumps(summarize(state), ensure_ascii=False))
    elif args.command == "confirm-mailbox":
        state = read_json(args.state)
        confirm_mailbox(state, args.email)
        write_json(args.state, state)
        print(f"Authorized automatic outreach from {state['mailbox']['confirmed_email']}")
    elif args.command == "record-sent":
        state = read_json(args.state)
        record_sent(state, args.domain, args.thread_id, args.message_id, args.sent_at)
        write_json(args.state, state)
        print(f"Recorded sent message for {normalize_domain(args.domain)}")
    elif args.command == "ingest-reply":
        state = read_json(args.state)
        ingest_reply(
            state, args.thread_id, args.message_id, args.reply_from, args.body,
            args.received_at, args.attachment,
        )
        write_json(args.state, state)
        print(json.dumps(summarize(state), ensure_ascii=False))
    elif args.command == "attach-messages":
        state = read_json(args.state)
        attach_messages(state, read_json(args.messages))
        write_json(args.state, state)
        print(json.dumps(summarize(state), ensure_ascii=False))
    elif args.command == "append-expansion":
        state = read_json(args.state)
        shortlist_payload = read_json(args.shortlist)
        shortlist = shortlist_payload.get("shortlist", shortlist_payload) if isinstance(shortlist_payload, dict) else shortlist_payload
        append_expansion(state, shortlist, read_json(args.messages))
        write_json(args.state, state)
        print(json.dumps(summarize(state), ensure_ascii=False))
    elif args.command == "ingest-replies-file":
        state = read_json(args.state)
        for item in read_json(args.input):
            ingest_reply(
                state, item["thread_id"], item["message_id"], item["reply_from"],
                item["body"], item["received_at"], item.get("attachments") or [],
            )
        write_json(args.state, state)
        print(json.dumps(summarize(state), ensure_ascii=False))
    elif args.command == "record-clarification":
        state = read_json(args.state)
        record_clarification(state, args.thread_id, args.message_id, args.sent_at)
        write_json(args.state, state)
        print(f"Recorded factual clarification for {args.thread_id}")
    elif args.command == "record-follow-up":
        state = read_json(args.state)
        record_follow_up(state, args.thread_id, args.message_id, args.sent_at)
        write_json(args.state, state)
        print(f"Recorded follow-up for {args.thread_id}")
    elif args.command == "record-referral-outreach":
        state = read_json(args.state)
        record_referral_outreach(
            state, args.parent_thread_id, args.referral_email, args.message_id,
            args.thread_id, args.sent_at, args.referred_by, args.subject,
        )
        write_json(args.state, state)
        print(f"Recorded referral outreach to {normalize_email(args.referral_email)}")
    elif args.command == "summary":
        print(json.dumps(summarize(read_json(args.state)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
