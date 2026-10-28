#!/usr/bin/env python3
"""Discover public business contact channels for shortlisted publisher domains."""

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


UA = "Mozilla/5.0 (compatible; PublicBusinessContactResearch/1.0)"
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
KEYWORDS = ("contact", "advertis", "sponsor", "media-kit", "media_kit", "write-for-us", "contribut", "submit", "editor", "partner", "press")
HIGH_ROLE_PARTS = ("editor", "editorial", "content", "advert", "media", "partner", "sponsor")
GENERAL_ROLE_PARTS = ("info", "hello", "contact", "office", "admin", "marketing", "sales", "enquir", "inquir")
REJECT_ROLE_PARTS = (
    "social", "event", "career", "jobs", "support", "billing", "privacy", "legal",
    "webmaster", "noreply", "no-reply", "recruit", "humanresources", "human.resources",
    "admission", "enrollment", "student", "circulation", "subscription", "warranty",
    "accounts", "payable", "investor", "press", "china",
)


class ContactParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self.forms: list[str] = []
        self.text: list[str] = []
        self._anchor_href = ""
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "a":
            self._anchor_href = values.get("href", "")
            self._anchor_text = []
        elif tag.lower() == "form":
            self.forms.append(urljoin(self.base_url, values.get("action", "") or self.base_url))

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.text.append(cleaned)
            if self._anchor_href:
                self._anchor_text.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor_href:
            self.links.append((urljoin(self.base_url, self._anchor_href), " ".join(self._anchor_text)))
            self._anchor_href = ""
            self._anchor_text = []


def host(url: str) -> str:
    value = (urlsplit(url).hostname or "").lower()
    return value[4:] if value.startswith("www.") else value


def fetch(url: str, timeout: int) -> tuple[str, str]:
    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=timeout) as response:
        return response.read(750_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace"), response.geturl()


def page_kind(url: str, text: str) -> str:
    value = f"{url} {text}".lower()
    if any(key in value for key in ("write-for-us", "contribut", "submit", "editorial", "for-authors", "guest-post")):
        return "submission"
    if any(key in value for key in ("advertis", "sponsor", "media-kit", "media_kit", "partnership")):
        return "advertising"
    return "contact"


def assess_recipient_fit(email: str, source_url: str, aligned_pages: set[str]) -> tuple[str, str]:
    local = email.rsplit("@", 1)[0].lower()
    if local in {"hr", "h.r", "human_resources", "human-resources"} or any(part in local for part in REJECT_ROLE_PARTS):
        return "reject", "Mailbox role is unrelated to editorial, advertising, sponsorship, partnerships, or content cooperation."
    if any(part in local for part in HIGH_ROLE_PARTS):
        return "high", "Role mailbox explicitly matches editorial, media, advertising, sponsorship, or partnerships."
    aligned = source_url in aligned_pages
    if aligned and any(part in local for part in GENERAL_ROLE_PARTS):
        return "medium", "General on-domain mailbox is published on a relevant submission, advertising, or contact page."
    if aligned and re.fullmatch(r"[a-z][a-z0-9._-]{1,40}", local):
        return "medium", "Named on-domain mailbox is published on a relevant submission, advertising, or contact page."
    return "reject", "The public source does not establish that this mailbox can route content cooperation."


def discover(row: dict[str, Any], timeout: int) -> dict[str, Any]:
    domain = row.get("normalized_domain") or row.get("domain")
    root = f"https://{domain}/"
    seeds = [root, row.get("evidence_url", "")]
    pages: dict[str, str] = {}
    parsed: list[tuple[str, ContactParser, str]] = []
    for seed in seeds:
        if not seed or seed in pages:
            continue
        try:
            html, final = fetch(seed, timeout)
        except Exception:
            continue
        pages[final] = html
        parser = ContactParser(final); parser.feed(html)
        parsed.append((final, parser, html))
        for link, label in parser.links:
            if host(link) == domain and any(key in f"{link} {label}".lower() for key in KEYWORDS):
                pages.setdefault(link, "")

    for url in list(pages)[:8]:
        if pages[url]:
            continue
        try:
            html, final = fetch(url, timeout)
        except Exception:
            continue
        parser = ContactParser(final); parser.feed(html)
        parsed.append((final, parser, html))

    emails: dict[str, str] = {}
    submission: list[str] = []
    advertising: list[str] = []
    contact_pages: list[str] = []
    forms: list[str] = []
    linkedin: list[str] = []
    whatsapp: list[str] = []
    for url, parser, html in parsed:
        kind = page_kind(url, " ".join(parser.text[:80]))
        if kind == "submission": submission.append(url)
        elif kind == "advertising": advertising.append(url)
        elif any(key in url.lower() for key in ("contact", "about")): contact_pages.append(url)
        for email in EMAIL_RE.findall(html.replace("[at]", "@").replace("(at)", "@")):
            email = email.lower().strip(".,;:")
            email_domain = email.rsplit("@", 1)[-1]
            if not email.endswith(("example.com", "sentry.io")) and not email_domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")):
                emails.setdefault(email, url)
        forms.extend(parser.forms)
        for link, _ in parser.links:
            lower = link.lower()
            if "linkedin.com/company/" in lower: linkedin.append(link)
            if "wa.me/" in lower or "api.whatsapp.com/" in lower: whatsapp.append(link)

    def unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    submission, advertising, contact_pages, forms, linkedin, whatsapp = map(unique, (submission, advertising, contact_pages, forms, linkedin, whatsapp))
    role_emails = sorted(emails, key=lambda value: (0 if any(role in value for role in HIGH_ROLE_PARTS) else 1, value))
    # A generic contact page is useful research evidence but does not, by itself,
    # establish that a general or named inbox owns content cooperation.
    aligned_pages = set(submission + advertising)
    assessed = []
    for email in role_emails:
        fit, reason = assess_recipient_fit(email, emails[email], aligned_pages)
        assessed.append({"email": email, "source_url": emails[email], "fit": fit, "reason": reason})
    eligible = sorted((item for item in assessed if item["fit"] in {"high", "medium"}), key=lambda item: (0 if item["fit"] == "high" else 1, item["email"]))
    recommended = eligible[0] if eligible else None
    recommended_email = recommended["email"] if recommended else ""
    if submission: channel = "投稿/编辑页面"
    elif role_emails and any(key in role_emails[0] for key in ("editor", "content")): channel = "编辑邮箱"
    elif advertising: channel = "广告/合作页面"
    elif role_emails: channel = "公开业务邮箱"
    elif forms: channel = "联系表单"
    elif linkedin: channel = "LinkedIn"
    elif whatsapp: channel = "WhatsApp"
    else: channel = "未找到"
    sources = unique(submission + advertising + contact_pages + list(emails.values()))
    confidence = "high" if (submission or advertising or role_emails) else "medium" if (forms or linkedin or whatsapp) else "low"
    result = dict(row)
    result["contact_info"] = {
        "recommended_channel": channel,
        "recommended_email": recommended_email,
        "recipient_fit": recommended["fit"] if recommended else "reject",
        "recipient_fit_reason": recommended["reason"] if recommended else "No public email passed the role-and-source gate.",
        "recommended_url": (submission or advertising or forms or contact_pages or linkedin or whatsapp or [""])[0],
        "department": "编辑/内容" if submission else "商务合作" if advertising else "综合咨询",
        "emails": role_emails[:8],
        "email_assessments": assessed[:12],
        "submission_pages": submission[:5],
        "advertising_pages": advertising[:5],
        "contact_pages": contact_pages[:5],
        "forms": forms[:5],
        "linkedin_pages": linkedin[:3],
        "whatsapp_links": whatsapp[:3],
        "source_urls": sources[:10],
        "confidence": confidence,
        "checked_at": date.today().isoformat(),
        "notes": "Public business channels only; no inferred addresses.",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = payload["shortlist"]
    output_rows: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(discover, row, args.timeout): i for i, row in enumerate(rows)}
        for future in as_completed(futures):
            i = futures[future]
            try: output_rows[i] = future.result()
            except Exception as exc:
                fallback = dict(rows[i]); fallback["contact_info"] = {"recommended_channel":"未找到","department":"","emails":[],"submission_pages":[],"advertising_pages":[],"contact_pages":[],"forms":[],"linkedin_pages":[],"whatsapp_links":[],"source_urls":[],"confidence":"low","checked_at":date.today().isoformat(),"notes":str(exc)}; output_rows[i] = fallback
            print(f"[{i+1}/{len(rows)}] {rows[i].get('normalized_domain') or rows[i].get('domain')}", flush=True)
    payload["shortlist"] = output_rows
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
