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
