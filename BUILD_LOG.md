# Build Log - OutreachOS

## Day 2: Lists and Dictionaries

**What I built:**
- week1/day2.py with 10 beginner exercises covering lists and dictionaries
- Business name list (indexing with [0] and [-1], len(), .append(), for loop)
- Single lead dictionary (f-strings, updating values, adding new keys)
- List of 4 lead dictionaries (filtering by has_website, filtering with is_good_lead)
- score_lead skeleton left as TODO for tomorrow

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about lists and dictionaries)

**Tomorrow:**
- Finish Exercise 10: write score_lead(), print "name: score" for each lead, and find the highest-scoring lead

## Day 3: Files, JSON, Try/Except, Virtual Environments

**What I built:**
- week1/day3.py with JSON write/read, load_leads(), save_leads(), JSONDecodeError demo
- .gitignore with .env, .venv/, __pycache__/, week1/leads.json
- requirements.txt with requests, google-genai, python-dotenv

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about files, JSON, and error handling)

**Tomorrow:**
- Build Day 4: HTTP APIs with the requests library

## Day 4: HTTP and REST APIs

**What I built:**
- week1/day4.py with GET request to jsonplaceholder.typicode.com, status codes, error handling, 404 demo
- fetch_users() TODO skeleton

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about HTTP and APIs)

**Tomorrow:**
- Build Day 5: Call a free LLM API (Gemini) via week1/llm.py

## Day 5: Call a Free LLM API (Gemini)

**What I built:**
- week1/llm.py with ask_llm(prompt) returning (text, input_tokens, output_tokens), 429 retry with backoff
- week1/day5.py with API key explainer, ask_llm demo, summarize_company() TODO
- .env setup (you create this yourself with your Gemini API key)

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about API keys and LLM calls)

**Tomorrow:**
- Build the Week 1 Checkpoint CLI tool (outreach_cli.py)

## Week 1 Checkpoint: CLI Tool

**What I built:**
- week1/outreach_cli.py with TODO skeletons for summarize_company() and the main loop
- week1/README.md with install/run instructions and example output

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned from building the full CLI tool)

**Tomorrow:**
- Final verification: run all days, answer 5-week quiz, commit one commit per day

## Week 2 Day 1: Supabase and First SQL

**What I built:**
- week2/sql/day1.sql with CREATE TABLE companies, INSERT 5 Coimbatore rows, SELECT *, SELECT WHERE, SELECT ORDER BY
- Plain-English explanations of database, table/row/column, Postgres, and why databases beat JSON files
- Primary keys and data types explained in 5 lines

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about SQL and Supabase)

**Tomorrow:**
- Build Week 2 Day 2: UPDATE, DELETE, JOIN

## Week 2 Day 2: UPDATE, DELETE, JOIN

**What I built:**
- week2/sql/day2.sql with UPDATE/DELETE with WHERE warnings, BEGIN...ROLLBACK example
- contacts table with FOREIGN KEY to companies, 8 fake contacts (@example.com only)
- INNER JOIN and LEFT JOIN examples with text drawing
- Practice queries: GROUP BY count, companies with no contacts, employees 5-20
- TODO skeleton for website + 5-20 employees query

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about JOINs and transactions)

**Tomorrow:**
- Build Week 2 Day 3: schema design

## Week 2 Day 3: Design the Schema

**What I built:**
- week2/sql/schema.sql with companies, contacts, lead_research tables
- UNIQUE constraint on companies.name (added for ON CONFLICT support in Day 5)
- UNIQUE (company_id, email) on contacts, indexes on company_id columns
- week2/schema.md with Mermaid ER diagram and rebuild instructions
- Drop-and-recreate script with loud dev-only warning
- TODO skeleton for status column with CHECK constraint

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about normalization and schema design)

**Tomorrow:**
- Build Week 2 Day 4: connect Python to Postgres

## Week 2 Day 4: Connect Python to Postgres

**What I built:**
- week2/db.py as the ONLY file that opens database connections, exposes get_engine()
- week2/day4.py with SQLAlchemy Core, text(), parameterized queries (:name style)
- SQL injection explanation in 5 lines
- Connect, print Postgres version, SELECT all companies, INSERT with parameters, commit
- try/except for connection errors with friendly message (never shows password)
- requirements.txt updated with sqlalchemy, psycopg

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about SQLAlchemy and connection strings)

**Tomorrow:**
- Build Week 2 Day 5: save real leads

## Week 2 Day 5: Save Real Leads

**What I built:**
- week2/day5.py with save_company() using ON CONFLICT (name) DO NOTHING
- import_leads() with batch insert in one transaction, one commit
- fetch_fake_leads() from jsonplaceholder.typicode.com (free, no key)
- logging module (not print) tracking inserted/skipped/failed
- try/except with friendly error message, never shows password
- TODO skeleton for save_ai_summaries() using week1/llm.py

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned today about batch inserts and logging)

**Tomorrow:**
- Build Week 2 Checkpoint: leads_cli.py

## Week 2 Checkpoint: CLI Tool

**What I built:**
- week2/leads_cli.py with TODO skeleton for menu loop
- SQL helper functions for list, search, add, JOIN
- README section on rebuilding database from schema.sql
- Test: 50 companies saved, JOIN queried, no duplicates after double import

**What broke:**
- (fill in any errors you hit while typing or running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned from building the full CLI tool)

**Tomorrow:**
- Final verification: git status (no .env, no .venv), search for password, 5 whole-week questions, one commit per day

## Week 3 Day 1: async / await

**What I built:**
- week3/day1_async.py with restaurant analogy explanation (6 lines)
- Slow sequential fetch of 10 URLs from jsonplaceholder.typicode.com
- Fast concurrent fetch with asyncio.gather and httpx.AsyncClient
- asyncio.Semaphore(5) to limit concurrency (free API rate limiting)
- Per-request httpx.HTTPError handling; reports succeeded/failed counts
- Prints both times side by side with speedup factor

**What broke:**
- (fill in any errors you hit while running the code)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned about async/await)

**Tomorrow:**
- Build Week 3 Day 2: pure logic functions + pytest

## Week 3 Day 2: Testing with pytest

**What I built:**
- week3/leads_logic.py with is_good_lead(), score_lead(), clean_company_name() (type hints, pure functions)
- week3/tests/test_leads_logic.py with parametrized tests, boundaries (4, 5, 20, 21), empty strings, extra spaces
- week3/tests/test_async_mock.py with mocked httpx (no real network calls)
- week3/tests/test_retry.py for retry_with_backoff (succeeds after retries, gives up, non-matching exception)

**What broke:**
- (fill in any errors you hit while running pytest)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned about pytest)

**Tomorrow:**
- Build Week 3 Day 3: FastAPI basics

## Week 3 Day 3: FastAPI basics

**What I built:**
- week3/app/main.py with FastAPI app, GET /health, GET /leads, GET /leads/{lead_id}, GET /leads/good
- CORS allowing only http://localhost:3000
- Route ordering comment: /leads/good before /leads/{lead_id}
- Parameterized SQL queries only (:name style)
- week3/app/schemas.py not yet created (Day 4)

**What broke:**
- (fill in any errors you hit while running uvicorn)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned about FastAPI)

**Tomorrow:**
- Build Week 3 Day 4: POST endpoints + Pydantic

## Week 3 Day 4: POST endpoints and Pydantic

**What I built:**
- week3/app/schemas.py with LeadCreate and LeadOut Pydantic models
- POST /leads with validation, ON CONFLICT DO NOTHING, 201 or 409
- PATCH /leads/{lead_id} for partial updates
- DELETE /leads/{lead_id} returning 204 or 404
- GET /leads with limit/offset/search query parameters
- GET /leads/good sorted by score
- 422 validation error explanation (5 lines)

**What broke:**
- (fill in any errors you hit)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned about Pydantic and FastAPI validation)

**Tomorrow:**
- Build Week 3 Day 5: logging, retries, API tests

## Week 3 Day 5: Logging, retries, and API tests

**What I built:**
- week3/app/logging_config.py with console + rotating file handler, request id, timestamp, level
- week3/app/retry.py with retry_with_backoff decorator (exponential backoff + jitter)
- week3/app/main.py updated with request-logging middleware, global exception handler (clean 500 JSON)
- week3/tests/test_api.py with TestClient tests for all endpoints (mocked database, no real data)
- logs/ added to .gitignore

**What broke:**
- (fill in any errors you hit)

**How I fixed it:**
- (fill in how you resolved each error)

**What I learned:**
- (fill in what you learned about logging and testing)

**Tomorrow:**
- Week 3 Checkpoint: run all tests, start server, verify endpoints, commit one per day

## Week 3 Checkpoint: Verification

**What I verified:**
- Ran `.\.venv\Scripts\python.exe -m pytest -v` from the repository root.
- Result: `30 passed, 1 warning in 1.98s`.
- API tests cover `/health` and `/leads` through FastAPI's TestClient with a mocked database; the suite makes no real Supabase or external HTTP calls.
- Confirmed `.env` and `.venv` are ignored by `.gitignore`.

**Warnings:**
- pytest-asyncio warns that the default fixture loop scope is not configured.
- Starlette warns that its TestClient integration with `httpx` is deprecated.
- Neither warning caused a test failure.

**Manual check (requires a configured `DATABASE_URL`):**
1. Run `uvicorn week3.app.main:app --reload`.
2. In another PowerShell window, run `Invoke-RestMethod -Uri http://localhost:8000/health` and confirm `status` is `ok`.
3. Run `Invoke-RestMethod -Uri http://localhost:8000/leads` and confirm it returns a JSON list from the configured database.
4. Stop the server with Ctrl+C.

**Before committing:** run `git status --short --untracked-files=all` and confirm `.env` and `.venv` are not listed. This workspace already contains unrelated, uncommitted Week 4 work; stage only the intended files.

## Weeks 4-16: Multi-tenant application through launch preparation

**What I built:**
- Week 4-5: Argon2/JWT authentication, organization membership, tenant-scoped API and tests, Alembic migration, Next.js/TypeScript/Tailwind UI, server-side API proxy with httpOnly cookie, lead search/CSV preview, settings and CORS.
- Week 6-8: polite public-business-site research with robots.txt and content limits, Pydantic research and email schemas, token budgets, draft approval, 30 fictional-lead email prompt evaluations and versioned reports.
- Week 9-12: Postgres job queue and worker, retries/dead jobs, Gmail OAuth token encryption, dry-run outbox/scheduler, unsubscribe and suppression handling, reply sync/classification, calendar free/busy, pipeline, analytics and prompt A/B routes.
- Week 13-14: Postgres RLS policies, Stripe test-mode checkout/webhook verification, plan limits, Sentry event sanitization, data export/deletion routes, privacy and unsubscribe UI, and a security checklist.
- Week 15-16: backend/frontend Dockerfiles and Compose, GitHub Actions, backup/restore script, fictional seed data, Locust workload, demo and beta templates, and a case-study draft. The local Compose configuration/build was not validated because Docker is not installed in this environment.

**Verification on 2026-11-02:**
- `.\.venv\Scripts\python.exe -m pytest -v`: **65 passed** (11 warnings; no failures).
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`: passed.
- `npm --prefix frontend audit --audit-level=moderate`: zero reported vulnerabilities.
- `.\.venv\Scripts\python.exe -m pip_audit`: no known vulnerabilities found; the tool emitted cache deserialization warnings but exited successfully.
- `.\.venv\Scripts\python.exe -m alembic -c alembic.ini history`: revision chain is `0001 -> 0002 -> 0003`. No migration was applied to the configured database.
- Email prompt evaluation: v2 won, 5.0/5 vs v1 at 4.0/5 across 30 fictional leads; weakest case improved from 4/5 to 5/5.
- Reply evaluation: 96/100 synthetic replies correctly classified (96%); all four errors were expected `interested` labeled `other`.
- Locust: isolated SQLite API, 20 users for 30 seconds; 1,768 requests, 0 failures, 60.21 requests/s, mean 9 ms, p95 22 ms, p99 46 ms, max 92 ms. This is a local smoke/load check, not hosted capacity evidence.
- `git check-ignore .env .venv` confirmed both local-only paths are ignored.

**Warnings and remaining manual work:**
- No Docker executable was available, so Compose validation and container builds were not run.
- No PostgreSQL migration, live RLS validation, Gmail send, Calendar call, Stripe live operation, Sentry account, or production hosting deployment was performed.
- Keep email dry-run enabled and use only fake/public business data. Free Gemini inputs may be used for Google's product improvement and may be human-reviewed.
- Consult [SECURITY.md](./SECURITY.md) for the automated evidence and manual release checklist; see [DECISIONS.md](./DECISIONS.md) for current free-tier caveats and hosting decisions.

**Exact verification commands:**
```powershell
.\.venv\Scripts\python.exe -m pytest -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=moderate
.\.venv\Scripts\python.exe -m pip_audit
.\.venv\Scripts\python.exe -m alembic -c alembic.ini history
.\.venv\Scripts\python.exe -m week4.evals.run
.\.venv\Scripts\python.exe -m week4.evals.reply_eval
```

**Manual checklist:** verify local signup/login and cookie behavior; use a backed-up disposable PostgreSQL instance to apply and inspect RLS migrations; confirm `SEND_MODE=dry-run`; verify only fictional demo rows; review Gmail Testing-mode setup and Stripe test keys; test backup/restore on disposable Postgres; and confirm `git status --short --untracked-files=all` does not list `.env` or `.venv`.

**Git commands (not run):**
```powershell
git status --short --untracked-files=all
git add <reviewed-files-only>
git commit -m "Complete OutreachOS Weeks 4-16"
```
