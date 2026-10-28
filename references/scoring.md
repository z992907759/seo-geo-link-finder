# Scoring and Price Calibration

Scores rank opportunities; they do not make purchase decisions.

## Component input

Rate each verified component from 0 to 5. Use `null` when unverified. The pipeline rescales available weights to 100, so missing evidence does not become a zero.

### SEO score

| Component | Weight | What to verify |
|---|---:|---|
| topical_relevance | 30 | Direct connection to the target topic, product, or buyer problem |
| organic_visibility | 20 | Public search presence or sourced organic-traffic evidence |
| domain_authority | 15 | Recognized industry authority or sourced third-party metric |
| indexation_freshness | 15 | Crawlable pages, current publishing, and evidence of indexability |
| editorial_quality | 10 | Original, useful content with editorial ownership |
| contextual_link_potential | 10 | A natural page/context exists for a useful citation or mention |

Use sampled guest/contributor pages to support `indexation_freshness` and `contextual_link_potential`. Do not award full evidence coverage from a submission page alone.

### GEO score

| Component | Weight | What to verify |
|---|---:|---|
| topical_authority | 25 | Sustained expertise in the relevant subject |
| citation_worthiness | 25 | Explanatory, data-rich, expert, or reference-style content |
| entity_transparency | 15 | Clear organization, authors, expertise, and editorial identity |
| discoverability | 15 | Crawlable, structured, findable content |
| content_freshness | 10 | Recent updates or maintained evergreen resources |
| natural_mention_fit | 10 | The target brand or expertise could be mentioned without forcing it |

## Confidence

- `high`: at least 80% of component weight is verified and the most heavily weighted component has direct evidence.
- `medium`: at least 55% of component weight is verified.
- `low`: less than 55% is verified; retain only when the opportunity rationale is still useful.

## Price hierarchy

Use the first available basis:

1. Public exact price or bounded public range: `public`, high confidence.
2. Historical price for the same normalized domain: `same_domain_history`, medium confidence unless a date confirms freshness.
3. At least two historical peers in the same category and roughly similar sourced authority: `historical_peer`, low confidence; use their interquartile range.
4. Historical global interquartile range: `historical_global`, low confidence.
5. No defensible basis: `unknown`; retain the candidate and mark it `待询价`.

Never present an estimate as a quote. Preserve the raw price evidence and currency. Do not convert currencies without recording the rate source and date.

## Recommendation

The pipeline calculates a focus score for ranking only:

- SEO focus: SEO score.
- GEO focus: GEO score.
- Balanced: mean of available SEO and GEO scores.

Recommendation bands:

- `优先`: focus score at least 75 and no hard exclusion.
- `值得评估`: 60–74.
- `补充候选`: below 60 but still relevant or strategically useful.

Risk flags, historical purchase, and price confidence remain separate columns. Do not conceal a concern inside a composite score.

Traffic, sample indexation, and observed link attributes remain separate evidence fields and must not be hidden inside either score. A missing paid-tool metric lowers evidence confidence but is not an automatic rejection.
