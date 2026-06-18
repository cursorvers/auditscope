# AuditScope v2

Medical AI paper governance monitor. Searches PubMed daily for AI-related
clinical papers, evaluates them on a 7-axis governance framework, generates
a Word report, and emails it via Gmail. Designed to be forked and customised
per clinical specialty.

## Tech stack

- Python 3 (no framework)
- BioPython Entrez (PubMed search)
- Google Generative AI SDK / Gemini 2.0 Flash (2-stage summarisation)
- python-docx (Word report, CJK Yu Gothic)
- Gmail SMTP (delivery)
- PyYAML + python-dotenv (config / env)
- GitHub Actions (daily 07:00 JST cron)

## Key files

- main.py            -- pipeline orchestrator (search -> filter -> summarise -> report -> mail)
- pubmed_searcher.py -- PubMed Entrez query runner
- paper_filter.py    -- retraction DB check, study-type scoring
- ai_summarizer.py   -- Gemini 2-stage 7-axis governance evaluation
- word_generator.py  -- Word document builder
- send_gmail.py      -- SMTP mailer
- audit_schema.py    -- JSONL audit log (run_id, sha256 hashes)
- setup.py           -- interactive config generator (Gemini-driven)
- config.yaml        -- search queries, journal tiers, governance axes, thresholds
- logs/audit.jsonl   -- append-only audit trail
- .github/workflows/ -- daily_summary.yml (cron), setup.yml

## Commands

```
python setup.py                     # interactive config generation (needs GEMINI_API_KEY)
python main.py                      # full pipeline run
python main.py --dry-run             # test without sending email
python main.py --dry-run --sample-output  # generate sample Word doc
python3 -m py_compile *.py           # syntax check before PR
pip install -r requirements.txt      # install deps
```

## Environment variables

- GEMINI_API_KEY      -- required, Google AI Studio key
- GMAIL_ADDRESS       -- required, sender Gmail address
- GMAIL_APP_PASSWORD  -- required, Gmail app password (2FA enabled)
- NCBI_API_KEY        -- optional, raises PubMed rate limit

## Constraints

- MeSH terms are banned in query_templates; use only words found in real titles/abstracts.
- v1 (HTML email, hardcoded config) is incompatible; see MIGRATION.md and legacy/v1 branch.
- Upstream: fork of yush02084/medical-paper-summarizer-public (MIT). Preserve attribution.
- config.yaml crosswalk_refs maps 7 axes to GuideScope columns (optional, off by default).
