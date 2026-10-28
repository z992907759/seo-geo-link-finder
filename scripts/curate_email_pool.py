#!/usr/bin/env python3
"""Apply an evidence-backed recipient selection spec to contact research results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    by_domain = {row.get("normalized_domain") or row.get("domain"): row for row in payload["shortlist"]}
    selected = []
    for item in spec:
        domain = item["domain"]
        row = by_domain.get(domain)
        if row is None:
            raise ValueError(f"domain not present in contact results: {domain}")
        contact = dict(row.get("contact_info") or {})
        assessments = {entry.get("email"): entry for entry in contact.get("email_assessments", [])}
        observed = {email: entry.get("source_url") for email, entry in assessments.items()}
        if item["email"] not in observed:
            raise ValueError(f"email was not observed for {domain}: {item['email']}")
        assessment = assessments[item["email"]]
        contact.update({
            "recommended_email": item["email"],
            "recommended_url": item.get("source_url") or observed[item["email"]],
            "recipient_fit": item.get("fit") or assessment.get("fit"),
            "recipient_fit_reason": item.get("reason") or assessment.get("reason"),
            "selected_email_observed_at": observed[item["email"]],
            "selected_for_quality_review": True,
        })
        result = dict(row)
        result["contact_info"] = contact
        selected.append(result)
    output = dict(payload)
    output["shortlist"] = selected
    output["curated_email_pool_count"] = len(selected)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Curated {len(selected)} evidence-backed email candidates")


if __name__ == "__main__":
    main()
