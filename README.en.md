# SEO/GEO Link Finder & Email Outreach

[简体中文](README.md) | **English**

An agent workflow for discovering backlink publishers, verifying public business contacts, preparing outreach emails, recording Gmail delivery state, tracking replies and quotes, and exporting results.

This is a standalone public copy of the original email outreach version from the project archived on October 19, 2026. It includes the workflow, scripts, tests, and example configuration. Historical client names embedded in code and the original sender name in test fixtures have been replaced or removed. The original archive remains local.

## Features

- Discover publishers and evaluate SEO / GEO quality, traffic, and cooperation evidence.
- Find public business email addresses and check recipient roles and mail domains.
- Generate personalized messages from verified facts; check signatures, prohibited disclosures, and duplicate copy.
- Track sending, follow-ups, referrals, bounces, replies, quotes, and risk flags.
- Manage ongoing outreach against volume and budget targets, and export prospect, contact, and quote worksheets.

## Project structure

```text
SKILL.md         Agent workflow entry point and authorization boundaries
agents/          Agent interface metadata
assets/          Example campaign configuration without real accounts
references/      Data contracts, qualification criteria, email style, and outreach rules
scripts/         Research, copy generation, state management, and spreadsheet tools
tests/           Python unit tests
```

## Requirements and usage

Python 3.10+. The Python scripts use only the standard library. Tests do not require an email account or a paid API.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/pipeline.py --help
python3 scripts/outreach_state.py --help
python3 scripts/compose_messages.py --help
```

Start a local campaign:

```bash
mkdir -p campaigns/my-campaign
cp assets/campaign-brief.example.json campaigns/my-campaign/campaign.json
```

Edit the target website, markets, budget, and approved facts. Prepare input data according to `references/data-contract.md`. See [SKILL.md](SKILL.md) for the full workflow and qualification order.

### Email and automation

The agent running this workflow sends and reads messages through connected Gmail tools. This repository does not include a standalone SMTP sender, Gmail OAuth client, or persistent scheduler. Running the Python scripts alone will not send emails. Live operation requires an agent environment with Gmail integration and scheduling, plus the mailbox identity, sender signature, and campaign authorization required by the workflow.

The example configuration defaults to `send_paused`: it permits message preparation but does not authorize delivery. Confirm the mailbox, signature, sending scope, and follow-up settings before enabling `automatic_outreach`.

### Optional DataForSEO integration

For DataForSEO search or traffic estimates, configure the `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` environment variables. On macOS, the password may also be read from the Keychain service `seo-geo-link-finder-dataforseo`, keyed by the API login. Supply your own account; API calls may incur charges. The scripts do not load `.env` files automatically.

### Excel export

The `*.mjs` tools require Node.js and `@oai/artifact-tool`. The runtime must supply this dependency; it is not bundled here, and availability through public npm is not guaranteed. The Python workflow and JSON outputs can be used without it. Excel rendering and export require a compatible environment.

## Data and boundaries

Real client lists, mailbox identities, actual email content, Gmail message and thread IDs, historical quotes, and Excel exports are excluded from this public repository. `.gitignore` excludes campaign folders, output folders, credentials, and runtime artifacts.

The workflow collects cooperation replies and quotes. It does not purchase placements, promise payment, or accept contracts. Outreach must respect provider rules and recipient opt-out requests.
