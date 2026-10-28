#!/usr/bin/env python3
"""Discover a broad publisher pool through DataForSEO Google organic SERPs."""

from __future__ import annotations

import argparse
import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dataforseo_credentials import get_credentials


ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
EXCLUDED_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "instagram.com", "linkedin.com",
    "pinterest.com", "x.com", "twitter.com", "reddit.com", "wikipedia.org",
    "amazon.com", "ebay.com", "alibaba.com", "quora.com", "medium.com",
}
SEO_KEYS = (
    "topical_relevance", "organic_visibility", "domain_authority",
    "indexation_freshness", "editorial_quality", "contextual_link_potential",
)
GEO_KEYS = (
    "topical_authority", "citation_worthiness", "entity_transparency",
    "discoverability", "content_freshness", "natural_mention_fit",
)


def normalize_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def excluded(domain: str, target_domain: str) -> bool:
    return not domain or domain == target_domain or any(domain == item or domain.endswith(f".{item}") for item in EXCLUDED_DOMAINS)


def components(keys: tuple[str, ...], values: tuple[float | None, ...]) -> dict[str, float | None]:
    return dict(zip(keys, values))


def candidate_from_item(item: dict[str, Any], query: dict[str, Any], today: str) -> dict[str, Any]:
    family = query["family"]
    core = query.get("relevance", "core") == "core"
    explicit = family in {"contribution", "commercial"}
    seo = (4.3, None, None, 3.8, 3.8, 4.2) if core else (3.6, None, None, 3.6, 3.6, 3.5)
    geo = (4.1, 3.9, 3.5, 3.8, 3.7, 4.0) if core else (3.5, 3.6, 3.4, 3.6, 3.5, 3.5)
    url = item.get("url") or ""
    title = item.get("title") or normalize_domain(url)
    return {
        "domain": normalize_domain(url),
        "site_name": title[:160],
        "country_region": query.get("country_region", "International"),
        "language": "English",
        "industry": query["cluster"],
        "pool": "explicit" if explicit else "editorial",
        "discovery_method": "DataForSEO Google organic SERP",
        "discovery_query": query["query"],
        "evidence_url": url,
        "relevance_reason": f"Discovered for {query['cluster']} coverage connected to steel structures, industrial buildings, warehouses, building systems, or adjacent professional audiences.",
        "cooperation_evidence": "Search result indicates a possible contribution or commercial route; direct page inspection required." if explicit else "Editorial publication or organization discovered from a topical publication query; collaboration status requires inspection.",
        "authority_metric": None,
        "metric_source": "",
        "traffic_estimate": None,
        "traffic_source": "",
        "public_price_min_usd": None,
        "public_price_max_usd": None,
        "price_evidence_url": "",
        "seo_components": components(SEO_KEYS, seo),
        "geo_components": components(GEO_KEYS, geo),
        "quality_checks": {
            "traffic_estimate": None,
            "traffic_unit": "estimated monthly organic visits",
            "traffic_source": "unavailable",
            "traffic_scope": "",
            "traffic_checked_at": today,
            "sample_size": 0,
            "indexed_observed_count": 0,
            "technically_indexable_count": 0,
            "index_status": "not_checked",
            "follow_count": 0,
            "nofollow_count": 0,
            "sponsored_count": 0,
            "ugc_count": 0,
            "dominant_link_attribute": "not_observed",
            "sample_urls": [],
            "checked_at": today,
            "confidence": "low",
            "notes": "Broad-discovery candidate; traffic, article samples, and contact route pending.",
        },
        "risk_flags": ["Broad-discovery candidate; direct inspection pending"],
        "hard_exclude_reason": "",
        "last_verified": today,
        "serp_rank": item.get("rank_group") or item.get("rank_absolute"),
        "discovery_sources": [{"query": query["query"], "url": url, "title": title}],
    }


def fetch_serp(task: dict[str, Any], token: str) -> dict[str, Any]:
    request = Request(
        ENDPOINT, data=json.dumps([task]).encode(),
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=180) as response:
        return json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--search-log", required=True)
    parser.add_argument("--usage", required=True)
    parser.add_argument("--target-domain", required=True)
    parser.add_argument("--location-code", type=int, default=2840)
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--depth", type=int, default=50)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    login, password = get_credentials()
    tasks = [{
        "keyword": row["query"], "location_code": args.location_code,
        "language_code": args.language_code, "device": "desktop", "os": "windows",
        "depth": args.depth,
    } for row in queries]
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    by_query = {row["query"]: row for row in queries}
    candidates: dict[str, dict[str, Any]] = {}
    logs = []
    total_cost = 0.0
    today = date.today().isoformat()
    payloads: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_serp, task, token): task["keyword"] for task in tasks}
        for future in as_completed(futures):
            query_text = futures[future]
            try:
                payloads.append(future.result())
            except Exception as exc:
                logs.append({"query": query_text, "source_type": "DataForSEO SERP/error", "results_reviewed": 0, "candidates_kept": 0, "notes": str(exc), "searched_at": today})
            print(f"[{len(payloads) + len(logs)}/{len(tasks)}] {query_text}")

    for payload in payloads:
      for task in payload.get("tasks") or []:
        total_cost += float(task.get("cost") or 0)
        query_text = (task.get("data") or {}).get("keyword") or ""
        query = by_query.get(query_text)
        if not query:
            continue
        if task.get("status_code") != 20000:
            logs.append({"query": query_text, "source_type": "DataForSEO SERP/error", "results_reviewed": 0, "candidates_kept": 0, "notes": f"{task.get('status_code')} {task.get('status_message')}", "searched_at": today})
            continue
        result_sets = task.get("result") or []
        items = result_sets[0].get("items", []) if result_sets else []
        organic = [item for item in items if item.get("type") == "organic"]
        kept = 0
        for item in organic:
            url = item.get("url") or ""
            domain = normalize_domain(url)
            if excluded(domain, args.target_domain):
                continue
            candidate = candidate_from_item(item, query, today)
            existing = candidates.get(domain)
            if existing:
                existing["discovery_sources"].append(candidate["discovery_sources"][0])
                if existing["pool"] == "editorial" and candidate["pool"] == "explicit":
                    candidate["discovery_sources"] = existing["discovery_sources"]
                    candidates[domain] = candidate
            else:
                candidates[domain] = candidate
                kept += 1
        logs.append({
            "query": query_text, "source_type": f"DataForSEO SERP/{query['family']}",
            "results_reviewed": len(organic), "candidates_kept": kept,
            "notes": query["cluster"], "searched_at": today,
        })

    rows = sorted(candidates.values(), key=lambda row: (0 if row["pool"] == "explicit" else 1, -(len(row["discovery_sources"])), row["domain"]))
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.search_log).write_text(json.dumps(logs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    usage = {
        "run_date": today, "dataforseo_serp_endpoint": ENDPOINT,
        "query_count": len(queries), "depth": args.depth,
        "raw_candidates": len(rows), "dataforseo_serp_cost_usd": round(total_cost, 6),
        "location_code": args.location_code, "language_code": args.language_code,
    }
    Path(args.usage).write_text(json.dumps(usage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discovered {len(rows)} unique domains from {len(queries)} queries; cost ${total_cost:.6f}")


if __name__ == "__main__":
    main()
