#!/usr/bin/env python3
"""Validate production outreach copy for disclosure, AI-style, and duplication risks."""

from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


BANNED_PHRASES = (
    "i hope this email finds you well",
    "i came across your amazing website",
    "valuable insights",
    "mutually beneficial",
    "elevate our online presence",
    "in today's digital landscape",
    "delve into",
    "unlock the potential",
    "game-changer",
    "cutting-edge solution",
    "seamlessly integrate",
)


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9'-]+", text or "")


def normalized_copy(text: str) -> str:
    return " ".join(word.lower() for word in words(text))


def client_tokens(campaign: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for value in (campaign.get("target_site"), campaign.get("campaign_name")):
        for token in re.findall(r"[a-z0-9]{6,}", str(value or "").lower()):
            if token not in {"https", "english", "global", "discovery", "pilot", "steel", "structure", "buildings", "outreach", "full", "rerun"}:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def with_signature(body: str, signature: str) -> str:
    lines = (body or "").rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines:
        lines[-1] = signature
    else:
        lines = [signature]
    return "\n".join(lines)


def prepare_ready_messages(campaign: dict[str, Any], messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outreach = campaign.get("outreach") or {}
    signature = str(outreach.get("approved_signature") or "").strip()
    if not outreach.get("sender_identity_confirmed") or not signature:
        raise ValueError("sender display name and signature must be confirmed before preparing messages")
    prepared = []
    for source in messages:
        if source.get("status") != "ready_to_send" or source.get("recipient_fit") not in {"high", "medium"}:
            continue
        row = dict(source)
        row["body"] = with_signature(str(row.get("body") or ""), signature)
        row["signature_check"] = "pass"
        prepared.append(row)
    return prepared


def validate_messages(campaign: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    tokens = client_tokens(campaign)
    bodies: list[tuple[str, str]] = []
    subjects: set[str] = set()
    ready_count = 0
    recheck_count = 0
    outreach = campaign.get("outreach") or {}
    confirmed_signature = str(outreach.get("approved_signature") or "").strip()
    if not outreach.get("sender_identity_confirmed") or not confirmed_signature:
        errors.append("campaign: sender display name and signature are not confirmed")

    for index, row in enumerate(messages, start=1):
        label = row.get("domain") or f"row {index}"
        subject = str(row.get("subject") or "").strip()
        body = str(row.get("body") or "").strip()
        recipient = str(row.get("recipient") or "").strip()
        lowered = f"{subject}\n{body}".lower()
        count = len(words(body))

        if not subject or not body or not recipient:
            errors.append(f"{label}: missing subject, body, or recipient")
        if count < 35 or count > 120:
            warnings.append(f"{label}: body length is {count} words")
        hits = [phrase for phrase in BANNED_PHRASES if phrase in lowered]
        if hits:
            errors.append(f"{label}: banned AI-style phrase(s): {', '.join(hits)}")
        leaks = [token for token in tokens if token and token in lowered]
        if re.search(r"https?://|www\.", lowered):
            leaks.append("URL")
        if leaks:
            errors.append(f"{label}: prohibited client disclosure: {', '.join(sorted(set(leaks)))}")
        if subject.lower() in subjects:
            warnings.append(f"{label}: duplicate subject")
        subjects.add(subject.lower())
        bodies.append((label, normalized_copy(body)))

        status = row.get("status")
        ready_count += status == "ready_to_send"
        recheck_count += status == "contact_recheck"
        if status != "ready_to_send" or row.get("recipient_fit") not in {"high", "medium"}:
            errors.append(f"{label}: recipient-fit gate was not completed before composition")
        last_line = next((line.strip() for line in reversed(body.splitlines()) if line.strip()), "")
        signature_ok = bool(confirmed_signature) and last_line == confirmed_signature
        if not signature_ok:
            errors.append(f"{label}: signature does not match the confirmed value")
        if row.get("signature_check") not in {None, "pass" if signature_ok else "fail"}:
            errors.append(f"{label}: signature check field is inconsistent")
        expected_disclosure = "pass" if not leaks else "fail"
        expected_banned = "pass" if not hits else "fail"
        if row.get("prohibited_disclosure_check") != expected_disclosure:
            errors.append(f"{label}: disclosure check field is inconsistent")
        if row.get("banned_phrase_check") != expected_banned:
            errors.append(f"{label}: banned-phrase check field is inconsistent")

    max_similarity = 0.0
    max_pair: tuple[str, str] | None = None
    for i, (left_label, left) in enumerate(bodies):
        for right_label, right in bodies[i + 1:]:
            ratio = SequenceMatcher(None, left, right).ratio()
            if ratio > max_similarity:
                max_similarity = ratio
                max_pair = (left_label, right_label)
            if ratio >= 0.72:
                warnings.append(f"high copy similarity {ratio:.2f}: {left_label} / {right_label}")

    return {
        "valid": not errors,
        "message_count": len(messages),
        "ready_to_send": ready_count,
        "contact_recheck": recheck_count,
        "max_pair_similarity": round(max_similarity, 3),
        "max_similarity_pair": list(max_pair) if max_pair else [],
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--messages", required=True)
    parser.add_argument("--output-ready")
    args = parser.parse_args()
    campaign = read_json(args.campaign)
    messages = read_json(args.messages)
    if args.output_ready:
        messages = prepare_ready_messages(campaign, messages)
        write_json(args.output_ready, messages)
    result = validate_messages(campaign, messages)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
