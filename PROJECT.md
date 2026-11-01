PROJECT: OutreachOS, an AI sales-outreach platform for B2B. FREE TOOLS ONLY.

ALREADY DONE: Weeks 1-3 (Python, venv, llm.py with Gemini free tier, Supabase Postgres with companies/contacts/lead_research, FastAPI with /leads endpoints, pytest, logging, retry helper).

STACK
- Backend: Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest
- DB: Supabase Postgres (free). Frontend: Next.js + TypeScript + Tailwind
- Jobs: Postgres-based queue (jobs table, SELECT ... FOR UPDATE SKIP LOCKED) and a worker process. No Redis, no paid services.
- AI: only through one file (llm.py). Model name in one constant. Retry with backoff on 429. Log every call in an llm_calls table (org_id, purpose, model, input_tokens, output_tokens, latency_ms, success).
- Email: Gmail API OAuth (Google Cloud project in Testing mode). Default SEND_MODE=dry-run: messages are written to an outbox table and shown in the UI, never sent. Live mode sends only to an ALLOWLIST of my own addresses until I remove it.
- Payments: Stripe TEST MODE only.

RULES
1. Do NOT quiz me. Do NOT ask questions unless something is missing or a command fails. Decide sensibly and record decisions in DECISIONS.md.
2. Secrets only in .env (in .gitignore before creation). Never print, log or commit secrets. Keep .env.example with fake values.
3. Every SQL query is parameterized. Every customer-data table has org_id, and every query filters by org_id. Tests prove Org A cannot read Org B.
4. Encrypt OAuth tokens at rest (Fernet, key in .env).
5. Validate all AI output with Pydantic. On invalid output retry once, then mark failed. Enforce per-org and per-lead token budgets.
6. Compliance: unsubscribe link in every email, sender postal address field, permanent suppression list checked before every send, daily limit per inbox (default 30).
7. Fake or public business data only. No scraping personal data. Respect robots.txt, 1 request/second per domain. Remind me the free Gemini tier may use inputs for Google's products, so no real customer data.
8. Beginner-friendly code: type hints, small files, a short comment above non-obvious lines.
9. After each week: run pytest and fix failures yourself; update README.md and BUILD_LOG.md; give me (a) the exact commands to run, (b) what output I should see, (c) a short manual checklist, (d) the git commands. Remind me to run git status and confirm .env and .venv are NOT listed. Then STOP until I say "next".
10. If something needs a paid service or a billing account, stop and offer a free alternative. Before choosing hosting or checking any limits, search the current official docs, because free tiers change.