---
name: seo-geo-link-finder
description: Discover and qualify SEO/GEO backlink publishers, find public business contacts, run authorized Gmail outreach, monitor replies and quotes, and update an Excel handoff. Use for supervised campaign setup followed by automatic prospecting and email outreach; never purchase placements or make payment commitments.
---

# SEO/GEO Link Finder and Outreach

Run an evidence-backed backlink campaign from discovery through reply and quote collection. Historical purchases calibrate duplicate and price signals; they are never the primary discovery source.

## Start with the mailbox gate

Before researching prospects or reading mailbox content, inspect the installed Gmail connector and retrieve the authenticated mailbox address and available read, draft, send, and thread-search actions. Do not ask for or store a Gmail password, OAuth token, cookie, or API credential.

Show the exact detected From address and any available send-as alias. Separately ask the user to confirm the public sender display name and complete closing signature; never infer them from the Gmail profile. Record the confirmed values and timestamp before composing any message. In `send_paused` mode, do not read mail, create Gmail drafts, or send. Before changing to `automatic_outreach`, ask for a separate confirmation that states the campaign and that initial emails and configured follow-ups will be sent without per-message review. Record the active mode and confirmation in `outreach_state.json`.

Offer monitoring defaults once during setup: `Asia/Shanghai`, weekdays at `09:00` and `16:00`, follow-ups on days 5 and 10, maximum two follow-ups, and a 30-day monitoring window. Let the user accept the defaults or provide a custom timezone, cadence, follow-up days, and duration. Record the confirmed settings. Do not silently choose a schedule, and do not create the scheduled task until the first initial email is successfully sent.

Do not continue when:

- Gmail is not connected;
- the current mailbox cannot be identified;
- the user does not confirm the exact From address;
- the user does not confirm the sender display name and signature before composition;
- the user does not confirm monitoring and follow-up settings before enabling automatic outreach;
- the connector lacks either send or thread-search/read capability.

Do not silently replace a missing Gmail action with browser automation. Available Gmail actions can vary by plan and workspace, so verify the actual tools at runtime.

After confirmation, check the From address, send-as alias, visible signature, and whether replies can be searched by thread. For a custom sending domain, publicly check SPF, DKIM, and DMARC and record warnings. A warning informs pacing and deliverability; only a missing send/read capability or mailbox mismatch blocks the campaign.

Read [references/outreach-automation.md](references/outreach-automation.md) for authorization, state transitions, reply handling, anti-fraud rules, and stopping conditions.

## Establish the campaign

Require the target website, target countries or regions, outreach languages, target price per placement, and maximum price per placement. Accept target pages, keywords, competitors, focus (`seo`, `geo`, or `balanced`), exclusions, sender identity, company description, and approved facts that may be used in replies. Default focus to `balanced`.

Read the target website before searching. Derive its business, audiences, core topics, adjacent topics, useful content angles, and likely target pages. Ask only when an unresolved ambiguity would materially change the market, language, budget, sender identity, or facts the campaign is allowed to disclose.

Create a campaign folder containing `campaign.json`, `raw_candidates.json`, `search_log.json`, normalized `history.json`, `shortlist.json`, `outreach_state.json`, and the final workbook. Follow [references/data-contract.md](references/data-contract.md).

## Discover and qualify from scratch

Read [references/discovery.md](references/discovery.md) before a live search. Use current web search, browser research, DataForSEO when configured, and another already-accessible SEO tool when available. Never invent unavailable metrics.

Evaluate at least 90 unique raw domains before selecting the requested outreach count. Maintain `explicit` and `editorial` pools. Store the exact discovery query and at least one current evidence URL for every retained candidate. Search breadth and relevance matter more than similarity to historical purchases.

Read [references/quality-checks.md](references/quality-checks.md) before selection. Run the traffic gate across the broad discovery pool first. Then run public-contact and recipient-fit checks across the traffic-qualified pool. Only after a surplus email-qualified pool exists should the workflow perform deeper article sampling, technical indexability, and outbound-link inspection. Use `scripts/site_checks.py`, `scripts/auto_enrich.py`, `scripts/dataforseo_enrich.py`, and `scripts/pipeline.py` as applicable.

For this campaign type, DataForSEO estimated monthly organic traffic must be at least 1,000. Exclude lower-traffic candidates from the outreach queue. Score SEO and GEO independently and rescale missing components instead of treating them as zero.

## Find contactable publishers

Read [references/contact-discovery.md](references/contact-discovery.md) and run `scripts/contact_discovery.py`. Collect only public business channels with exact source URLs. Never guess an email pattern or collect private contact data.

Any public business channel qualifies for the research workbook. Gmail automation, however, requires a verified public business email whose role and source page fit editorial, advertising, partnership, contributor, or general business routing. Run this gate on the broad traffic-qualified pool, not on an already capped 30-site shortlist. Build a surplus email pool before deep quality review. Social-media, events, careers, support, regional, or unrelated named inboxes do not enter the production-message queue unless the source explicitly assigns them content-cooperation responsibility. Keep rejected contacts only in internal audit data and continue finding replacement contacts or sites until the requested email-sendable count is reached. Do not expose late-stage `contact_recheck` rows in the client send workbook.

## Prepare production messages with sending paused

Use `send_paused` when the user wants the complete production campaign prepared but delivery stopped at the final send boundary. Run discovery, qualification, contact research, evidence selection, and complete production-message composition, then export the subject and body to the workbook with status `ready_to_send`. These are the actual campaign messages, not samples. Do not read Sent mail, create Gmail drafts, send messages, schedule reply checks, or mutate Gmail while sending is paused.

Support a disclosure policy in `campaign.json`. When `public_identity_mode` is `sector_only`, describe the sender only with the approved sector phrase, such as `we work in the steel structure sector`. Do not include the client name, client website, target page, URL, product page, anchor text, or any other prohibited disclosure. Recipient publication names and evidence-backed sections may still be used for personalization.

Read [references/email-style.md](references/email-style.md). Each production-message row must include the recipient, recipient-fit confidence, subject, complete body, personalization evidence URL, template family, prohibited-disclosure check, banned-phrase check, duplication-risk check, and `ready_to_send` status.

## Compose and send without per-message review

Only after the user explicitly changes the campaign from `send_paused` to `automatic_outreach`, send the prepared initial emails automatically. Preparing production messages does not authorize Gmail writes or delivery.

Every message must use only verified campaign and publisher evidence. Personalize with one concrete, relevant detail; do not fabricate article readership, compliments, relationships, or metrics. Keep the email brief and ask for the price and core placement terms. Run a factual and duplication check immediately before sending.

Use conservative pacing, the recipient's business hours when known, and a configurable daily cap. Stop sending on repeated bounces, authentication failure, connector errors, or abnormal complaint/delivery signals. Never evade provider limits or rotate accounts to bypass them.

Record Gmail thread ID, message ID, recipient, subject, sent timestamp, template family, and evidence used. `scripts/outreach_state.py` provides deterministic state, quote extraction, reply classification, and risk-flag helpers.

## Monitor replies and update the workbook

Use the Gmail thread ID as the primary join key. On a schedule, search for replies to sent threads, classify them, extract price and terms, apply anti-fraud flags, and update `outreach_state.json` and the workbook.

The automation may send factual clarification replies using only approved campaign facts and may ask once for a missing price or link terms. It must not negotiate a discount, accept an offer, promise payment, approve publication, provide credentials, open unknown attachments, or follow payment links.

An explicit referral to a sponsorship, advertising, partnerships, or editorial contact overrides ordinary clarification. Stop messaging the original responder, validate the referred business address against the publisher or an evidenced parent domain, then send one new-thread introduction to that contact mentioning the referrer and requesting the missing terms. Link the referral thread to its parent in state and never contact the same referral twice. Do not count referral outreach as a clarification or follow-up on the original thread.

Use no more than the configured follow-up count. Stop follow-ups immediately after a human reply, rejection, bounce, unsubscribe request, or risk flag.

After the first successful send, create one Campaign-level scheduled task in the current chat so it keeps the Campaign context. The scheduled task invokes this Skill and Gmail at the confirmed cadence, stops after the configured monitoring window, and pauses early when every thread reaches a terminal status. In desktop mode, local Excel updates require the machine on, the app running, and the project directory available.

The client-facing workbook should prioritize `有效回复与报价`, followed by `候选资源`, `联系记录`, `运行消耗`, and `历史记录`. Show reply status, quoted price and currency, Follow/Nofollow/Sponsored, permanence, turnaround, content requirements, sender-domain match, risk level, risk reason, source URLs, and last update. Keep the existing restrained white/gray presentation.

## Rolling prospecting mode

When the user explicitly authorizes an ongoing daily campaign, record the daily send target and a concrete completion target in `rolling_state.json`. On each scheduled day, calculate the completion target first with `scripts/rolling_campaign.py`. If it is not met and today's initial-email quota remains, discover and qualify enough new domains to send up to the daily target. Deduplicate against every purchased, previously evaluated, queued, sent, referred, rejected, and bounced domain and recipient.

Before composition, run the usual traffic, publisher-type, contact-role, article-sample, and technical checks plus `scripts/email_preflight.py`. The MX or mail-domain address fallback check is a domain-level preflight, not proof that a mailbox exists. Never pad a daily batch with weak sites or wrong departments. Stop the remaining daily sends after three new hard bounces or any provider/authentication warning and surface the issue.

For a price ceiling campaign, count a publisher as client-handoff ready only when it has no risk flag and either: (a) supplied a quote at or below the configured maximum price, or (b) confirmed a free editorial route. Positive replies that still need pricing, a responsible contact, a required user fact, or fraud review remain pending. Once the target is reached, stop new prospecting, create a client workbook containing only the ready publishers and their evidence/terms, notify the user, and continue monitoring already-sent threads until the configured monitoring window ends.

## Handoff boundary

Deliver the updated workbook and a concise count of sent, replied, quoted, bounced, rejected, awaiting reply, and risk-flagged threads. This Skill never:

- purchases a placement or initiates payment;
- accepts a quote, contract, insertion order, or binding term;
- provides passwords, verification codes, API keys, or client account access;
- opens unknown attachments or submits payment information;
- represents a suspicious reply as safe.

Stop at evidence-backed replies and quotes and hand those results to the client.
