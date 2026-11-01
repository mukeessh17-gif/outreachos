-- ==================================================================
-- Week 2 Day 3: Database Schema
-- OutreachOS - AI sales outreach tool
-- Free tools only: Supabase Postgres
-- Run this in the Supabase SQL Editor to rebuild your dev database.
-- ==================================================================

-- ==================================================================
-- 1. Schema design principles (8 lines)
-- ==================================================================
-- Normalization means one fact lives in one place. A company's name
-- is stored only in the companies table, never repeated in contacts.
-- A foreign key protects data by refusing to link a contact to a
-- company that does not exist (no orphan rows).
-- An index is like a book index: it helps the database find rows
-- faster without scanning every row, at the cost of slightly slower writes.

-- ==================================================================
-- 2. Drop existing tables (DEV ONLY - loud warning)
-- ==================================================================
-- WARNING: This deletes ALL data in these tables. Run ONLY on your
-- development database. Never run this on production data.
DROP TABLE IF EXISTS lead_research CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- ==================================================================
-- 3. Companies table
-- ==================================================================
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    city TEXT,
    employees INTEGER,
    has_website BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================================================================
-- 4. Contacts table
-- ==================================================================
-- company_id references companies.id (foreign key).
-- NOT NULL on company_id means every contact must belong to a company.
-- UNIQUE on (company_id, email) means one email per company,
-- but the same email can appear for different companies.
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT,
    UNIQUE (company_id, email)
);

-- ==================================================================
-- 5. Lead research table
-- ==================================================================
-- company_id links each research row to one company.
-- NOT NULL on company_id and summary means those must always be present.
-- confidence is a number from 0 to 100.
-- created_at records when the research was saved.
CREATE TABLE lead_research (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    summary TEXT NOT NULL,
    confidence INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================================================================
-- 6. Indexes for faster lookups
-- ==================================================================
-- Index on company_id in contacts: speeds up "find all contacts for company X".
-- Index on company_id in lead_research: speeds up "find research for company X".
CREATE INDEX idx_contacts_company_id ON contacts(company_id);
CREATE INDEX idx_lead_research_company_id ON lead_research(company_id);

-- ==================================================================
-- 7. TODO for you
-- ==================================================================
-- TODO: Add a "status" column to the contacts table with a CHECK constraint
-- that allows only these values: 'new', 'contacted', 'replied', 'unsubscribed'.
-- Example syntax:
--   ALTER TABLE contacts ADD COLUMN status TEXT;
--   ALTER TABLE contacts ADD CONSTRAINT contacts_status_check
--     CHECK (status IN ('new', 'contacted', 'replied', 'unsubscribed'));
-- Write the SQL yourself.

-- End of schema.sql