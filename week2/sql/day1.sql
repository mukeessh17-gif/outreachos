-- ==================================================================
-- Week 2 Day 1: Supabase and First SQL
-- OutreachOS - AI sales outreach tool
-- Free tools only: Supabase free tier (no credit card required)
-- ==================================================================

-- ==================================================================
-- 1. Plain-English explanation
-- ==================================================================
-- A database is like a digital filing cabinet that stores information
-- in an organized way so programs can find and change it quickly.
--   - Table: one sheet in the cabinet, holding one kind of thing (e.g., companies).
--   - Row: one record in the table (e.g., one company's info).
--   - Column: one piece of info in each row (e.g., the company's name).
-- Postgres (PostgreSQL) is a free, open-source database that is very
-- popular and reliable. Supabase is a hosting service that gives you
-- a Postgres database plus a web interface to run SQL.
-- A database beats a JSON file once data grows because:
--   - Searching is fast (indexes) instead of reading the whole file.
--   - Many users can read/write at the same time without corrupting data.
--   - Safety: transactions, backups, and user permissions protect your data.

-- ==================================================================
-- 2. Supabase free account (do this in your browser, not in SQL)
-- ==================================================================
-- 1. Go to supabase.com and sign up for a FREE account. No credit card needed.
-- 2. Create a new project. Pick a name and a region near you.
-- 3. Supabase will generate a database password. SAVE IT somewhere safe.
--    NEVER paste it into chat, NEVER put it in code, NEVER commit it to Git.
-- 4. Confirm the current free-plan limits and the 7-day inactivity pause
--    at supabase.com/pricing before you start.
-- 5. Open the SQL Editor in the Supabase dashboard to run the queries below.

-- ==================================================================
-- 3. Create the companies table
-- ==================================================================
-- id: primary key (unique ID for each row, auto-generated)
-- name: company name (text)
-- city: where the company is located (text)
-- employees: number of employees (whole number)
-- has_website: true or false (boolean)
-- created_at: when the row was added (date and time with time zone)
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    employees INTEGER,
    has_website BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================================================================
-- Insert 5 Coimbatore sample rows
-- ==================================================================
INSERT INTO companies (name, city, employees, has_website) VALUES
    ('Kovai Textiles', 'Coimbatore', 15, TRUE),
    ('Peelamedu Hardware', 'Coimbatore', 30, FALSE),
    ('RS Puram Stores', 'Coimbatore', 8, TRUE),
    ('Ganapathy Motors', 'Coimbatore', 50, FALSE),
    ('Sowripalayam Traders', 'Coimbatore', 12, TRUE);

-- ==================================================================
-- SELECT all companies
-- ==================================================================
-- This returns every column of every row in the companies table.
-- Predict what you will see before you run it.
SELECT * FROM companies;

-- ==================================================================
-- SELECT with WHERE (filter rows)
-- ==================================================================
-- This returns only companies that have a website.
-- Predict how many rows you will see before you run it.
SELECT * FROM companies
WHERE has_website = TRUE;

-- ==================================================================
-- SELECT with ORDER BY (sort rows)
-- ==================================================================
-- This returns companies sorted by employee count, smallest first.
-- Predict which company will be first before you run it.
SELECT * FROM companies
ORDER BY employees ASC;

-- ==================================================================
-- 4. Primary keys and data types (5 lines)
-- ==================================================================
-- A primary key is a unique ID for each row - no two rows share the same id.
-- TEXT stores words/sentences. INTEGER stores whole numbers.
-- BOOLEAN stores TRUE or FALSE. TIMESTAMPTZ stores date and time with time zone.
-- NOT NULL means the column must always have a value (cannot be empty).

-- ==================================================================
-- 5. Before you run each SELECT, predict what it returns
-- ==================================================================
-- Write down your guess on paper, then run the query and compare.
-- This helps you learn how SQL filters and sorts data.

-- End of day1.sql