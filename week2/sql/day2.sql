-- ==================================================================
-- Week 2 Day 2: UPDATE, DELETE, JOIN
-- OutreachOS - AI sales outreach tool
-- Free tools only: Supabase Postgres (no credit card required)
-- ==================================================================

-- ==================================================================
-- 1. UPDATE and DELETE with WHERE
-- ==================================================================
-- WARNING: Never run UPDATE or DELETE without a WHERE clause.
-- Without WHERE, the change applies to EVERY row in the table.
-- Always test your WHERE condition with a SELECT first.

-- Example: change the employee count for one company.
-- First, test which rows will match:
SELECT id, name, employees FROM companies
WHERE name = 'Kovai Textiles';

-- If the SELECT returns the right row, run the UPDATE:
UPDATE companies
SET employees = 16
WHERE name = 'Kovai Textiles';

-- Example: delete one company.
-- Test first:
SELECT id, name FROM companies
WHERE name = 'RS Puram Stores';

-- Then delete:
DELETE FROM companies
WHERE name = 'RS Puram Stores';

-- ==================================================================
-- Safe example with BEGIN ... ROLLBACK
-- ==================================================================
-- BEGIN starts a transaction. ROLLBACK undoes everything since BEGIN.
-- This lets you try a change safely without permanently altering data.
BEGIN;

UPDATE companies
SET employees = 999
WHERE name = 'Peelamedu Hardware';

-- Check what changed:
SELECT * FROM companies
WHERE name = 'Peelamedu Hardware';

-- Undo the change (remove the two dashes to actually run):
-- ROLLBACK;

-- If instead you want to keep the change, use COMMIT instead of ROLLBACK.
-- COMMIT;

-- ==================================================================
-- 2. Create a contacts table with a foreign key to companies
-- ==================================================================
-- company_id points to the id column in the companies table.
-- That foreign key means every contact must belong to a real company.
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT
);

-- Insert 8 contacts using FAKE names and emails only (@example.com).
-- No real personal data.
INSERT INTO contacts (company_id, full_name, email, role) VALUES
    (1, 'Alex Kumar', 'alex.kumar@example.com', 'Owner'),
    (1, 'Priya Singh', 'priya.singh@example.com', 'Manager'),
    (2, 'Ravi Menon', 'ravi.menon@example.com', 'Founder'),
    (3, 'Sita Rao', 'sita.rao@example.com', 'Accountant'),
    (3, 'Arun Iyer', 'arun.iyer@example.com', 'Sales'),
    (4, 'Meena Das', 'meena.das@example.com', 'Operator'),
    (5, 'Karan Verma', 'karan.verma@example.com', 'Partner'),
    (5, 'Lakshmi Nair', 'lakshmi.nair@example.com', 'Assistant');

-- ==================================================================
-- 3. What is a JOIN? (plain English with a text drawing)
-- ==================================================================
-- A JOIN combines rows from two tables using a related column.
-- Think of it like matching two spreadsheets on a shared ID.

-- companies table                    contacts table
-- id | name            id | company_id | full_name
-- -- | --------------  -- | ---------- | -----------
--  1 | Kovai Textiles   1 | 1          | Alex Kumar
--  2 | Peelamedu HW     2 | 1          | Priya Singh
--  3 | RS Puram Stores  3 | 2          | Ravi Menon

-- INNER JOIN keeps only rows that match in BOTH tables.
-- A company with no contacts will not appear.
-- A contact with no matching company will not appear.

-- LEFT JOIN keeps ALL rows from the left table (companies),
-- even if there is no matching row in the right table (contacts).
-- Missing contact fields show as NULL.

-- INNER JOIN example:
SELECT companies.name, contacts.full_name, contacts.email
FROM companies
INNER JOIN contacts ON companies.id = contacts.company_id;

-- LEFT JOIN example:
SELECT companies.name, contacts.full_name, contacts.email
FROM companies
LEFT JOIN contacts ON companies.id = contacts.company_id;

-- ==================================================================
-- 4. Practice queries
-- ==================================================================
-- Count contacts per company (GROUP BY):
SELECT companies.name, COUNT(contacts.id) AS contact_count
FROM companies
LEFT JOIN contacts ON companies.id = contacts.company_id
GROUP BY companies.id, companies.name
ORDER BY contact_count DESC;

-- Companies with no contacts:
SELECT companies.name
FROM companies
LEFT JOIN contacts ON companies.id = contacts.company_id
WHERE contacts.id IS NULL;

-- Companies with between 5 and 20 employees:
SELECT name, employees
FROM companies
WHERE employees >= 5 AND employees <= 20;

-- ==================================================================
-- 5. TODO for you
-- ==================================================================
-- TODO: Write a query that lists company name, contact name and email
-- for companies that have a website AND 5-20 employees.
-- Use INNER JOIN and a WHERE clause with both conditions.
--
-- Example skeleton (fill in the details):
--
-- SELECT companies.name, contacts.full_name, contacts.email
-- FROM companies
-- INNER JOIN contacts ON companies.id = contacts.company_id
-- WHERE companies.has_website = TRUE
--   AND companies.employees >= 5
--   AND companies.employees <= 20;

-- End of day2.sql