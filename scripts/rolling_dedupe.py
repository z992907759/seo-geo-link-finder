#!/usr/bin/env python3
"""Remove domains and recipients already evaluated by a rolling campaign."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def normalize_domain(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").rstrip(".")
    return host[4:] if host.startswith("www.") else host


def walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def collect(paths: list[Path]) -> tuple[set[str], set[str]]:
    domains: set[str] = set()
    emails: set[str] = set()
    for path in paths:
        if not path.exists() or path.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for row in walk(payload):
            for key in ("domain", "normalized_domain", "original_domain_raw"):
                domain = normalize_domain(row.get(key))
                if domain:
                    domains.add(domain)
            for key in ("recipient", "recommended_email", "email", "referral_email"):
                email = str(row.get(key) or "").strip().lower()
                if EMAIL_RE.match(email):
                    emails.add(email)
    return domains, emails


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--exclude-root")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    paths: list[Path] = []
    if args.exclude_root:
        exclude_root = Path(args.exclude_root)
        paths.extend(p for p in exclude_root.rglob("*.json") if input_path not in (p.resolve(),))
    paths.extend(Path(p) for p in args.exclude)
    seen_domains, seen_emails = collect(paths)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    rows = payload.get("shortlist", payload) if isinstance(payload, dict) else payload
    kept: list[dict[str, Any]] = []
    audit: list[dict[str, str]] = []
    batch_domains: set[str] = set()
    batch_emails: set[str] = set()
    for row in rows:
        domain = normalize_domain(row.get("normalized_domain") or row.get("domain"))
        contact = row.get("contact_info") or {}
        email = str(row.get("recipient") or contact.get("recommended_email") or "").strip().lower()
        if domain in seen_domains:
            audit.append({"domain": domain, "email": email, "reason": "previously_evaluated_domain"})
            continue
        if email and email in seen_emails:
            audit.append({"domain": domain, "email": email, "reason": "previously_evaluated_recipient"})
            continue
        if domain in batch_domains or (email and email in batch_emails):
            audit.append({"domain": domain, "email": email, "reason": "duplicate_in_current_batch"})
            continue
        batch_domains.add(domain)
        if email:
            batch_emails.add(email)
        kept.append(row)

    output: Any = kept
    if isinstance(payload, dict):
        output = dict(payload)
        output["shortlist"] = kept
        output["rolling_dedupe"] = {
            "input": len(rows),
            "kept": len(kept),
            "excluded": len(audit),
            "seen_domains": len(seen_domains),
            "seen_recipients": len(seen_emails),
        }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kept {len(kept)} of {len(rows)} rows after rolling dedupe")


if __name__ == "__main__":
    main()
