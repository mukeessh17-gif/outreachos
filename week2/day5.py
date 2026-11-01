# Week 2 Day 5: Save Real Leads
# OutreachOS - AI sales outreach tool
# Run this file from inside the week2/ folder.
# Free tools only: jsonplaceholder.typicode.com (no API key) + Supabase Postgres.

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from db import get_engine

# ==================================================================
# Logging setup (not print)
# ==================================================================
# logging lets you record how many rows were inserted, skipped, or failed,
# with timestamps and levels (INFO, WARNING, ERROR). It is better than print
# because you can turn it on or off without changing code.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("outreachos")


# ==================================================================
# 1. save_company(engine, company_dict)
# ==================================================================
# INSERT one company and return the new id.
# ON CONFLICT (name) DO NOTHING means: if a company with the same name
# already exists, skip the insert instead of crashing or making a duplicate.
def save_company(engine, company_dict):
    with engine.connect() as connection:
        sql = text("""
            INSERT INTO companies (name, city, employees, has_website)
            VALUES (:name, :city, :employees, :has_website)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """)
        result = connection.execute(sql, {
            "name": company_dict.get("name"),
            "city": company_dict.get("city"),
            "employees": company_dict.get("employees"),
            "has_website": company_dict.get("has_website", False),
        })
        row = result.fetchone()
        connection.commit()

        if row is None:
            # ON CONFLICT skipped the insert because a row with that name exists.
            logger.warning("Skipped duplicate: %s", company_dict.get("name"))
            return None
        return row[0]

import requests


# ==================================================================
# 2. Fetch 50 records from a free public API
# ==================================================================
# jsonplaceholder.typicode.com/users returns fake user data.
# We treat each user as a lead. Do NOT use real business or personal data.
def fetch_fake_leads(limit=50):
    url = "https://jsonplaceholder.typicode.com/users"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            users = response.json()
            leads = []
            for user in users[:limit]:
                leads.append({
                    "name": user["name"],
                    "city": user["address"]["city"],
                    "employees": len(user["name"]) * 2,
                    "has_website": bool(user["website"]),
                })
            return leads
        else:
            logger.error("API returned status %s", response.status_code)
            return []
    except Exception as error:
        logger.error("Could not fetch leads: %s", error)
        return []


# ==================================================================
# 3. Batch insert in one transaction, one commit
# ==================================================================
# Doing 50 separate commits means 50 round-trips to the database. One
# transaction with one commit is much faster because Postgres writes
# everything in a single batch.
def import_leads(engine, leads):
    inserted = 0
    skipped = 0
    failed = 0

    with engine.connect() as connection:
        # Begin one transaction. All inserts wait here until we commit.
        trans = connection.begin()
        try:
            for lead in leads:
                sql = text("""
                    INSERT INTO companies (name, city, employees, has_website)
                    VALUES (:name, :city, :employees, :has_website)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                """)
                result = connection.execute(sql, {
                    "name": lead.get("name"),
                    "city": lead.get("city"),
                    "employees": lead.get("employees"),
                    "has_website": lead.get("has_website", False),
                })
                row = result.fetchone()
                if row is None:
                    skipped += 1
                    logger.warning("Skipped duplicate: %s", lead.get("name"))
                else:
                    inserted += 1
                    logger.info("Inserted: %s (id=%s)", lead.get("name"), row[0])

            # One commit saves all inserts at once.
            trans.commit()
            logger.info("Done. Inserted=%d, Skipped=%d, Failed=%d", inserted, skipped, failed)
        except Exception as error:
            # If anything fails, roll back the whole batch so we don't save half the data.
            trans.rollback()
            logger.error("Batch failed, rolled back: %s", error)
            failed = len(leads) - inserted - skipped
            logger.info("Done. Inserted=%d, Skipped=%d, Failed=%d", inserted, skipped, failed)

    return inserted, skipped, failed


# ==================================================================
# 4. Run the import
# ==================================================================
if __name__ == "__main__":
    try:
        engine = get_engine()
        leads = fetch_fake_leads(50)
        if leads:
            logger.info("Fetched %d leads from API", len(leads))
            import_leads(engine, leads)
        else:
            logger.warning("No leads to import.")
    except Exception as error:
        # Friendly message, never shows the password.
        logger.error("Could not connect to the database. Check .env and Supabase.")


# ==================================================================
# 5. TODO for you
# ==================================================================
# TODO: Write a function that re-reads the AI summary from Week 1's llm.py
# for 5 companies and saves it into lead_research.
#   - import ask_llm from week1/llm.py
#   - SELECT 5 companies from Postgres
#   - for each, call ask_llm with a prompt asking for a 3-sentence summary
#   - INSERT into lead_research (company_id, summary, confidence)
#   - WARNING: the free Gemini tier may send your inputs to Google.
#     Use only fake or public company data. Never real customer data.
#
# def save_ai_summaries(engine):
#     ...

print("Day 5 setup complete. Add UNIQUE(name) to companies if not present, then run.")