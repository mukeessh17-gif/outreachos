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