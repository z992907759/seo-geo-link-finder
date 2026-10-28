#!/usr/bin/env python3
"""Apply syntax, placeholder, and MX-domain checks before Gmail outreach."""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
from pathlib import Path


EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+)$", re.I)
PLACEHOLDER_PARTS = ("example", "test@", "name@", "yourdomain", "sentry", "wixpress")


def mx_records(domain: str) -> list[str]:
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain], check=False, capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def address_records(domain: str) -> list[str]:
    try:
        values = socket.getaddrinfo(domain, None)
    except OSError:
        return []
    return list(dict.fromkeys(item[4][0] for item in values if item[4]))


def check_email(email: str) -> tuple[bool, str, list[str]]:
    value = str(email or "").strip().lower()
    match = EMAIL_RE.match(value)
    if not match:
        return False, "invalid_email_syntax", []
    if any(part in value for part in PLACEHOLDER_PARTS):
        return False, "placeholder_or_telemetry_address", []
    records = mx_records(match.group(1).lower())
    if records:
        return True, "mx_observed", records
    fallback = address_records(match.group(1).lower())
    if fallback:
        return True, "mail_domain_a_fallback_observed", fallback
    return False, "mail_domain_has_no_observed_mx_or_address", []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload.get("shortlist", payload)
    kept, audit = [], []
    for row in rows:
        contact = row.get("contact_info") or {}
        email = contact.get("recommended_email") or ""
        ok, reason, records = check_email(email)
        if ok:
            result = dict(row)
            result_contact = dict(contact)
            result_contact["mx_preflight"] = {"status": reason, "records": records}
            result["contact_info"] = result_contact
            kept.append(result)
        else:
            audit.append({"domain": row.get("normalized_domain") or row.get("domain"), "email": email, "reason": reason})
    output = dict(payload) if isinstance(payload, dict) else {}
    output["shortlist"] = kept
    output["email_preflight"] = {"input": len(rows), "kept": len(kept), "excluded": len(audit)}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Email preflight kept {len(kept)} of {len(rows)} candidates")


if __name__ == "__main__":
    main()
