# app/services/db.py
import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv
import logging

# ensure .env is loaded no matter which module is executed first
load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError(
        "SUPABASE_DB_URL is not set. Check your .env and that it is in the project root."
    )

# basic logger setup (dashboard debugging)
logger = logging.getLogger("dashboard.db")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

@contextmanager
def get_conn():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()

def run_query(sql: str, params=None, fetch: str = "all"):
    """Helper for dashboard debugging. Returns query results and logs SQL + params."""
    with get_conn() as conn, conn.cursor() as cur:
        logger.info("SQL: %s", sql.replace("\n", " ").strip())
        logger.info("Params: %s", params)
        cur.execute(sql, params or [])
        if fetch == "one":
            return cur.fetchone()
        return cur.fetchall()
