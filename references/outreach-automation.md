# Gmail Outreach Automation

## Mailbox and authorization gate

1. Inspect the available Gmail connector actions.
2. Retrieve the authenticated mailbox and send-as aliases without reading message bodies.
3. Show the exact From address and campaign target site to the user.
4. Ask the user to confirm the public sender display name and complete closing signature; do not infer them from the Gmail profile.
5. Ask for one explicit confirmation that this mailbox may automatically send initial outreach and configured follow-ups, read replies, and send fact-only clarification messages for this campaign.
6. Record the mailbox, signature, confirmation timestamps, and enabled actions. No per-message review is required afterward.

To prepare a production campaign without delivery, set `authorization.mode` to `send_paused`. This mode authorizes full research, production-message composition, validation, and workbook export. Prospects with completed messages use status `ready_to_send`. It does not authorize reading mailbox content, creating Gmail drafts, sending, following up, or monitoring replies. Promotion to `automatic_outreach` requires a new explicit confirmation.

If the Gmail connector cannot expose the mailbox identity, send messages, or search/read threads, stop. Never request a password or silently fall back to browser automation.

## Sending state

Only prospects with a public business email and source URL enter `ready`. Send in configured batches, record the Gmail thread ID, and transition to `sent` or `awaiting_reply`. Apply at most the configured follow-ups. Stop immediately on reply, bounce, rejection, unsubscribe, or risk hold.

Use Gmail thread ID as the join key. Domain is a secondary key; email subject is not a reliable key.

## Reply classes

- `quoted`: contains a price or price range for a placement.
- `replied`: relevant human reply without a usable price.
- `rejected`: declines guest, sponsored, advertising, or link cooperation.
- `bounced`: delivery failure.
- `unsubscribed`: asks not to be contacted.
- `risk_hold`: contains a fraud, credential, attachment, or identity warning.
- `auto_reply`: out-of-office or automated acknowledgement; keep waiting.
- `unrelated`: not a response to the campaign request.

Extract the original wording and structured fields separately: amount, currency, whether the figure is a range, link attribute, permanence, turnaround, content responsibility, number of links, publication URL or category, payment timing, and conditions. Never translate a price estimate into a quote.

## Automatic clarification

One factual clarification reply is allowed when the publisher asks for the target site, target page, topic, company identity, or another fact explicitly approved in `campaign.json`. If the response says cooperation is available but omits price or link terms, ask once for the missing information.

### Explicit contact referrals take priority

If a human reply names or supplies a different person responsible for sponsorship, advertising, partnerships, or editorial cooperation, do not ask the original responder any more placement questions. Treat the referral as an instruction to switch contacts:

1. Extract the referred person's name and public business email from the reply.
2. Confirm the email domain matches the publisher or an already evidenced parent/company domain. Otherwise place it on `risk_hold` for manual review.
3. Open a new Gmail thread to the referred contact, mention the referrer naturally, and ask for the still-missing price and core placement terms.
4. Record the new message as a child of the original thread in `referral_outreach`, including both Gmail thread IDs and message IDs.
5. Never contact the same referred address twice. A referral email is separate from, and does not consume, the original thread's clarification or follow-up allowance.

After a valid referral is recorded, the original responder receives no further clarification or follow-up. Replies to the referral thread are monitored and classified under the same quote, safety, and stopping rules.

Do not negotiate, request a discount, accept terms, approve an insertion order, promise payment, or supply information absent from approved campaign facts.

## Fraud and safety flags

Place a thread on `risk_hold` when any of these occurs:

- From or Reply-To domain does not match the publisher domain or a previously evidenced parent/company domain;
- the recipient changes to an unrelated free-mail or payment address;
- requested payment uses cryptocurrency, gift cards, money transfer, friends-and-family payment, or a newly changed bank account;
- the reply requests passwords, login access, verification codes, API keys, cookies, or remote access;
- an unexpected executable, macro-enabled document, archive, or password-protected attachment appears;
- the sender uses unusual urgency, secrecy, or threatens immediate loss;
- the quoted publication domain or URL differs from the researched publisher.

A flag does not prove fraud; it prevents automatic replies and makes the discrepancy visible to the client. Do not open unknown attachments or payment links.

## Scheduled monitoring

Offer, then confirm, these defaults during Campaign setup:

- timezone: `Asia/Shanghai`;
- reply checks: weekdays at `09:00` and `16:00`;
- follow-ups: days 5 and 10 after the initial email;
- maximum follow-ups: 2;
- monitoring window: 30 days.

The user may accept the defaults or provide custom values. Store `monitoring_settings_confirmed` and its timestamp. Do not create a scheduled task while sending is paused. After the first successful initial email, create one Campaign-level scheduled task in the current chat and invoke this Skill explicitly. On desktop, the host must remain available for local-file updates.

Each check must be idempotent: ignore already recorded Gmail message IDs and write one event per newly observed message. Pause the scheduled task when the monitoring window expires or every thread is replied, rejected, bounced, unsubscribed, or held for risk.

### Rolling daily prospecting

Rolling prospecting is opt-in and uses one durable Campaign-level scheduled task. Store `daily_new_email_target`, `positive_target`, local timezone, maximum price, cumulative candidate/message paths, and completed daily batches in `rolling_state.json`. The first run each local day may research and send the remaining daily quota; later runs that day only monitor or complete an interrupted, idempotent batch.

Every retained address must pass public-source recipient fit and an MX or mail-domain address fallback preflight. Never store DataForSEO or Gmail passwords in Campaign JSON, automation prompts, or output files. Non-interactive DataForSEO calls may read the password from macOS Keychain service `seo-geo-link-finder-dataforseo`, keyed by the API login supplied through `DATAFORSEO_LOGIN`.

Count completion using `scripts/rolling_campaign.py`, not an ad hoc total. Handoff-ready means a risk-free quote within budget or a confirmed free editorial route. Over-budget quotes, rejects, auto-replies, delivery delays, referrals still awaiting the responsible contact, and positive replies missing price remain visible but do not satisfy the target. When the target is reached, stop new discovery/sending and produce the client-only workbook; do not accept any offer or initiate payment.

## Stop conditions

Stop new sending and surface the issue when Gmail authentication expires, the confirmed mailbox changes, send capability disappears, several consecutive messages bounce, or provider delivery/complaint signals become abnormal. Never rotate accounts or increase volume to bypass a provider restriction.

The workflow ends at a client handoff containing replies, quotes, placement terms, and risk flags. It never purchases, pays, accepts, contracts, or shares credentials.
