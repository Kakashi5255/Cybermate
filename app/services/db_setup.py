from app.services.db import get_conn
from app.services.sql_schema import SCHEMA_SQL

def run_schema():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()

if __name__ == "__main__":
    run_schema()
    print("Schema created/verified.")
