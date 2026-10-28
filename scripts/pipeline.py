#!/usr/bin/env python3
"""Deterministic scoring, price calibration, validation, and shortlist selection."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit


SEO_WEIGHTS = {
    "topical_relevance": 30,
    "organic_visibility": 20,
    "domain_authority": 15,
    "indexation_freshness": 15,
    "editorial_quality": 10,
    "contextual_link_potential": 10,
}

GEO_WEIGHTS = {
    "topical_authority": 25,
    "citation_worthiness": 25,
    "entity_transparency": 15,
    "discoverability": 15,
    "content_freshness": 10,
    "natural_mention_fit": 10,
}

REQUIRED_CAMPAIGN_FIELDS = (
    "campaign_name",
    "target_site",
    "target_markets",
    "languages",
    "target_price_usd",
    "max_price_usd",
)

REQUIRED_CANDIDATE_FIELDS = (
    "domain",
    "site_name",
    "country_region",
    "language",
    "industry",
    "pool",
    "discovery_method",
    "discovery_query",
    "evidence_url",
    "relevance_reason",
    "cooperation_evidence",
    "seo_components",
    "geo_components",
    "quality_checks",
    "risk_flags",
    "last_verified",
)


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_domain(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = re.split(r"[（(]", raw, maxsplit=1)[0].strip()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        hostname = (urlsplit(candidate).hostname or "").rstrip(".")
    except ValueError:
        return ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    except ValueError:
        return raw.lower().rstrip("/")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+", "/", parsed.path or "/").rstrip("/")
    return f"{host}{path}".rstrip("/")


def parse_price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) and float(value) > 0 else None
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)", str(value).replace(",", ""))
    if not match:
        return None
    number = float(match.group(1))
    return number if number > 0 else None


def numeric(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def weighted_score(components: dict[str, Any], weights: dict[str, int]) -> tuple[int | None, str, int]:
    weighted_sum = 0.0
    available_weight = 0
    for name, weight in weights.items():
        value = numeric(components.get(name))
        if value is None:
            continue
        if value < 0 or value > 5:
            raise ValueError(f"component {name!r} must be between 0 and 5")
        weighted_sum += value / 5 * weight
        available_weight += weight
    if available_weight == 0:
        return None, "low", 0
    score = round(weighted_sum / available_weight * 100)
    heaviest = max(weights, key=weights.get)
    heaviest_verified = numeric(components.get(heaviest)) is not None
    if available_weight >= 80 and heaviest_verified:
        confidence = "high"
    elif available_weight >= 55:
        confidence = "medium"
    else:
        confidence = "low"
    return score, confidence, available_weight


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate percentile of an empty list")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def price_range(values: Iterable[float]) -> tuple[int, int]:
    cleaned = sorted(float(value) for value in values if value and value > 0)
    if not cleaned:
        raise ValueError("no price values")
    low = round(percentile(cleaned, 0.25))
    high = round(percentile(cleaned, 0.75))
    return min(low, high), max(low, high)


def history_prices(history: list[dict[str, Any]]) -> list[float]:
    result: list[float] = []
    for row in history:
        value = numeric(row.get("price_usd")) or parse_price(row.get("price_raw"))
        if value is not None:
            result.append(value)
    return result


def calibrate_price(candidate: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    public_min = numeric(candidate.get("public_price_min_usd"))
    public_max = numeric(candidate.get("public_price_max_usd"))
    if public_min is not None or public_max is not None:
        low = public_min if public_min is not None else public_max
        high = public_max if public_max is not None else public_min
        return {
            "price_min_usd": round(min(low, high)),
            "price_max_usd": round(max(low, high)),
            "price_basis": "public",
            "price_confidence": "high",
        }

    domain = candidate["normalized_domain"]
    same_domain = []
    for row in history:
        if normalize_domain(row.get("domain") or row.get("original_domain_raw")) == domain:
            price = numeric(row.get("price_usd")) or parse_price(row.get("price_raw"))
            if price is not None:
                same_domain.append(price)
    if same_domain:
        return {
            "price_min_usd": round(min(same_domain)),
            "price_max_usd": round(max(same_domain)),
            "price_basis": "same_domain_history",
            "price_confidence": "medium",
        }

    category = str(candidate.get("industry") or "").strip().lower()
    candidate_authority = numeric(candidate.get("authority_metric"))
    peers = []
    for row in history:
        row_category = str(row.get("category") or "").strip().lower()
        price = numeric(row.get("price_usd")) or parse_price(row.get("price_raw"))
        row_authority = numeric(row.get("authority_metric_raw"))
        category_match = category and row_category and (
            category in row_category or row_category in category
        )
        authority_match = (
            candidate_authority is None
            or row_authority is None
            or abs(candidate_authority - row_authority) <= 10
        )
        if price is not None and category_match and authority_match:
            peers.append(price)
    if len(peers) >= 2:
        low, high = price_range(peers)
        return {
            "price_min_usd": low,
            "price_max_usd": high,
            "price_basis": "historical_peer",
            "price_confidence": "low",
        }

    global_prices = history_prices(history)
    if global_prices:
        low, high = price_range(global_prices)
        return {
            "price_min_usd": low,
            "price_max_usd": high,
            "price_basis": "historical_global",
            "price_confidence": "low",
        }
    return {
        "price_min_usd": None,
        "price_max_usd": None,
        "price_basis": "unknown",
        "price_confidence": "low",
    }


def focus_score(seo_score: int | None, geo_score: int | None, focus: str) -> int | None:
    if focus == "seo":
        return seo_score
    if focus == "geo":
        return geo_score
    available = [score for score in (seo_score, geo_score) if score is not None]
    return round(statistics.mean(available)) if available else None


def validate_campaign(campaign: dict[str, Any]) -> list[str]:
    issues = [f"campaign missing {field}" for field in REQUIRED_CAMPAIGN_FIELDS if campaign.get(field) in (None, "", [])]
    if campaign.get("focus", "balanced") not in {"seo", "geo", "balanced"}:
        issues.append("campaign focus must be seo, geo, or balanced")
    target = numeric(campaign.get("target_price_usd"))
    ceiling = numeric(campaign.get("max_price_usd"))
    if target is not None and ceiling is not None and target > ceiling:
        issues.append("target_price_usd cannot exceed max_price_usd")
    return issues


def validate_candidate(candidate: dict[str, Any], index: int) -> list[str]:
    issues = [f"candidate {index}: missing {field}" for field in REQUIRED_CANDIDATE_FIELDS if field not in candidate]
    if candidate.get("pool") not in {"explicit", "editorial"}:
        issues.append(f"candidate {index}: pool must be explicit or editorial")
    if not normalize_domain(candidate.get("domain")):
        issues.append(f"candidate {index}: domain is invalid")
    for group_name, weights in (("seo_components", SEO_WEIGHTS), ("geo_components", GEO_WEIGHTS)):
        group = candidate.get(group_name)
        if not isinstance(group, dict):
            issues.append(f"candidate {index}: {group_name} must be an object")
            continue
        unknown = set(group) - set(weights)
        if unknown:
            issues.append(f"candidate {index}: unknown {group_name} fields: {sorted(unknown)}")
    checks = candidate.get("quality_checks")
    if not isinstance(checks, dict):
        issues.append(f"candidate {index}: quality_checks must be an object")
    else:
        for field in ("traffic_source", "index_status", "dominant_link_attribute", "sample_size", "sample_urls"):
            if field not in checks:
                issues.append(f"candidate {index}: quality_checks missing {field}")
    return issues


def enrich_candidate(candidate: dict[str, Any], campaign: dict[str, Any], history: list[dict[str, Any]], purchased_urls: set[str]) -> dict[str, Any]:
    result = dict(candidate)
    result["normalized_domain"] = normalize_domain(candidate.get("domain"))
    result["normalized_evidence_url"] = normalize_url(candidate.get("evidence_url"))
    result["quality_checks"] = dict(candidate.get("quality_checks", {}))

    seo_score, seo_confidence, seo_coverage = weighted_score(candidate.get("seo_components", {}), SEO_WEIGHTS)
    geo_score, geo_confidence, geo_coverage = weighted_score(candidate.get("geo_components", {}), GEO_WEIGHTS)
    result.update(
        seo_score=seo_score,
        seo_confidence=seo_confidence,
        seo_evidence_coverage=seo_coverage,
        geo_score=geo_score,
        geo_confidence=geo_confidence,
        geo_evidence_coverage=geo_coverage,
    )

    history_rows = [
        row for row in history
        if normalize_domain(row.get("domain") or row.get("original_domain_raw")) == result["normalized_domain"]
    ]
    result["purchased_before"] = bool(history_rows)
    historical_values = [
        numeric(row.get("price_usd")) or parse_price(row.get("price_raw"))
        for row in history_rows
    ]
    historical_values = [value for value in historical_values if value is not None]
    result["previous_price_usd"] = round(statistics.median(historical_values)) if historical_values else None
    result["exact_placement_duplicate"] = bool(result["normalized_evidence_url"] and result["normalized_evidence_url"] in purchased_urls)
    result.update(calibrate_price(result, history))

    focus = campaign.get("focus", "balanced")
    result["focus_score"] = focus_score(seo_score, geo_score, focus)
    if result.get("hard_exclude_reason"):
        result["recommendation"] = "排除"
    elif result["focus_score"] is not None and result["focus_score"] >= 75:
        result["recommendation"] = "优先"
    elif result["focus_score"] is not None and result["focus_score"] >= 60:
        result["recommendation"] = "值得评估"
    else:
        result["recommendation"] = "补充候选"
    return result


def process(campaign: dict[str, Any], candidates: list[dict[str, Any]], history: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    issues = validate_campaign(campaign)
    for index, candidate in enumerate(candidates, start=1):
        issues.extend(validate_candidate(candidate, index))
    if issues:
        raise ValueError("; ".join(issues))

    purchased_urls = {
        normalize_url(row.get("placement_url"))
        for row in history
        if normalize_url(row.get("placement_url"))
    }
    enriched = [enrich_candidate(candidate, campaign, history, purchased_urls) for candidate in candidates]

    excluded: list[dict[str, Any]] = []
    eligible_by_domain: dict[str, dict[str, Any]] = {}
    for candidate in enriched:
        reason = candidate.get("hard_exclude_reason")
        if candidate.get("exact_placement_duplicate"):
            reason = reason or "exact historical placement URL"
        if reason:
            candidate["exclusion_reason"] = reason
            excluded.append(candidate)
            continue
        domain = candidate["normalized_domain"]
        current = eligible_by_domain.get(domain)
        if current is None or (candidate.get("focus_score") or -1) > (current.get("focus_score") or -1):
            if current is not None:
                current["exclusion_reason"] = "lower-ranked duplicate domain"
                excluded.append(current)
            eligible_by_domain[domain] = candidate
        else:
            candidate["exclusion_reason"] = "lower-ranked duplicate domain"
            excluded.append(candidate)

    pool_order = {"explicit": 0, "editorial": 1}
    eligible = list(eligible_by_domain.values())
    eligible.sort(
        key=lambda item: (
            -(item.get("focus_score") if item.get("focus_score") is not None else -1),
            pool_order.get(item.get("pool"), 9),
            item.get("price_max_usd") if item.get("price_max_usd") is not None else 10**9,
            item["normalized_domain"],
        )
    )
    shortlist = eligible[:limit]
    for rank, candidate in enumerate(shortlist, start=1):
        candidate["rank"] = rank

    return {
        "campaign_name": campaign["campaign_name"],
        "raw_candidate_count": len(candidates),
        "unique_eligible_count": len(eligible),
        "shortlist_count": len(shortlist),
        "shortlist": shortlist,
        "not_shortlisted": eligible[limit:],
        "excluded": excluded,
        "gap_note": "" if len(candidates) >= 90 else f"Only {len(candidates)} raw candidates were evaluated; target is 90.",
    }


def command_process(args: argparse.Namespace) -> int:
    campaign = read_json(args.campaign)
    candidates = read_json(args.candidates)
    history = read_json(args.history)
    if not isinstance(candidates, list) or not isinstance(history, list):
        raise ValueError("candidates and history must be JSON arrays")
    output = process(campaign, candidates, history, args.limit)
    write_json(args.output, output)
    print(
        f"Processed {output['raw_candidate_count']} raw candidates; "
        f"selected {output['shortlist_count']} and excluded {len(output['excluded'])}."
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    payload = read_json(args.shortlist)
    shortlist = payload.get("shortlist") if isinstance(payload, dict) else None
    if not isinstance(shortlist, list):
        raise ValueError("shortlist payload must contain a shortlist array")
    issues = []
    seen_domains = set()
    for index, row in enumerate(shortlist, start=1):
        domain = row.get("normalized_domain")
        if not domain:
            issues.append(f"row {index}: missing normalized_domain")
        if domain in seen_domains:
            issues.append(f"row {index}: duplicate domain {domain}")
        seen_domains.add(domain)
        if not row.get("evidence_url"):
            issues.append(f"row {index}: missing evidence_url")
        if row.get("seo_score") is None or row.get("geo_score") is None:
            issues.append(f"row {index}: missing SEO or GEO score")
        if row.get("price_basis") not in {"public", "same_domain_history", "historical_peer", "historical_global", "unknown"}:
            issues.append(f"row {index}: invalid price basis")
        checks = row.get("quality_checks")
        if not isinstance(checks, dict):
            issues.append(f"row {index}: missing quality_checks")
        elif checks.get("traffic_source") in (None, "") or checks.get("index_status") in (None, "") or checks.get("dominant_link_attribute") in (None, ""):
            issues.append(f"row {index}: incomplete traffic/index/link checks")
    if issues:
        raise ValueError("; ".join(issues))
    print(f"Valid shortlist: {len(shortlist)} unique candidates with evidence and scores.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="score and select candidates")
    process_parser.add_argument("--campaign", required=True)
    process_parser.add_argument("--candidates", required=True)
    process_parser.add_argument("--history", required=True)
    process_parser.add_argument("--output", required=True)
    process_parser.add_argument("--limit", type=int, default=30)
    process_parser.set_defaults(func=command_process)

    validate_parser = subparsers.add_parser("validate", help="validate a shortlist JSON file")
    validate_parser.add_argument("--shortlist", required=True)
    validate_parser.set_defaults(func=command_validate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
