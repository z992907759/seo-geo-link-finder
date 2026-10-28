#!/usr/bin/env python3
"""Inspect supplied article samples for technical indexability and outbound link attributes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


def normalize_host(value: str) -> str:
    host = (urlsplit(value).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.base_host = normalize_host(base_url)
        self.noindex = False
        self.canonical = ""
        self.external_attributes: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "meta" and attributes.get("name", "").lower() in {"robots", "googlebot"}:
            directives = {item.strip().lower() for item in attributes.get("content", "").split(",")}
            if "noindex" in directives or "none" in directives:
                self.noindex = True
        if tag.lower() == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = urljoin(self.base_url, attributes.get("href", ""))
        if tag.lower() != "a":
            return
        href = attributes.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return
        absolute = urljoin(self.base_url, href)
        target_host = normalize_host(absolute)
        if not target_host or target_host == self.base_host:
            return
        rel = {item.strip().lower() for item in attributes.get("rel", "").split() if item.strip()}
        if "sponsored" in rel:
            label = "sponsored"
        elif "ugc" in rel:
            label = "ugc"
        elif "nofollow" in rel:
            label = "nofollow"
        else:
            label = "follow"
        self.external_attributes[label] += 1


def inspect_html(html: str, base_url: str, status: int = 200, headers: dict[str, str] | None = None) -> dict[str, Any]:
    parser = PageParser(base_url)
    parser.feed(html)
    header_map = {key.lower(): value for key, value in (headers or {}).items()}
    x_robots = header_map.get("x-robots-tag", "").lower()
    header_noindex = "noindex" in x_robots or "none" in x_robots
    technical_indexable = 200 <= status < 300 and not parser.noindex and not header_noindex
    canonical_host = normalize_host(parser.canonical) if parser.canonical else ""
    canonical_ok = not canonical_host or canonical_host == normalize_host(base_url)
    return {
        "url": base_url,
        "http_status": status,
        "noindex": parser.noindex or header_noindex,
        "canonical": parser.canonical,
        "canonical_ok": canonical_ok,
        "technically_indexable": technical_indexable and canonical_ok,
        "follow_count": parser.external_attributes["follow"],
        "nofollow_count": parser.external_attributes["nofollow"],
        "sponsored_count": parser.external_attributes["sponsored"],
        "ugc_count": parser.external_attributes["ugc"],
    }


def fetch_and_inspect(sample: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = sample["url"]
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SEOQualityCheck/1.0)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
            result = inspect_html(body, response.geturl(), int(response.status), dict(response.headers.items()))
    except Exception as exc:  # Network and publisher behavior are recorded, not hidden.
        result = {
            "url": url,
            "http_status": None,
            "noindex": None,
            "canonical": "",
            "canonical_ok": None,
            "technically_indexable": False,
            "follow_count": 0,
            "nofollow_count": 0,
            "sponsored_count": 0,
            "ugc_count": 0,
            "fetch_error": str(exc),
        }
    result["search_observation"] = sample.get("search_observation", "unknown")
    result["search_engine"] = sample.get("search_engine", "")
    result["search_checked_at"] = sample.get("search_checked_at", "")
    return result


def aggregate_check(domain: str, traffic: dict[str, Any], samples: list[dict[str, Any]], checked_at: str) -> dict[str, Any]:
    sample_size = len(samples)
    technical = sum(result.get("technically_indexable") is True for result in samples)
    indexed = sum(result.get("search_observation") == "indexed" for result in samples)
    not_found = sum(result.get("search_observation") == "not_found" for result in samples)
    counts = {
        name: sum(int(result.get(f"{name}_count") or 0) for result in samples)
        for name in ("follow", "nofollow", "sponsored", "ugc")
    }
    if sample_size == 0:
        index_status = "not_checked"
    elif sample_size < 3:
        index_status = "insufficient_samples"
    elif technical == 0:
        index_status = "technically_blocked"
    elif indexed == sample_size:
        index_status = "indexed"
    elif indexed > 0:
        index_status = "partially_indexed"
    elif not_found == sample_size:
        index_status = "not_found"
    else:
        index_status = "not_checked"
    dominant = max(counts, key=counts.get) if any(counts.values()) else "not_observed"
    traffic_source = traffic.get("traffic_source", "unavailable")
    if sample_size >= 5 and traffic_source != "unavailable":
        confidence = "high"
    elif sample_size >= 3:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "domain": domain,
        "traffic_estimate": traffic.get("traffic_estimate"),
        "traffic_unit": traffic.get("traffic_unit", "monthly organic visits"),
        "traffic_source": traffic_source,
        "traffic_scope": traffic.get("traffic_scope", ""),
        "traffic_checked_at": traffic.get("traffic_checked_at", checked_at),
        "public_audience_note": traffic.get("public_audience_note", ""),
        "sample_size": sample_size,
        "indexed_observed_count": indexed,
        "technically_indexable_count": technical,
        "index_status": index_status,
        "follow_count": counts["follow"],
        "nofollow_count": counts["nofollow"],
        "sponsored_count": counts["sponsored"],
        "ugc_count": counts["ugc"],
        "dominant_link_attribute": dominant,
        "sample_urls": [result["url"] for result in samples],
        "sample_results": samples,
        "checked_at": checked_at,
        "confidence": confidence,
        "notes": traffic.get("notes", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="JSON array of domains, traffic data, and sample URLs")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    checked_at = date.today().isoformat()
    output = []
    for entry in plan:
        samples = [fetch_and_inspect(sample, args.timeout) for sample in entry.get("samples", [])]
        output.append(aggregate_check(entry["domain"], entry.get("traffic", {}), samples, checked_at))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(output)} domains and {sum(item['sample_size'] for item in output)} sample pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
