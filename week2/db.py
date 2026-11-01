# week2/db.py
# The ONLY file in OutreachOS that opens database connections.
# If you change how you connect to Postgres, change only this file.
# All other files call get_engine() to get a connection.

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load DATABASE_URL from .env (never from code, never printed).
load_dotenv()

# The engine is a pool of database connections. It holds several open
# connections ready to reuse, so your program does not open a brand-new
# connection to Postgres every time it runs a query.
_engine = None


def get_engine():
    """Return a SQLAlchemy engine, creating it once and reusing it."""
    global _engine
    if _engine is None:
        # Read the connection string from the environment.
        # DATABASE_URL must be set in .env before this runs.
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not found in .env file.")
        # create_engine builds the connection pool. pool_pre_ping=True
        # checks that a connection is still alive before using it.
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine