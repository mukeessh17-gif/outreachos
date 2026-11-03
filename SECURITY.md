# Security checklist

Status reviewed 2026-11-02. Automated checks describe this local development checkout, not a production security certification.

## Verified in code/tests

- [x] `.env` and `.venv` are ignored by Git (`git check-ignore .env .venv`). `.env.example` contains placeholders only. Recheck with `git status --short --untracked-files=all` before every commit.
- [x] Password hashing, signup/login, invalid credentials, password length validation, and auth throttling are tested in `week4/tests/test_auth.py`.
- [x] App-level tenant isolation is tested for cross-organization lead read, edit, and delete in `week4/tests/test_api.py`. This does not substitute for database RLS verification.
- [x] Pydantic validation, CSV rejected-row reporting, prompt output validation, unsafe claims and banned phrase rejection, and research source validation have tests in `week4/tests/`.
- [x] Dry-run sending, unsubscribe text, idempotency, suppression, live allowlist rejection, reply unsubscribe, bounce suppression, and Stripe test webhook signatures/idempotency are tested in `week4/tests/test_delivery_and_replies.py`.
- [x] OAuth token encryption/decryption is tested with a generated test-only Fernet key. The real key must exist only in `.env`; losing it makes stored Gmail credentials unrecoverable.
- [x] Security response headers and localhost-only CORS behavior are tested in `week4/tests/test_api.py`.
- [x] Optional Sentry setup disables default PII and removes URL query strings, authorization/cookie headers, and request bodies before forwarding. This is code-reviewed; no live Sentry account was configured.
- [x] `npm --prefix frontend audit --audit-level=moderate`: zero reported vulnerabilities.
- [x] `.venv\\Scripts\\python.exe -m pip_audit`: no known vulnerabilities found. pip-audit emitted cache deserialization warnings but exited successfully; audit data can change.
- [x] A 30-second local Locust run used 20 concurrent users and fictional data: 1,768 requests, 0 failures, 60.21 requests/second; aggregate average 9 ms, p95 22 ms, p99 46 ms, maximum 92 ms. This was an isolated SQLite development run, not a production capacity guarantee.

## Manual checks required before any public or real-data use

- [ ] Use a disposable, backed-up PostgreSQL database to apply Alembic migrations; inspect and test RLS policies using separate database roles and two organizations. SQLite tests do not exercise PostgreSQL RLS.
- [ ] Review all environment values locally. Confirm `SEND_MODE=dry-run`, test-only Stripe credentials, a unique `JWT_SECRET`, valid `FERNET_KEY`, and no `.env`/`.venv` in Git status. Never paste secrets into chat or logs.
- [ ] Run the local UI and verify signup/login, cookie attributes (httpOnly, SameSite=Lax), logout, allowed localhost CORS, and rejection of an untrusted browser origin.
- [ ] Keep Gmail OAuth in Testing mode with only the owner as a test user. Verify dry-run output first and keep live delivery disabled; before any owner-only live test, confirm allowlist, postal address, unsubscribe processing, suppression checks, and daily cap. Restricted Gmail scopes may require Google verification/security assessment for a public release.
- [ ] Verify Stripe only with test keys and test webhooks. Never enable live billing credentials.
- [ ] Run `scripts/backup_restore.py` against a disposable Postgres database and verify restoration before relying on backups. Restore is destructive and requires `--confirm`.
- [ ] Re-run `npm --prefix frontend audit` and `.venv\\Scripts\\python.exe -m pip_audit` immediately before release; dependency findings and free-tier terms change.
- [ ] Review the current privacy policy, legal basis, consent, data-retention, email, and unsubscribe obligations with qualified counsel before using customer or personal data.

## Data-use warning

The Gemini unpaid tier may use prompts and responses to improve Google products, and Google may have human reviewers process this content. Use only fake or public business information with the free tier. Never send real customer, personal, confidential, or sensitive data. Gmail and Stripe remain optional integrations; email defaults to dry-run and payment integration is test-mode only.
