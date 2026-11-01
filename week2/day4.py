# Week 2 Day 4: Connect Python to Postgres
# OutreachOS - AI sales outreach tool
# Run this file from inside the week2/ folder.
# You need a Supabase project running and DATABASE_URL in .env.

# ==================================================================
# 1. Connection string, .env, connection pool (6 lines)
# ==================================================================
# A connection string (DATABASE_URL) tells your program where the database
# lives, what port, which database name, and the username/password.
# It goes in .env because it contains secrets; committing it to Git would
# expose your database to anyone who reads your history.
# A connection pool is a set of open database connections kept ready to
# reuse. It avoids the slow work of opening a new connection for every query.

# ==================================================================
# 2. Find your connection string in Supabase
# ==================================================================
# In the Supabase dashboard: Project Settings -> Database.
# Look for "Connection string" and choose the "Connection string (pooled)"
# option if you connect from your home/work network.
# Copy it into .env as:
#   DATABASE_URL=postgresql://postgres:<password>@<host>:<port>/postgres
# Never print DATABASE_URL. Never paste it into chat.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from db import get_engine


# ==================================================================
# 5. SQL injection explained (5 lines)
# ==================================================================
# SQL injection happens when you build a query with f-strings or string
# concatenation using user input. Example:
#   query = f"SELECT * FROM companies WHERE name = '{user_input}'"
# If user_input is: Kovai' OR '1'='1
# the query becomes: SELECT * FROM companies WHERE name = 'Kovai' OR '1'='1'
# which returns every company. Always use parameterized queries (:name)
# so user input is treated as data, not as part of the SQL command.

# ==================================================================
# 6. Connect, read version, SELECT, INSERT with parameters
# ==================================================================
try:
    # Get the connection pool (the only place connections are opened).
    engine = get_engine()

    # Open one connection from the pool. "with" closes it automatically.
    with engine.connect() as connection:

        # Ask Postgres for its version.
        # text() wraps raw SQL. No user input here, just a built-in function.
        result = connection.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print("Connected to Postgres:", version)

        # SELECT all companies using SQLAlchemy Core.
        result = connection.execute(text("SELECT id, name, city, employees, has_website FROM companies"))
        companies = result.fetchall()
        print("\nCompanies:")
        for row in companies:
            print(f"  {row.id} | {row.name} | {row.city} | {row.employees} | {row.has_website}")

        # INSERT one company using PARAMETERS (:name, :city, ...).
        # Never use f-strings to put variables inside SQL.
        insert_sql = text("""
            INSERT INTO companies (name, city, employees, has_website)
            VALUES (:name, :city, :employees, :has_website)
        """)
        connection.execute(insert_sql, {
            "name": "Demo Company",
            "city": "Coimbatore",
            "employees": 10,
            "has_website": True,
        })

        # Commit saves the INSERT permanently. Without commit, it rolls back.
        connection.commit()
        print("\nInserted Demo Company and committed.")

except Exception as error:
    # Friendly message. Never print error details that could reveal the password.
    print("Sorry, could not connect to the database. Check your .env and Supabase project.")

# ==================================================================
# 8. TODO for you
# ==================================================================
# TODO: Write get_good_leads(engine) here.
# It should:
#   - use engine.connect() to open a connection
#   - run a parameterized SELECT for companies where employees >= 5
#     AND employees <= 20 AND has_website = TRUE
#   - return the results as a list of dictionaries
#   - wrap it in try/except and print a friendly message on failure
#
# def get_good_leads(engine):
#     ...

print("Day 4 setup complete. Configure DATABASE_URL in .env and run again.")