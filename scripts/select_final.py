#!/usr/bin/env python3
"""Select and normalize the final outreach candidates from a reviewed pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload["shortlist"]
    by_domain = {row.get("normalized_domain") or row.get("domain"): row for row in rows}
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    final = []
    selected_domains = set()
    for rank, item in enumerate(spec, start=1):
        domain = item["domain"]
        row = by_domain.get(domain)
        if row is None:
            raise ValueError(f"final selection domain missing: {domain}")
        result = dict(row)
        result.update({
            "rank": rank,
            "site_name": item["site_name"],
            "industry": item["industry"],
            "content_angle": item["content_angle"],
            "recommendation": "ready_to_compose",
        })
        final.append(result)
        selected_domains.add(domain)
    audit = [{"domain": row.get("normalized_domain") or row.get("domain"), "reason": "not selected after final relevance, contact, and article-quality review"} for row in rows if (row.get("normalized_domain") or row.get("domain")) not in selected_domains]
    output = dict(payload)
    output["shortlist"] = final
    output["final_count"] = len(final)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Selected {len(final)} final outreach candidates")


if __name__ == "__main__":
    main()
