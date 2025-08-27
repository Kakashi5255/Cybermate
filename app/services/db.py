# app/services/db.py
import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv

# ensure .env is loaded no matter which module is executed first
load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError(
        "SUPABASE_DB_URL is not set. Check your .env and that it is in the project root."
    )

@contextmanager
def get_conn():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()
