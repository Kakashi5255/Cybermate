# app/routes/meta.py
from fastapi import APIRouter
from typing import List, Dict, Any, Tuple
from app.services.db import get_conn
from app.services.population import POPULATION

router = APIRouter(tags=["meta"])

@router.get("/filters")
def filters() -> Dict[str, Any]:
    """
    Returns distinct values the frontend needs to build dropdowns:
      - states, scam_types, categories, contact_methods
      - years: {min, max, list}
      - last5_years (as used by backend defaults)
      - latest_year (for the 2025-locked top3; falls back to max)
    """
    with get_conn() as conn, conn.cursor() as cur:
        # States
        cur.execute("SELECT DISTINCT state FROM scam_stats WHERE state IS NOT NULL ORDER BY state;")
        states = [r[0] for r in cur.fetchall() if r[0]]

        # Scam types / categories / contact methods
        cur.execute("SELECT DISTINCT scam_type FROM scam_stats WHERE scam_type IS NOT NULL ORDER BY scam_type;")
        scam_types = [r[0] for r in cur.fetchall() if r[0]]

        cur.execute("SELECT DISTINCT category FROM scam_stats WHERE category IS NOT NULL ORDER BY category;")
        categories = [r[0] for r in cur.fetchall() if r[0]]

        cur.execute("SELECT DISTINCT contact_method FROM scam_stats WHERE contact_method IS NOT NULL ORDER BY contact_method;")
        contact_methods = [r[0] for r in cur.fetchall() if r[0]]

        # Years
        cur.execute("SELECT MIN(year), MAX(year) FROM scam_stats;")
        y_min, y_max = cur.fetchone()
        y_min = int(y_min or 0)
        y_max = int(y_max or 0)
        years_list = list(range(y_min, y_max + 1)) if y_min and y_max else []

        # Last 5 years (backend default window)
        last5 = [y for y in range(y_max, y_max - 5, -1)] if y_max else []

    # Top 3 by loss is locked to 2025 (fallback to latest in data)
    top3_year = 2025 if (y_max and 2025 <= y_max) else y_max

    return {
        "states": states,
        "scam_types": scam_types,
        "categories": categories,
        "contact_methods": contact_methods,
        "years": {"min": y_min, "max": y_max, "list": years_list},
        "last5_years": last5,
        "latest_year": y_max,
        "top3_year_locked": top3_year
    }

@router.get("/populations")
def populations() -> Dict[str, Any]:
    """
    Returns the population mapping used for likelihood tiles so the UI
    can show tooltips / disclaimers or compute client-side if needed.
    """
    return {"population": POPULATION}
