# app/services/db_setup.py
# Utility script to create or verify the database schema.

from app.services.db import get_conn
from app.services.sql_schema import SCHEMA_SQL

def run_schema():
    """Execute the schema SQL to create or verify required tables."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()

if __name__ == "__main__":
    run_schema()
    print("Schema created/verified.")
