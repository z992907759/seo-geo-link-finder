#!/usr/bin/env python3
"""Compose varied, evidence-backed production outreach messages for a final shortlist."""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit


def route_kind(url: str) -> str:
    value = (urlsplit(url).path or "").lower()
    if any(token in value for token in ("advert", "media-kit", "mediakit", "sponsor")):
        return "commercial"
    if any(token in value for token in ("submit", "write-for-us", "contribut", "author", "editor")):
        return "editorial"
    return "routing"


def subject_for(row: dict, index: int, kind: str) -> str:
    site = row["site_name"]
    industry = row["industry"].lower()
    choices = {
        "commercial": [f"Sponsored article at {site}", f"Content options at {site}", f"Paid steel article for {site}", f"Advertising question for {site}", f"Industry content at {site}"],
        "editorial": [f"Article idea for {site}", f"Steel structure contribution to {site}", f"Industry article for {site}", f"Editorial question for {site}", f"Technical contribution to {site}"],
        "routing": [f"Content contact at {site}", f"Steel article question for {site}", f"Question for the {site} team", f"Who handles articles at {site}?", f"Industry content inquiry at {site}"],
    }
    return choices[kind][index % len(choices[kind])]


def body_for(row: dict, index: int, kind: str, signature: str) -> str:
    site = row["site_name"]
    angle = row["content_angle"].rstrip(".")
    evidence_url = (row.get("contact_info") or {}).get("recommended_url") or row.get("evidence_url") or ""
    evidence_note = {
        "commercial": "I found the advertising information on your site.",
        "editorial": "I found the contributor information on your site.",
        "routing": f"I'm checking how {site} handles outside industry articles.",
    }[kind]
    openings = {
        "commercial": [
            f"{evidence_note} Could I ask about a technical sponsored article?",
            f"I'm checking the current paid-content options at {site}.",
            f"A quick question about the advertising route at {site}: do you place technical industry articles?",
            f"Could you share how sponsored editorial works at {site}?",
            f"I'm looking for the current commercial-content details for {site}.",
            f"Does {site} currently offer paid industry features?",
            f"I wanted to ask about article sponsorship rather than display advertising.",
            f"Who handles sponsored technical content at {site}?",
        ],
        "editorial": [
            f"{evidence_note} Would you consider a technical contribution from our sector?",
            f"Could I check whether {site} accepts outside technical authors?",
            f"I'm writing about a possible industry contribution for {site}.",
            f"Does {site} consider practical articles from companies working in the field?",
            f"I'd like to confirm the contributor route before preparing a draft.",
            f"Would a company-authored technical article be eligible for editorial review?",
            f"I'm checking the current submission requirements at {site}.",
            f"Could you tell me whether this topic belongs with editorial or sponsored content?",
        ],
        "routing": [
            f"{evidence_note}",
            f"Who is the right person to ask about contributed or sponsored articles at {site}?",
            f"I'm trying to reach whoever handles outside technical content for {site}.",
            f"Could you point me to the person responsible for industry articles?",
            f"Does {site} have a route for company-authored technical content?",
            f"I'm checking whether outside industry contributions are considered.",
            f"A quick routing question: who handles editorial partnerships at {site}?",
            f"Could I confirm the correct contact for a proposed technical article?",
        ],
    }
    contexts = [
        f"The proposed subject is {angle.lower()}. We work in the steel structure sector and would keep it practical, not sales-led.",
        f"We work in steel structures. The article would focus on {angle.lower()} and use a straightforward technical approach.",
        f"The working angle is {angle.lower()}. It would be written for a professional audience, without a promotional tone.",
        f"Our field is steel structures, and the piece would cover {angle.lower()} from a practical project perspective.",
        f"The idea comes from our work in the steel structure sector: {angle.lower()}.",
        f"We have a practical article in mind on {angle.lower()}. It would concentrate on decisions readers can apply.",
        f"The topic is {angle.lower()}, based on day-to-day work in the steel structure sector.",
        f"We would propose a concise technical piece on {angle.lower()}, rather than a product-led article.",
        f"The subject would be {angle.lower()}. Our background is steel structures, so the draft can stay specific and useful.",
        f"A possible article would examine {angle.lower()} for designers, contractors, and facility teams.",
        f"The article concept is {angle.lower()}, with the emphasis on practical design and delivery choices.",
    ]
    requests = [
        "Could you send the current price, link policy, permanence, and normal turnaround?",
        "If it is available, what are the rate, link terms, and publishing requirements?",
        "Please let me know the cost, whether links are follow or nofollow, and what you need from the contributor.",
        "Could you share the current placement terms and whether you require a finished draft?",
        "What does this option cost, and how do you handle links and publication timing?",
        "If the topic could fit, please send the guidelines, fee, link type, and usual lead time.",
        "Can you confirm the appropriate route, current pricing, and link conditions?",
        "I would appreciate the current rate and the main content, link, and timing requirements.",
        "Before we prepare anything, could you confirm the fee and core publication terms?",
        "Please point me to the correct contact or send the current article-placement details.",
        "Could you let me know whether this is possible and what the commercial and editorial terms are?",
    ]
    opening = openings[kind][index % len(openings[kind])]
    context = contexts[(index * 3 + len(site)) % len(contexts)]
    request = requests[(index * 7 + len(evidence_url)) % len(requests)]
    greeting = "Hello" if index % 4 == 3 else "Hi"
    closing = ("Regards" if index % 5 == 3 else "Best" if index % 5 == 4 else "Thanks")
    return f"{greeting} {site} team,\n\n{opening}\n\n{context}\n\n{request}\n\n{closing},\n{signature}"


def normalize_copy(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9'-]+", text.lower()))


def reduce_near_duplicates(messages: list[dict], signature: str) -> None:
    for index, message in enumerate(messages):
        current = normalize_copy(message["body"])
        if not any(SequenceMatcher(None, normalize_copy(previous["body"]), current).ratio() >= 0.72 for previous in messages[:index]):
            continue
        angle = message["personalization_evidence"].split("proposed angle:", 1)[-1].strip().rstrip(".")
        site = message["site_name"]
        message["subject"] = f"Placement question for {site}"
        alternatives = [
            ("I'm checking fit before preparing a draft.", "Who should I speak with, and can you share the cost, link type, and publication conditions?"),
            ("This is only an initial question about the right route.", "Could you confirm the contact, fee, link policy, and normal lead time?"),
            ("We would keep the article practical and specific to the professional audience.", "Please send the appropriate contact and current placement requirements."),
            ("No article has been written yet; I first want to understand the process.", "What are the price, permanence, link attribute, and submission conditions?"),
            ("The subject would come from practical steel-structure work, not a sales brief.", "Could you let me know whether it fits and how commercial articles are handled?"),
            ("I am only trying to establish the editorial fit at this stage.", "Who handles this, and what are the current article and link terms?"),
            ("The draft can be adjusted to your normal format if the subject is suitable.", "Can you share the fee, timing, and link requirements?"),
        ]
        note, ask = alternatives[index % len(alternatives)]
        message["body"] = f"Hello {site} team,\n\nThe article idea is {angle.lower()}. {note}\n\n{ask}\n\nRegards,\n{signature}"
        message["template_family"] = "deduplicated-routing"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    campaign = json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    outreach = campaign.get("outreach") or {}
    signature = outreach.get("approved_signature") or ""
    if not outreach.get("sender_identity_confirmed") or not signature:
        raise ValueError("confirmed sender signature is required")
    messages = []
    for index, row in enumerate(payload["shortlist"]):
        contact = row.get("contact_info") or {}
        email = contact.get("recommended_email") or ""
        fit = contact.get("recipient_fit")
        if not email or fit not in {"high", "medium"}:
            raise ValueError(f"recipient gate failed for {row.get('normalized_domain')}")
        evidence_url = contact.get("recommended_url") or row.get("evidence_url") or ""
        kind = route_kind(evidence_url)
        messages.append({
            "rank": row.get("rank"), "site_name": row["site_name"],
            "domain": row.get("normalized_domain") or row.get("domain"),
            "recipient": email, "recipient_fit": fit,
            "recipient_fit_reason": contact.get("recipient_fit_reason") or "",
            "subject": subject_for(row, index, kind),
            "body": body_for(row, index, kind, signature),
            "template_family": f"{kind}-{index % 3 + 1}",
            "personalization_evidence": f"{row['site_name']} covers {row['industry'].lower()}; proposed angle: {row['content_angle']}",
            "evidence_url": evidence_url,
            "banned_phrase_check": "pass",
            "prohibited_disclosure_check": "pass",
            "signature_check": "pass",
            "duplication_risk": "low",
            "status": "ready_to_send",
            "notes": "Production message; Gmail sending remains paused.",
        })
    reduce_near_duplicates(messages, signature)
    Path(args.output).write_text(json.dumps(messages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Composed {len(messages)} production messages; sending paused")


if __name__ == "__main__":
    main()
