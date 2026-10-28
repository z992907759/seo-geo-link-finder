# Campaign Data Contract

All JSON files use UTF-8. Dates use `YYYY-MM-DD`; timestamps use ISO 8601.

## `campaign.json`

```json
{
  "campaign_name": "",
  "target_site": "https://example.com/",
  "target_markets": ["United States"],
  "languages": ["English"],
  "target_price_usd": 100,
  "max_price_usd": 150,
  "focus": "balanced",
  "target_pages": [],
  "keywords": [],
  "competitors": [],
  "exclusions": [],
  "business_summary": "",
  "audience_summary": "",
  "core_topics": [],
  "adjacent_topics": [],
  "content_angles": [],
  "outreach": {
    "mode": "send_paused",
    "public_identity_mode": "sector_only",
    "public_industry_description": "we work in the steel structure sector",
    "prohibited_disclosures": ["client name", "client website", "target page", "URL", "anchor text"],
    "requested_email_count": 30,
    "daily_send_cap": 20,
    "monitoring_timezone": "Asia/Shanghai",
    "reply_check_times": ["09:00", "16:00"],
    "reply_check_days": ["MO", "TU", "WE", "TH", "FR"],
    "follow_up_days": [5, 10],
    "max_follow_ups": 2,
    "monitoring_duration_days": 30,
    "monitoring_settings_confirmed": false,
    "monitoring_settings_confirmed_at": "",
    "reply_check_schedule": "09:00 and 16:00 on weekdays",
    "approved_sender_name": "",
    "approved_signature": "",
    "sender_identity_confirmed": false,
    "sender_identity_confirmed_at": "",
    "approved_company_name": "",
    "approved_sender_facts": []
  }
}
```

`focus` is `seo`, `geo`, or `balanced`.

## `history.json`

An array of records with `domain`, `authority_metric_raw`, `traffic_estimate_raw`, `category`, `link_attribute`, `price_raw`, `price_usd`, `anchor_and_target_raw`, `placement_url`, `original_domain_raw`, and `source_row`.

The importer must not label the generic authority or traffic columns as Ahrefs, Semrush, DR, or DA without source evidence.

## `raw_candidates.json`

Each candidate contains:

- identity: `domain`, `site_name`, `country_region`, `language`, `industry`;
- discovery: `pool`, `discovery_method`, `discovery_query`, `evidence_url`, `relevance_reason`, `cooperation_evidence`;
- sourced metrics: `authority_metric`, `metric_source`, `traffic_estimate`, `traffic_source`;
- price: optional `public_price_min_usd`, `public_price_max_usd`, `price_evidence_url`;
- scoring: `seo_components` and `geo_components`, using the component names in `scoring.md` and values from 0–5 or null;
- quality: `risk_flags`, `hard_exclude_reason`, `last_verified`;
- verification: `quality_checks` with the shape below;
- public contact channels: optional `contact_info` produced after shortlist enrichment;
- editable review: optional `human_decision` and `reviewer_notes`.

Do not add private contact names, guessed email addresses, phone numbers, mailbox credentials, OAuth tokens, cookies, or payment details. Public business email and outbound-message state belong in `contact_info` and `outreach_state.json`, not in raw discovery fields.

### `quality_checks`

```json
{
  "traffic_estimate": null,
  "traffic_unit": "monthly organic visits",
  "traffic_source": "unavailable",
  "traffic_scope": "",
  "traffic_checked_at": "2026-08-24",
  "public_audience_note": "",
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
  "checked_at": "2026-08-24",
  "confidence": "low",
  "notes": ""
}
```

`traffic_source` must identify the provider or be `unavailable`. `index_status` is one of `indexed`, `partially_indexed`, `not_found`, `technically_blocked`, `insufficient_samples`, or `not_checked`. Search-result absence is an observation, not definitive proof of non-indexation.

### `contact_info`

Contains `recommended_channel`, `department`, `emails`, `submission_pages`, `advertising_pages`, `contact_pages`, `forms`, `linkedin_pages`, `whatsapp_links`, `source_urls`, `confidence`, `checked_at`, and `notes`. Every email or channel must be publicly observable at a recorded source URL. Do not infer address patterns.

## `search_log.json`

An array with `query`, `source_type`, `results_reviewed`, `candidates_kept`, `notes`, and `searched_at`.

## `shortlist.json`

The pipeline enriches candidates with normalized domains, independent SEO/GEO scores and confidence, price range/basis/confidence, traffic/index/link-check fields, purchase-history flags, focus score, recommendation, and rank. Excluded candidates are retained under the top-level `excluded` array for auditability.

## `outreach_state.json`

```json
{
  "version": 1,
  "campaign_name": "",
  "mailbox": {
    "detected_email": "",
    "confirmed_email": "",
    "confirmed_at": "",
    "send_capability": false,
    "thread_read_capability": false,
    "send_as_alias": "",
    "spf": "unknown",
    "dkim": "unknown",
    "dmarc": "unknown"
  },
  "sender_identity": {
    "display_name": "",
    "signature": "",
    "confirmed": false,
    "confirmed_at": ""
  },
  "authorization": {
    "mode": "disabled",
    "authorized_at": "",
    "target_site": "",
    "initial_email": false,
    "follow_ups": false,
    "read_replies": false,
    "factual_clarifications": false
  },
  "settings": {
    "daily_send_cap": 20,
    "monitoring_timezone": "Asia/Shanghai",
    "reply_check_times": ["09:00", "16:00"],
    "reply_check_days": ["MO", "TU", "WE", "TH", "FR"],
    "follow_up_days": [5, 10],
    "max_follow_ups": 2,
    "monitoring_duration_days": 30,
    "monitoring_settings_confirmed": false,
    "monitoring_settings_confirmed_at": "",
    "scheduled_task_id": "",
    "scheduled_task_created_at": ""
  },
  "prospects": [],
  "events": []
}
```

`authorization.mode` becomes `automatic_outreach` only after the user confirms the exact mailbox, sender display name/signature, and campaign. Each prospect stores `domain`, `recipient`, `contact_source_url`, `status`, Gmail `thread_id` and `message_id`, send and reply timestamps, follow-up count, reply classification, quote fields, placement terms, risk flags, and evidence URLs. An explicit publisher referral is stored in `referral_outreach` with `recipient`, `referred_by`, `parent_thread_id`, its own Gmail `thread_id` and `message_id`, sent time, reply status, processed reply IDs, quote, placement terms, and risk flags. Never store mailbox secrets or payment credentials.

Allowed prospect statuses are `ready`, `ready_to_send`, `contact_recheck`, `sent`, `followed_up`, `replied`, `quoted`, `rejected`, `bounced`, `unsubscribed`, `risk_hold`, `awaiting_reply`, and `other_channel`.

`send_paused` is an authorization mode, not a delivery authorization. It permits full production research, message generation, validation, and workbook export only. Store only recipient-fit-qualified production rows in `outreach_messages_ready.json`; rejected contacts remain in internal audit data. Each row contains `domain`, `site_name`, `recipient`, `recipient_fit`, `recipient_fit_reason`, `subject`, `body`, `template_family`, `personalization_evidence`, `evidence_url`, `banned_phrase_check`, `prohibited_disclosure_check`, `signature_check`, `duplication_risk`, and `status` (`ready_to_send`).

## Client workbook

The default sheet order is `有效回复与报价`, `候选资源`, `联系记录`, `运行消耗`, and `历史记录`. The first sheet contains only human replies and extracted quotes. `联系记录` retains all attempts for auditability. Thread IDs are identifiers, not links; include a separate Gmail thread URL when the connector returns one.
