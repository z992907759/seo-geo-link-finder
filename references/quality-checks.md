# Traffic, Indexation, and Link-Attribute Checks

Run these checks after broad discovery and before the final shortlist.

## 1. Traffic

Use an already-authorized Ahrefs, Semrush, or equivalent account when available. Record the exact provider, database/country scope, value, unit, and check date. Keep provider metrics separate because they are estimates and are not directly interchangeable.

If no SEO tool is available:

- set `traffic_source` to `unavailable` and leave `traffic_estimate` null;
- optionally record a clearly labeled public audience figure from a current media kit or publisher page;
- use `auto_enrich.py` to request a public directional total-traffic estimate when the configured public source is reachable;
- never transform readership, newsletter circulation, or page views into organic traffic.

Public total-traffic estimates must be labeled as total visits and must not be presented as Ahrefs/Semrush-style organic traffic.

## 2. Article sample

Find 3–5 recent pages that best represent the placement being considered. Prefer guest, contributor, sponsored, partner, expert-column, or externally authored articles. Do not use a submission, advertise, category, or home page as a placement sample.

Record every sample URL. If fewer than three suitable pages can be found, use the available pages and mark `insufficient_samples`.

## 3. Technical indexability

For each sample, check:

- HTTP success status;
- absence of `noindex` in meta robots or `X-Robots-Tag`;
- a sensible canonical URL;
- publicly readable textual content.

Technical eligibility is not proof of search-engine indexation.

## 4. Search-result observation

Search the exact URL and a distinctive exact-title query. Record `indexed` only when the page is observed in current search results. Record `not_found` when it is not observed, with the check date and engine. Do not claim `not indexed`: search operators are not exhaustive for third-party sites.

Aggregate a sample as:

- `indexed`: all checked samples observed;
- `partially_indexed`: at least one but not all observed;
- `not_found`: none observed and pages remain technically eligible;
- `technically_blocked`: samples contain blocking technical signals;
- `insufficient_samples`: fewer than three suitable pages;
- `not_checked`: no usable sample.

## 5. Link attributes

Inspect external content links in the article HTML. Classify each link once, using this precedence:

1. `sponsored` when `rel` contains `sponsored`;
2. `ugc` when `rel` contains `ugc`;
3. `nofollow` when `rel` contains `nofollow`;
4. `follow` when none of those attributes are present.

Report counts and the dominant observed attribute. This describes the sampled pages only; it is not a guarantee of the terms a publisher will offer later.

## 6. Missing evidence

Keep candidates with insufficient article samples when they are otherwise relevant and record the lower confidence. For an automatic-outreach campaign whose configured hard gate requires DataForSEO monthly organic traffic of at least 1,000, a missing or lower traffic value does not enter the send queue. It may remain in internal audit data, but the workflow must continue discovering replacements rather than contacting it.
