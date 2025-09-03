# app/routes/meta.py
# API endpoints for metadata required by the frontend.
# Provides filter options (states, scam types, categories, contact methods, years)
# and population mappings used for likelihood calculations.

from fastapi import APIRouter
from typing import Dict, Any
from app.services.db import get_conn
from app.services.population import POPULATION

router = APIRouter(tags=["meta"])

@router.get("/filters")
def filters() -> Dict[str, Any]:
    """
    Return distinct values required for populating frontend dropdowns:
      - states, scam_types, categories, contact_methods
      - years: min, max, and full list
      - last 5 years (for default views)
      - latest available year
      - top3_year_locked (2025 if present, else latest year in data)
    """
    with get_conn() as conn, conn.cursor() as cur:
        # States
        cur.execute("SELECT DISTINCT state FROM scam_stats WHERE state IS NOT NULL ORDER BY state;")
        states = [r[0] for r in cur.fetchall() if r[0]]

        # Scam types
        cur.execute("SELECT DISTINCT scam_type FROM scam_stats WHERE scam_type IS NOT NULL ORDER BY scam_type;")
        scam_types = [r[0] for r in cur.fetchall() if r[0]]

        # Categories
        cur.execute("SELECT DISTINCT category FROM scam_stats WHERE category IS NOT NULL ORDER BY category;")
        categories = [r[0] for r in cur.fetchall() if r[0]]

        # Contact methods
        cur.execute("SELECT DISTINCT contact_method FROM scam_stats WHERE contact_method IS NOT NULL ORDER BY contact_method;")
        contact_methods = [r[0] for r in cur.fetchall() if r[0]]

        # Year range
        cur.execute("SELECT MIN(year), MAX(year) FROM scam_stats;")
        y_min, y_max = cur.fetchone()
        y_min = int(y_min or 0)
        y_max = int(y_max or 0)
        years_list = list(range(y_min, y_max + 1)) if y_min and y_max else []

        # Last 5 years (default window for backend calculations)
        last5 = [y for y in range(y_max, y_max - 5, -1)] if y_max else []

    # For Top 3 by loss, lock to 2025 if data includes it, else use latest year
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
    Return the population mapping used in likelihood tiles.
    This allows the frontend to display explanatory tooltips
    or perform calculations client-side if needed.
    """
    return {"population": POPULATION}
