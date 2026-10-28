#!/usr/bin/env python3
"""Deterministically spot-check final evidence, contact source, and article samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


UA = "Mozilla/5.0 (compatible; FinalOutreachReview/1.0)"


def check_url(url: str, timeout: int) -> dict:
    if not url:
        return {"url": "", "ok": False, "status": None, "error": "missing URL"}
    try:
        with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as response:
            return {"url": response.geturl(), "ok": 200 <= response.status < 400, "status": response.status, "error": ""}
    except Exception as exc:
        return {"url": url, "ok": False, "status": getattr(exc, "code", None), "error": str(exc)[:240]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))["shortlist"]
    indexes = sorted(set(round(i * (len(rows) - 1) / 9) for i in range(10)))
    reviews = []
    for index in indexes:
        row = rows[index]
        contact = row.get("contact_info") or {}
        quality = row.get("quality_checks") or {}
        reviews.append({
            "rank": row.get("rank"), "domain": row.get("normalized_domain"),
            "email": contact.get("recommended_email"), "recipient_fit": contact.get("recipient_fit"),
            "evidence": check_url(row.get("evidence_url") or "", args.timeout),
            "contact_source": check_url(contact.get("recommended_url") or "", args.timeout),
            "sample": check_url((quality.get("sample_urls") or [""])[0], args.timeout),
            "traffic_estimate": quality.get("traffic_estimate"),
            "sample_size": quality.get("sample_size"),
            "technically_indexable_count": quality.get("technically_indexable_count"),
            "dominant_link_attribute": quality.get("dominant_link_attribute"),
            "price_status": "awaiting_quote",
        })
    Path(args.output).write_text(json.dumps(reviews, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "reviewed": len(reviews),
        "evidence_ok": sum(item["evidence"]["ok"] for item in reviews),
        "contact_source_ok": sum(item["contact_source"]["ok"] for item in reviews),
        "sample_ok": sum(item["sample"]["ok"] for item in reviews),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
