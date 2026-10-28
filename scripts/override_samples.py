#!/usr/bin/env python3
"""Apply verified article-sample overrides for sites with nonstandard navigation."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from site_checks import aggregate_check, fetch_and_inspect


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--overrides", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    overrides = json.loads(Path(args.overrides).read_text(encoding="utf-8"))
    for row in payload["shortlist"]:
        domain = row.get("normalized_domain") or row.get("domain")
        urls = overrides.get(domain)
        if not urls:
            continue
        existing = row.get("quality_checks") or {}
        samples = [fetch_and_inspect({"url": url, "search_observation": "unknown"}, args.timeout) for url in urls]
        aggregate = aggregate_check(domain, existing, samples, date.today().isoformat())
        for key in ("traffic_estimate", "traffic_unit", "traffic_source", "traffic_scope", "traffic_checked_at", "organic_serp_count"):
            if key in existing:
                aggregate[key] = existing[key]
        aggregate["sample_discovery"] = "verified manual override for nonstandard publication navigation"
        row["quality_checks"] = aggregate
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Applied verified article-sample overrides")


if __name__ == "__main__":
    main()
