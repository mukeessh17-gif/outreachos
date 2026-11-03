# Decisions - OutreachOS Week 3

These are sensible choices I made so you don't have to. Change them if your setup differs.

## Database connection
- `DATABASE_URL` uses the `postgresql+psycopg://` prefix (required by `psycopg` v3 with SQLAlchemy).
- It comes from Supabase: Connect → Connection string (pooled/session).
- Never printed, logged, or committed.

## Testing
- Tests use a **mocked database layer** (unittest.mock), never a real Supabase project.
- No real network calls in pytest; HTTP calls are mocked with `unittest.mock.AsyncMock`.
- Free tier only: `jsonplaceholder.typicode.com` for async demo data.

## Package layout
- `week3/app/` is a Python package (`__init__.py` exists).
- `week3/app/main.py` adds `..` (the repo root) to `sys.path` so it can import `week2.db.get_engine()`.
- `week3/tests/` is a separate package with `__init__.py`.

## Logging
- Console handler + rotating file handler writing to `logs/app.log`.
- `logs/` is in `.gitignore`.
- Each log line includes a timestamp, level, and request ID.
- Request bodies and secrets are never logged.

## Pydantic
- Pydantic v2 style (`from pydantic import BaseModel, Field`).
- `LeadCreate` and `LeadOut` models with field constraints.

## Rate limiting
- `asyncio.Semaphore(5)` limits concurrent HTTP requests so free APIs are not overwhelmed.

## Weeks 4-16 decisions (reviewed 2026-11-02)

- The authenticated application entrypoint is `week4.main:app`. The older Week 3 API remains unchanged for the original lesson but is not the app to use for multi-tenant work.
- Authentication uses Argon2id password hashes and short-lived JWTs. The Next.js server-side proxy keeps the bearer token in an httpOnly, SameSite=Lax cookie instead of browser storage. CORS is restricted to localhost origins.
- `users` represents global login identities; tenant membership is held in `memberships`. Business/customer records and all tenant-specific tables carry `org_id` and have app-level filters. Postgres RLS is added as a second layer. SQLite tests do not validate RLS; run and inspect the migration only on a backed-up development Postgres database.
- Gemini model selection is centralized in `week1/llm.py` as `gemini-3.8-flash`. Google's official docs list this as a stable model with a free tier as of 2026-11-02. Google's unpaid-service terms say inputs and outputs may be used to improve products and may be reviewed by humans; never submit real customer, personal, confidential, or sensitive data.
- The frontend proxy stores the access token in an httpOnly cookie. The browser never receives the raw JWT in a response body after login/signup.
- Google OAuth scopes are minimized to `gmail.send`, `gmail.readonly`, and `calendar.freebusy`. Gmail readonly is a restricted scope. Keep the consent screen in Testing mode and add only the owner's account; public release requires separate Google policy/verification review and potentially a security assessment.
- `SEND_MODE=dry-run` remains the default. Gmail OAuth credentials are encrypted with Fernet. Live sending requires an explicit owner-only allowlist, and the same recipient must pass suppression checks at schedule and delivery time. The scheduler processes one organization's due messages; a crash while a message is `processing` requires operator reconciliation rather than an automatic resend.
- Stripe integration accepts only a test API key and rejects webhook events marked live. Checkout is disabled until a test price ID is configured.
- The free local Docker Compose stack is the recommended full-stack development environment. A public free deployment is only a demo, not reliable production hosting: a free Render web service sleeps after 15 minutes without traffic, has an ephemeral filesystem and 750 shared workspace instance-hours/month; a free Render Postgres database is 1 GB and expires after 30 days. Supabase Free has 500 MB DB storage and pauses projects after one week of inactivity. Vercel Hobby is positioned for personal projects and has usage limits; it does not provide the required persistent Postgres plus always-on worker. No reliable, always-on public hosting option for the full backend/worker/database stack was identified without paying.
- Sentry is optional. The free Developer plan is currently listed as one user with 50,000 monthly errors, 5 GB of logs, and a 30-day lookback; limits can change. Event filtering removes query strings, cookies, authorization headers, and request bodies before forwarding.
- The build pipeline provides tests, type checking, and production frontend builds. Database backup/restore uses the free PostgreSQL CLI tools; restore requires an explicit confirmation flag and is destructive.

### Official service references checked 2026-11-02

- [Gemini models](https://ai.google.dev/gemini-api/docs/models) and [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API terms and unpaid-service data use](https://ai.google.dev/gemini-api/terms)
- [Gmail API OAuth scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [Calendar API OAuth scopes](https://developers.google.com/workspace/calendar/api/auth), and [Google restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
- [Render free services and limitations](https://render.com/docs/free)
- [Supabase plans and free project limits](https://supabase.com/pricing)
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [Sentry pricing](https://sentry.io/pricing/)