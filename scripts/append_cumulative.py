#!/usr/bin/env python3
"""Idempotently append one qualified rolling batch to cumulative JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


def domain(value: str) -> str:
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def write(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cumulative-candidates", required=True)
    parser.add_argument("--cumulative-messages", required=True)
    parser.add_argument("--batch-candidates", required=True)
    parser.add_argument("--batch-messages", required=True)
    args = parser.parse_args()

    candidate_path = Path(args.cumulative_candidates)
    message_path = Path(args.cumulative_messages)
    candidates = json.loads(candidate_path.read_text(encoding="utf-8"))
    messages = json.loads(message_path.read_text(encoding="utf-8"))
    batch_candidates = json.loads(Path(args.batch_candidates).read_text(encoding="utf-8"))["shortlist"]
    batch_messages = json.loads(Path(args.batch_messages).read_text(encoding="utf-8"))

    known_domains = {domain(row.get("normalized_domain") or row.get("domain") or "") for row in candidates["shortlist"]}
    known_recipients = {str(row.get("recipient") or "").lower() for row in messages}
    added_candidates = []
    for row in batch_candidates:
        key = domain(row.get("normalized_domain") or row.get("domain") or "")
        if key and key not in known_domains:
            candidates["shortlist"].append(row)
            known_domains.add(key)
            added_candidates.append(key)
    added_messages = []
    for row in batch_messages:
        key = str(row.get("recipient") or "").lower()
        if key and key not in known_recipients:
            messages.append(row)
            known_recipients.add(key)
            added_messages.append(key)
    if len(added_candidates) != len(added_messages):
        raise ValueError(f"candidate/message append mismatch: {len(added_candidates)} vs {len(added_messages)}")

    candidates["shortlist_count"] = len(candidates["shortlist"])
    candidates["unique_eligible_count"] = len(candidates["shortlist"])
    write(candidate_path, candidates)
    write(message_path, messages)
    print(json.dumps({"added": len(added_candidates), "candidate_total": len(candidates["shortlist"]), "message_total": len(messages)}))


if __name__ == "__main__":
    main()
