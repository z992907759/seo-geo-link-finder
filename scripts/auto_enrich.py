#!/usr/bin/env python3
"""Fully automatic public traffic and article-sample enrichment for a shortlist."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from site_checks import aggregate_check, fetch_and_inspect, normalize_host


USER_AGENT = "Mozilla/5.0 (compatible; SEOResearchBot/1.0; public-data-check)"
EXCLUDED_PARTS = {
    "about", "contact", "privacy", "terms", "advertise", "advertising", "media-kit",
    "login", "register", "subscribe", "author", "authors", "category", "tag", "search",
    "jobs", "events", "newsletter", "wp-content", "feed", "sitemap", "submission", "submit",
}
EXCLUDED_SUBSTRINGS = (
    "login", "log-in", "sign-in", "privacy", "terms", "cookie", "subscribe",
    "subscription", "newsletter", "advertise", "advertising", "media-kit",
    "mediakit", "contact", "about-us", "write-for-us", "submit", "submission",
    "editorial-calendar", "author-guideline", "for-authors", "sitemap", "search",
)
ARTICLE_MARKERS = ("/article/", "/articles/", "/blog/", "/news/", "/post/", "/posts/", "/features/", "/story/", "/stories/")


def fetch_text(url: str, timeout: int = 15, max_bytes: int = 2_000_000) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        body = response.read(max_bytes).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        return body, response.geturl()


class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = {key.lower(): (value or "") for key, value in attrs}
        href = values.get("href", "").strip()
        if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
            self.links.append(urljoin(self.base_url, href).split("#", 1)[0])


def is_article_url(url: str, domain: str) -> bool:
    parsed = urlsplit(url)
    if normalize_host(url) != domain:
        return False
    path = parsed.path.strip("/")
    if not path or path.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip")):
        return False
    parts = [part.lower() for part in path.split("/") if part]
    if any(part in EXCLUDED_PARTS for part in parts):
        return False
    lower_path = f"/{path.lower()}/"
    if any(token in lower_path for token in EXCLUDED_SUBSTRINGS):
        return False
    last = parts[-1]
    looks_like_article = any(marker in lower_path for marker in ARTICLE_MARKERS) or any(f"/{year}/" in lower_path for year in ("2024", "2025", "2026")) or last.count("-") >= 4
    return looks_like_article and len(last) >= 12


def rank_article_url(url: str) -> tuple[int, int, str]:
    lower = url.lower()
    preferred = any(token in lower for token in ("guest", "contributor", "sponsored", "partner-content", "expert"))
    year = 2026 if "/2026/" in lower else 2025 if "/2025/" in lower else 0
    return (1 if preferred else 0, year, url)


def discover_samples(domain: str, evidence_url: str, limit: int, timeout: int) -> list[str]:
    root = f"https://{domain}/"
    candidates: set[str] = set()
    for url in (root, evidence_url):
        try:
            html, final_url = fetch_text(url, timeout)
        except Exception:
            continue
        parser = LinkParser(final_url)
        parser.feed(html)
        candidates.update(link for link in parser.links if is_article_url(link, domain))

    if len(candidates) < limit:
        for feed_url in (urljoin(root, "feed/"), urljoin(root, "rss/"), urljoin(root, "sitemap.xml")):
            try:
                text, _ = fetch_text(feed_url, timeout)
            except Exception:
                continue
            for match in re.findall(r"<loc>(.*?)</loc>|<link>(https?://.*?)</link>", text, flags=re.I | re.S):
                found = next((item.strip() for item in match if item.strip()), "")
                if found and is_article_url(found, domain):
                    candidates.add(found)
            if len(candidates) >= limit * 3:
                break

    ordered = sorted(candidates, key=rank_article_url, reverse=True)
    return ordered[:limit]


def public_traffic(domain: str, timeout: int) -> dict[str, Any]:
    source_url = f"https://sitefigures.com/site/{domain}"
    html, _ = fetch_text(source_url, timeout)
    scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.I | re.S)
    for script in scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        nodes = payload.get("@graph", []) if isinstance(payload, dict) else []
        for node in nodes:
            if node.get("@type") != "Dataset":
                continue
            values = {item.get("name"): item.get("value") for item in node.get("variableMeasured", [])}
            visitors = values.get("Estimated monthly visitors")
            pageviews = values.get("Estimated monthly page views")
            if visitors is not None:
                confidence_match = re.search(r'id="score-value"[^>]*>([0-9.]+)<', html)
                return {
                    "traffic_estimate": int(visitors),
                    "traffic_unit": "estimated monthly total visitors",
                    "traffic_source": "Site Figures public estimate",
                    "traffic_scope": "global total traffic; not organic-only",
                    "traffic_checked_at": date.today().isoformat(),
                    "traffic_source_url": source_url,
                    "estimated_pageviews": int(pageviews) if pageviews is not None else None,
                    "traffic_confidence_score": float(confidence_match.group(1)) if confidence_match else None,
                }
    raise ValueError("traffic dataset not found")


def enrich_row(row: dict[str, Any], sample_limit: int, timeout: int) -> dict[str, Any]:
    result = dict(row)
    domain = row.get("normalized_domain") or row.get("domain")
    checks = dict(row.get("quality_checks", {}))
    if not str(checks.get("traffic_source", "")).startswith("DataForSEO"):
        try:
            checks.update(public_traffic(domain, timeout))
        except Exception as exc:
            checks["traffic_source"] = "unavailable"
            checks["traffic_error"] = str(exc)

    sample_urls = discover_samples(domain, row.get("evidence_url", ""), sample_limit, timeout)
    samples = [fetch_and_inspect({"url": url, "search_observation": "unknown"}, timeout) for url in sample_urls]
    aggregate = aggregate_check(domain, checks, samples, date.today().isoformat())
    for key in (
        "traffic_estimate", "traffic_unit", "traffic_source", "traffic_scope",
        "traffic_checked_at", "traffic_source_url", "estimated_pageviews",
        "traffic_confidence_score", "traffic_error", "public_audience_note",
    ):
        if key in checks:
            aggregate[key] = checks[key]
    aggregate["sample_discovery"] = "automatic: home page, evidence page, RSS, sitemap"
    aggregate["sample_type_note"] = "Prioritizes guest/contributor/sponsored URL patterns; otherwise uses recent editorial article samples."
    result["quality_checks"] = aggregate
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload.get("shortlist") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("input must be a shortlist payload or JSON array")
    enriched: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(enrich_row, row, args.samples, args.timeout): index for index, row in enumerate(rows)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                enriched[index] = future.result()
            except Exception as exc:
                fallback = dict(rows[index])
                checks = dict(fallback.get("quality_checks", {}))
                checks["notes"] = f"automatic enrichment failed: {exc}"
                fallback["quality_checks"] = checks
                enriched[index] = fallback
            print(f"[{index + 1}/{len(rows)}] {rows[index].get('normalized_domain') or rows[index].get('domain')}")
    if isinstance(payload, dict):
        payload["shortlist"] = enriched
        output = payload
    else:
        output = enriched
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Enriched {len(rows)} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
