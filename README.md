# OutreachOS

AI-powered B2B sales outreach tool. Week 1 builds the core pieces: lists/dictionaries, JSON storage, HTTP APIs, and a free LLM for company summaries.

## What it does

- Stores lead information in dictionaries and lists (Day 2)
- Saves and loads leads from a JSON file (Day 3)
- Calls public HTTP APIs with error handling (Day 4)
- Calls a free LLM API (Gemini) for company summaries via `week1/llm.py` (Day 5)
- CLI tool that ties it all together: enter a company, get a summary, save it (Checkpoint)

## How to install

1. Open PowerShell in the `outreachos` folder.
2. Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `outreachos` folder (not inside `week1`) with one line:
   ```
   GEMINI_API_KEY=your-key-here
   ```
   Get a free key from [Google AI Studio](https://aistudio.google.com/) — do not link a billing account.
   Never share your key. `.env` is in `.gitignore` and will not be committed.
5. Verify the model name in `week1/llm.py` matches a current free-tier model in Google AI Studio.

## How to run

From inside the `week1` folder:

- Run a single day:
  ```
  python day2.py
  python day3.py
  python day4.py
  python day5.py
  ```
- Run the checkpoint CLI tool:
  ```
  python outreach_cli.py
  ```
  (You will need to write the main loop and `summarize_company()` first — they are left as TODO skeletons.)

## Example output

```
Enter a company name: Kovai Textiles
Summary: Kovai Textiles is a textile manufacturer based in Coimbatore...
Note: This summary is based on the model's general knowledge and may be wrong.
Input tokens: 12
Output tokens: 48
Saved 1 leads to leads.json
Enter a company name: quit
Goodbye!
```

## Safety

- `.env` contains your API key and is listed in `.gitignore`. Never commit it.
- `.venv/` is also in `.gitignore`. It can be rebuilt from `requirements.txt`.
- Never paste real customer data into a free-tier LLM key.

## Week 2: SQL and Postgres

Week 2 adds a relational database (Supabase Postgres, free tier) to store companies, contacts, and AI research.

### What it does

- Stores companies and contacts in Postgres tables (Days 1–2)
- Designs a normalized schema with indexes and constraints (Day 3)
- Connects Python to Postgres with SQLAlchemy Core (Day 4)
- Imports 50 leads from a free public API in one transaction (Day 5)
- CLI tool to list, search, add, and JOIN companies with contacts (Checkpoint)

### How to install (Week 2)

1. Create a free Supabase project at [supabase.com](https://supabase.com/) — no credit card required.
2. Save your database password privately. Never paste it into chat or code.
3. Get your connection string from Supabase: Connect → Connection string (pooled/session).
4. Add `DATABASE_URL` to your `.env` file:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:<password>@<host>:<port>/postgres
   ```
   Use `postgresql+psycopg://` as the prefix (required by `psycopg` v3).
5. Rebuild the database from schema: copy `week2/sql/schema.sql` into the Supabase SQL Editor and run it.
6. Install new dependencies:
   ```
   pip install -r requirements.txt
   ```

### How to run (Week 2)

From inside the `week2` folder:

- Run the SQL files in the Supabase SQL Editor: `day1.sql`, `day2.sql`, `schema.sql`
- Run the Python files:
  ```
  python day4.py
  python day5.py
  python leads_cli.py
  ```
  (You will need to write the menu loop in `leads_cli.py` first — it is left as a TODO skeleton.)

### Rebuilding the database from scratch

Free Supabase projects can pause after 7 days of inactivity. To rebuild:

1. Open `week2/sql/schema.sql` in the Supabase SQL Editor.
2. Run it — it drops and recreates `companies`, `contacts`, and `lead_research`.
3. **Warning:** this deletes all data. Only run on your dev database.

### Example output

```
--- OutreachOS Leads CLI ---
1. List all companies
2. Search companies by name
3. Add a company
4. Show companies with contacts
5. Quit
Choose an option: 1

1 | Kovai Textiles | Coimbatore | 15 | True
2 | Peelamedu Hardware | Coimbatore | 30 | False
...
Choose an option: 5
Goodbye!
```

## Safety (all weeks)

- `.env` contains your API key and database URL. Both are in `.gitignore`. Never commit them.
- `.venv/` is also in `.gitignore`. It can be rebuilt from `requirements.txt`.
- Never paste real customer data into a free-tier LLM key or a free database.