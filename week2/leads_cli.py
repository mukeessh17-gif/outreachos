# Week 2 Checkpoint: leads_cli.py
# OutreachOS - AI sales outreach tool
# Run this file from inside the week2/ folder.
# You write the menu loop. I provide the SQL helper functions.
# Free tools only: Supabase Postgres.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from db import get_engine


# ==================================================================
# SQL helper functions (you can use these in your menu loop)
# ==================================================================


def list_all_companies(engine):
    """Return all companies as a list of dictionaries."""
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT id, name, city, employees, has_website
            FROM companies
            ORDER BY id
        """))
        return [dict(row._mapping) for row in result]


def search_companies_by_name(engine, search_text):
    """Return companies whose name contains search_text (case-insensitive)."""
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT id, name, city, employees, has_website
            FROM companies
            WHERE name ILIKE :search
            ORDER BY id
        """), {"search": f"%{search_text}%"})
        return [dict(row._mapping) for row in result]


def add_company(engine, name, city, employees, has_website):
    """Insert a new company and return its new id. Returns None if duplicate."""
    with engine.connect() as connection:
        sql = text("""
            INSERT INTO companies (name, city, employees, has_website)
            VALUES (:name, :city, :employees, :has_website)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """)
        result = connection.execute(sql, {
            "name": name,
            "city": city,
            "employees": employees,
            "has_website": has_website,
        })
        row = result.fetchone()
        connection.commit()
        if row is None:
            return None
        return row[0]


def list_companies_with_contacts(engine):
    """Return a JOIN of companies with their contacts."""
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT companies.id, companies.name, companies.city,
                   contacts.full_name, contacts.email, contacts.role
            FROM companies
            LEFT JOIN contacts ON companies.id = contacts.company_id
            ORDER BY companies.id, contacts.id
        """))
        return [dict(row._mapping) for row in result]


# ==================================================================
# TODO: Write your menu loop here.
# ==================================================================
# It should:
#   - get the engine with get_engine()
#   - loop:
#       - print a menu: 1) List all companies, 2) Search by name,
#         3) Add a company, 4) Show companies with contacts, 5) Quit
#       - read the user's choice
#       - call the right helper function and print the results nicely
#       - handle empty input and bad choices without crashing
#       - exit when the user chooses Quit
#
# Example skeleton (fill in the details yourself):
#
# engine = get_engine()
#
# while True:
#     print("\n--- OutreachOS Leads CLI ---")
#     print("1. List all companies")
#     print("2. Search companies by name")
#     print("3. Add a company")
#     print("4. Show companies with contacts")
#     print("5. Quit")
#     choice = input("Choose an option: ")
#     ...
#
#     if choice == "5":
#         print("Goodbye!")
#         break

print("leads_cli.py ready. TODO: write the menu loop above.")