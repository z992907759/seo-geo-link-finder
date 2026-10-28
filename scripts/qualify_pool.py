#!/usr/bin/env python3
"""Apply pre-contact traffic and publisher-type gates to a discovery pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DENY_SUFFIXES = {
    "finance.yahoo.com", "pmc.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "ebsco.com",
    "sciencedirect.com", "goodreads.com", "scribd.com", "researchgate.net",
    "crunchbase.com", "springer.com", "link.springer.com", "thriftbooks.com",
    "wiley.com", "onlinelibrary.wiley.com", "mdpi.com", "science.org",
    "tandfonline.com", "rocketreach.co", "content.govdelivery.com", "muckrack.com",
    "semanticscholar.org", "academia.edu", "jstor.org", "sagepub.com", "nature.com",
    "ssrn.com", "arxiv.org", "ieee.org", "books.google.com", "archive.org",
    "issuu.com", "yumpu.com", "fliphtml5.com", "docslib.org", "slideshare.net",
    "feedspot.com", "magazine.feedspot.com", "adsy.com", "linksmanagement.com",
    "buzzstream.com", "seosandwitch.com", "seranking.com", "searchenginejournal.com",
    "searchengineland.com", "ahrefs.com", "semrush.com", "moz.com", "hubspot.com",
    "servicenow.com", "onetonline.org", "iheart.com", "dealstream.com", "upwork.com",
    "fiverr.com", "glassdoor.com", "indeed.com", "ziprecruiter.com", "amazon.com",
    "ebay.com", "etsy.com", "alibaba.com", "walmart.com", "pinterest.com",
    "facebook.com", "linkedin.com", "instagram.com", "youtube.com", "reddit.com",
    "quora.com", "wikipedia.org", "inc.com", "forbes.com", "bloomberg.com",
    "reuters.com", "nytimes.com", "wsj.com", "bbc.com", "cnn.com",
}


def denied(domain: str) -> bool:
    return any(domain == suffix or domain.endswith(f".{suffix}") for suffix in DENY_SUFFIXES)


def qualify(row: dict[str, Any], threshold: float) -> tuple[bool, str]:
    domain = row.get("normalized_domain") or row.get("domain") or ""
    traffic = (row.get("quality_checks") or {}).get("traffic_estimate")
    if traffic is None or float(traffic) < threshold:
        return False, "traffic_below_threshold_or_missing"
    if denied(domain):
        return False, "platform_database_marketplace_or_mass_media"
    if domain.endswith((".gov", ".gov.uk", ".mil")):
        return False, "government_site"
    return True, "qualified_for_contact_research"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--traffic-threshold", type=float, default=1000)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload.get("shortlist", payload) if isinstance(payload, dict) else payload
    kept, audit = [], []
    for row in rows:
        ok, reason = qualify(row, args.traffic_threshold)
        if ok:
            kept.append(row)
        else:
            audit.append({"domain": row.get("normalized_domain") or row.get("domain"), "reason": reason})
    output = dict(payload) if isinstance(payload, dict) else {}
    output["shortlist"] = kept
    output["pre_contact_filter"] = {"traffic_threshold": args.traffic_threshold, "input": len(rows), "kept": len(kept), "excluded": len(audit)}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Qualified {len(kept)} of {len(rows)} domains for contact research")


if __name__ == "__main__":
    main()
