# app/main.py
from typing import Optional, List, Any
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_NAME, APP_VERSION
from app.services.db import get_conn
from app.routes.detect import router as detect_router

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# (optional) CORS for your frontend; edit origins for Vercel URL later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": APP_NAME, "version": APP_VERSION}

@app.get("/version")
def version():
    return {"version": APP_VERSION}

# ---------- Epic 1: /stats ----------
@app.get("/stats")
def stats(
    year: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    scam_type: Optional[str] = Query(None),
    contact_method: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
):
    """
    Returns KPIs, monthly series, and category breakdown from materialized view scam_stats.
    """
    where = ["1=1"]
    params: List[Any] = []

    if year is not None:        where.append("year = %s");            params.append(year)
    if state:                   where.append("state = %s");           params.append(state)
    if category:                where.append("category = %s");        params.append(category)
    if scam_type:               where.append("scam_type = %s");       params.append(scam_type)
    if contact_method:          where.append("contact_method = %s");  params.append(contact_method)
    if age_group:               where.append("age_group = %s");       params.append(age_group)
    if gender:                  where.append("gender = %s");          params.append(gender)

    where_sql = " AND ".join(where)

    series_sql = f"""
        SELECT year, month, SUM(reports) AS reports, SUM(losses)::float AS losses
        FROM scam_stats
        WHERE {where_sql}
        GROUP BY year, month
        ORDER BY year, month;
    """

    kpi_sql = f"""
        SELECT
          COALESCE(SUM(reports),0) AS reports,
          COALESCE(SUM(losses),0)::float AS losses
        FROM scam_stats
        WHERE {where_sql};
    """

    breakdown_sql = f"""
        SELECT category, SUM(reports) AS reports, SUM(losses)::float AS losses
        FROM scam_stats
        WHERE {where_sql}
        GROUP BY category
        ORDER BY losses DESC NULLS LAST, reports DESC NULLS LAST
        LIMIT 20;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            # KPIs
            cur.execute(kpi_sql, params)
            r_reports, r_losses = cur.fetchone()
            total_reports = int(r_reports or 0)
            total_losses  = float(r_losses or 0.0)
            avg_loss = float(round((total_losses / total_reports), 2)) if total_reports else 0.0

            # Series
            cur.execute(series_sql, params)
            rows = cur.fetchall()
            series = [
                {"period": f"{int(y)}-{int(m):02d}", "reports": int(rep or 0), "losses": float(loss or 0.0)}
                for (y, m, rep, loss) in rows
            ]

            # Breakdown by category
            cur.execute(breakdown_sql, params)
            bre = [
                {"category": c or "Unknown", "reports": int(rep or 0), "losses": float(loss or 0.0)}
                for (c, rep, loss) in cur.fetchall()
            ]

    return {
        "kpis": {"total_losses": round(total_losses, 2), "reports": total_reports, "avg_loss": avg_loss},
        "series": series,
        "breakdown": bre
    }

# ---------- Epic 2: /detect ----------
app.include_router(detect_router)
