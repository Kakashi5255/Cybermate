# app/services/db.py
# Database service module for managing PostgreSQL connections and queries.

import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

# Load environment variables so DB connection works regardless of entry point
load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError(
        "SUPABASE_DB_URL is not set. Check your .env file in the project root."
    )

# Configure a basic logger for database interactions
logger = logging.getLogger("dashboard.db")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

@contextmanager
def get_conn():
    """Provide a managed PostgreSQL connection."""
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()

def run_query(sql: str, params=None, fetch: str = "all"):
    """
    Execute a SQL query with optional parameters.
    Logs the query and returns results based on fetch mode.
      - fetch="one" → return single row
      - fetch="all" → return all rows
    """
    with get_conn() as conn, conn.cursor() as cur:
        logger.info("SQL: %s", sql.replace("\n", " ").strip())
        logger.info("Params: %s", params)
        cur.execute(sql, params or [])
        if fetch == "one":
            return cur.fetchone()
        return cur.fetchall()
