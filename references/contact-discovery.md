# Public Business Contact Discovery

Use this stage after the broad pool passes the traffic threshold and before the final 30-site email shortlist. Build a surplus of email-qualified candidates, then run deeper article-quality checks on that smaller pool.

## Search order

1. Submission, contributor, write-for-us, editorial, or author-guideline page.
2. Advertising, sponsored-content, media-kit, partnership, or sales page.
3. Public editorial or business email on those pages.
4. Official contact form or general company inbox.
5. Official LinkedIn organization page or WhatsApp business link published by the site.

## Rules

- Capture only channels published on the website itself.
- Store the exact source URL for every result.
- Do not guess emails from names or domain patterns.
- Do not scrape gated directories or personal profiles.
- Prefer a role inbox (`editorial@`, `advertising@`, `partnerships@`) over a named person's address when both are available.
- A page that only contains a form is still a valid contact channel.
- Record `not_found` when no public channel is found; do not invent one.

## Recommended channel

Choose the first available: submission page, editorial email, advertising/partnership email, contact form, general business email, LinkedIn organization page, WhatsApp business link.

The research workbook may retain any public business channel. Automatic Gmail outreach requires a publicly observed business email with a recorded source URL. Mark candidates that only expose a form, LinkedIn page, or WhatsApp link as `其他渠道待接入`; do not pretend they were contacted by email.

## Gmail recipient-fit gate

Apply this gate before message composition:

- `high`: role inbox or named contact explicitly tied to editorial, advertising, partnerships, sponsored content, contributor submissions, or media sales;
- `medium`: general or named business inbox explicitly published on a submission, advertising, sponsorship, media-kit, or partnership page that can route the request;
- `reject`: social-media, events, careers, HR, recruiting, legal, privacy, admissions, circulation, subscriptions, support, billing, warranty, investor-relations, regional, press-only, or unrelated named inbox without evidence that it owns content cooperation. A generic contact page alone does not qualify a general or named inbox for Gmail outreach.

Only `high` and `medium` enter the production-message queue. A named on-domain address discovered on an unrelated landing page is not sufficient evidence. Store rejected contacts and reasons in internal audit data, then continue discovery for replacements. Do not write a message first and mark the recipient for recheck afterward.

Mailbox confirmation, confirmed sender signature, and campaign-level automatic-outreach authorization are separate gates. Once all are recorded in `outreach_state.json`, individual messages do not require review. The authorization never includes payment, acceptance, negotiation, credentials, or contracts.
