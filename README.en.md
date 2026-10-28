# SEO/GEO Link Finder

**Find publishers. Reach the right inbox. Get the quote. Keep it all together.**

[简体中文](README.md) | **English**

Backlink outreach comes with a lot of legwork: searching for sites, digging up contact details, writing each email, then checking your inbox for replies.

This project puts those steps into one AI assistant workflow. Provide your website, target market, and budget, then confirm your sending identity and scope. The assistant can find publishers, send outreach, and organize replies so you can see who is interested, what they charge, and what their terms are.

```text
Your website + target market + budget
                  ↓
Find sites → Check quality → Find contacts → Email → Follow up
                  ↓
Publisher shortlist, quotes, placement terms, and contact history
```

## What it takes off your plate

- **Find sites with a reason to contact them.** Check topic fit, traffic thresholds, and cooperation opportunities. Keep source links so you can review the evidence.
- **Check who handles partnerships.** Find public editorial, advertising, or business contacts and filter out unrelated recruiting and support inboxes.
- **Write an email that fits each publisher.** Use verified sections and cooperation details to ask about price, link policy, and timing. Check signatures, repetitive copy, and prohibited client disclosures before sending.
- **Turn replies into usable results.** Track quotes, free editorial opportunities, rejections, and bounces. Handle referrals to another contact, and stop follow-ups after a reply or opt-out.

Built for people doing website SEO, international content partnerships, or publisher outreach for clients.

## What you get back

A list you can use to move a conversation forward:

| Your question | What the results include |
| --- | --- |
| Why contact this site? | Topic fit, qualification evidence, and source links |
| Where does the conversation stand? | Sent, awaiting reply, quoted, rejected, or bounced |
| What does it cost? | Quoted price and currency, or a confirmed free editorial route |
| What are the terms? | Link attributes, permanence, turnaround, and content requirements, where supplied |
| What needs my judgment? | Missing terms, unusual replies, and risk flags |

Keep results as JSON, or export to Excel when a compatible spreadsheet runtime is configured.

## An example brief

> Find industry publishers serving English-speaking markets for my website. Start with 30 suitable contacts, with a maximum budget of $100 per placement. Prepare the outreach emails for me to review, then send them after I confirm and collect the quotes that come back.

The assistant checks your goals, mailbox, and signature before starting. The default is to prepare messages before sending. With explicit authorization, it can also send and follow up within the scope you agree on.

**Live email requires an AI assistant environment connected to Gmail. Ongoing follow-ups also require scheduling support.** This repository supplies the Skill and supporting scripts; running Python alone will not send emails.

## Get started

```bash
git clone https://github.com/z992907759/seo-geo-link-finder.git
cd seo-geo-link-finder

# Run local tests without an email account or paid API
python3 -m unittest discover -s tests -v

# Create your own campaign configuration
mkdir -p campaigns/my-campaign
cp assets/campaign-brief.example.json campaigns/my-campaign/campaign.json
```

Requires **Python 3.10+**. The Python scripts use only the standard library. Set your website, markets, and budget in the configuration, then give [SKILL.md](SKILL.md) to an assistant that supports this workflow. Follow its steps to connect Gmail, confirm the sender identity, and prepare your data.

To inspect a script entry point, run `python3 scripts/pipeline.py --help`. See the [data reference](references/data-contract.md) for input formats.

<details>
<summary>Optional setup: traffic data and Excel export</summary>

### DataForSEO

DataForSEO can supply website search and traffic estimates. Bring your own account; API calls may incur charges.

Set the `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` environment variables. On macOS, the password can also be read from the Keychain service `seo-geo-link-finder-dataforseo`, keyed by the API login. The scripts do not load `.env` files automatically.

### Excel

The spreadsheet scripts require Node.js and a runtime that provides `@oai/artifact-tool`. This dependency is not bundled, and availability through public npm is not guaranteed. Without it, you can still use the Python scripts and JSON results.

</details>

<details>
<summary>Where is everything?</summary>

| File / directory | Purpose |
| --- | --- |
| `SKILL.md` | Complete instructions for the assistant |
| `assets/` | Example campaign configuration |
| `scripts/` | Site qualification, email copy, reply tracking, and spreadsheet tools |
| `references/` | Qualification rules, email style, and data formats |
| `tests/` | Unit tests |
| `agents/` | Assistant interface configuration |

</details>

## Keep your campaign data in your own workspace

The public repository contains code, documentation, and examples. It does not include real client lists, mailbox accounts, email records, or historical quotes. `.gitignore` excludes campaign folders, output folders, common credentials, and campaign state files. Review new files before publishing your own changes.

The assistant finds opportunities and collects replies and quotes. You decide which publisher to work with, whether to buy, and whether to accept terms. Respect email provider rules and recipient opt-out requests.
