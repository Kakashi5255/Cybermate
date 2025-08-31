# app/main.py
from app.config import APP_NAME, APP_VERSION
from app.services.db import get_conn
from app.routes.detect import router as detect_router
from app.routes.meta import router as meta_router
from typing import Optional, List, Any, Tuple
from fastapi import FastAPI, Query
from app.services.population import POPULATION
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ScamBot Backend", version="0.1.0")
app.include_router(meta_router)



# -------------------------------------------------
# helpers
# -------------------------------------------------
def _get_year_bounds(conn) -> Tuple[int, List[int]]:
    """Return (max_year, last5_years_desc)."""
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(year), 0) FROM scam_stats;")
        row = cur.fetchone()
        max_year = int(row[0] or 0)
    if max_year == 0:
        return 0, []
    last5 = [y for y in range(max_year, max_year - 5, -1)]
    return max_year, last5

def _make_where(base: List[str], params: List[Any], *,
                years: Optional[List[int]] = None,
                year: Optional[int] = None,
                state: Optional[str] = None,
                category: Optional[str] = None,
                scam_type: Optional[str] = None,
                contact_method: Optional[str] = None,
                age_group: Optional[str] = None,
                gender: Optional[str] = None):
    if year is not None:
        base.append("year = %s"); params.append(year)
    elif years:
        placeholders = ",".join(["%s"] * len(years))
        base.append(f"year IN ({placeholders})"); params.extend(years)

    if state:
        base.append("state = %s"); params.append(state)
    if category:
        base.append("category = %s"); params.append(category)
    if scam_type:
        base.append("scam_type = %s"); params.append(scam_type)
    if contact_method:
        base.append("contact_method = %s"); params.append(contact_method)
    if age_group:
        base.append("age_group = %s"); params.append(age_group)
    if gender:
        base.append("gender = %s"); params.append(gender)

# -------------------------------------------------
# /stats
# -------------------------------------------------
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
    Returns JSON for the dashboard, with Year logic and extra tiles.

    - If `year` is omitted: KPI/series/breakdown use the last 5 years found in DB.
    - If `year` is provided: KPI/series/breakdown for that single year.
    - top3: always 2025 (fallback to max year), respects state only.
    - breaking_news: always last 5 years, respects state only (ignores scam_type).
    """
    with get_conn() as conn:
        max_year, last5 = _get_year_bounds(conn)

        # ------------- KPI + SERIES + BREAKDOWN (Year filter applies) -------------
        where = ["1=1"]; params: List[Any] = []
        _make_where(
            where, params,
            years=None if year is not None else last5,  # default window
            year=year,
            state=state,
            category=category,
            scam_type=scam_type,
            contact_method=contact_method,
            age_group=age_group,
            gender=gender,
        )
        where_sql = " AND ".join(where)

        kpi_sql = f"""
          SELECT COALESCE(SUM(reports),0) AS reports,
                 COALESCE(SUM(losses),0)::float AS losses,
                 COALESCE(SUM(reports_with_loss),0) AS reports_with_loss
          FROM scam_stats
          WHERE {where_sql};
        """
        series_sql = f"""
          SELECT year, month, SUM(reports) AS reports, SUM(losses)::float AS losses
          FROM scam_stats
          WHERE {where_sql}
          GROUP BY year, month
          ORDER BY year, month;
        """
        breakdown_sql = f"""
          SELECT category, SUM(reports) AS reports, SUM(losses)::float AS losses
          FROM scam_stats
          WHERE {where_sql}
          GROUP BY category
          ORDER BY losses DESC NULLS LAST, reports DESC NULLS LAST
          LIMIT 20;
        """

        with conn.cursor() as cur:
            cur.execute(kpi_sql, params)
            r_reports, r_losses, r_reports_with_loss = cur.fetchone()
            total_reports = int(r_reports or 0)
            total_losses  = float(r_losses or 0.0)
            total_reports_with_loss = int(r_reports_with_loss or 0)

            cur.execute(series_sql, params)
            rows = cur.fetchall()
            series = [
                {"period": f"{int(y)}-{int(m):02d}",
                 "reports": int(rep or 0),
                 "losses": float(loss or 0.0)}
                for (y, m, rep, loss) in rows
            ]

            cur.execute(breakdown_sql, params)
            breakdown = [
                {"category": c or "Unknown",
                 "reports": int(rep or 0),
                 "losses": float(loss or 0.0)}
                for (c, rep, loss) in cur.fetchall()
            ]

        # ------------- Likelihood tiles (need population + state) -------------------
        likelihood_scammed_pct = None
        likelihood_loss_per_10 = None
        if state and state in POPULATION and POPULATION[state]:
            pop = float(POPULATION[state])
            likelihood_scammed_pct = round((total_reports / pop) * 100.0, 2) if pop > 0 else None
            likelihood_loss_per_10 = round((total_reports_with_loss / pop) * 10.0, 3) if pop > 0 else None

        # ------------- Top 3 scams by loss (ALWAYS 2025 fallback -> max_year) ------
        top3_year = 2025 if (max_year and 2025 <= max_year) else max_year
        top3_params: List[Any] = []
        top3_where = ["year = %s"]; top3_params.append(top3_year)
        if state:
            top3_where.append("state = %s"); top3_params.append(state)
        # by spec: ignore scam_type/category filters here
        top3_sql = f"""
          SELECT category, scam_type, contact_method,
                 SUM(losses)::float AS losses, SUM(reports) AS reports
          FROM scam_stats
          WHERE {" AND ".join(top3_where)}
          GROUP BY category, scam_type, contact_method
          ORDER BY losses DESC NULLS LAST, reports DESC NULLS LAST
          LIMIT 3;
        """
        with get_conn() as conn2, conn2.cursor() as cur2:
            cur2.execute(top3_sql, top3_params)
            top3 = [
                {
                    "category": c or "Unknown",
                    "scam_type": st or "Unknown",
                    "contact_method": cm or "Unknown",
                    "losses": float(ls or 0.0),
                    "reports": int(rp or 0),
                    "year": top3_year,
                }
                for (c, st, cm, ls, rp) in cur2.fetchall()
            ]

        # ------------- Breaking news (ALWAYS last 5 years, ignores scam_type) ------
        bn_params: List[Any] = []
        bn_where = ["1=1"]
        # last5 may be [], handle gracefully
        if last5:
            placeholders = ",".join(["%s"] * len(last5))
            bn_where.append(f"year IN ({placeholders})"); bn_params.extend(last5)
        if state:
            bn_where.append("state = %s"); bn_params.append(state)
        # ignore scam_type by design

        # We compute percentage change in losses by contact_method over the window:
        # pct_change = (losses_latest - losses_earliest) / NULLIF(losses_earliest,0)
        bn_sql = f"""
          WITH by_year AS (
            SELECT contact_method, year, SUM(losses)::float AS losses
            FROM scam_stats
            WHERE {" AND ".join(bn_where)}
            GROUP BY contact_method, year
          ),
          span AS (
            SELECT
              contact_method,
              MIN(year) AS y0,
              MAX(year) AS y1
            FROM by_year
            GROUP BY contact_method
          ),
          joined AS (
            SELECT
              s.contact_method,
              b0.losses AS losses_start,
              b1.losses AS losses_end
            FROM span s
            LEFT JOIN by_year b0 ON b0.contact_method = s.contact_method AND b0.year = s.y0
            LEFT JOIN by_year b1 ON b1.contact_method = s.contact_method AND b1.year = s.y1
          )
          SELECT contact_method,
                 COALESCE(
                   CASE WHEN losses_start IS NULL OR losses_start = 0 THEN NULL
                        ELSE (losses_end - losses_start) / losses_start * 100.0
                   END, 0.0
                 ) AS pct_change,
                 COALESCE(losses_start,0.0) AS losses_start,
                 COALESCE(losses_end,0.0)   AS losses_end
          FROM joined
          ORDER BY pct_change DESC NULLS LAST
          LIMIT 3;
        """
        with get_conn() as conn3, conn3.cursor() as cur3:
            cur3.execute(bn_sql, bn_params)
            breaking_news = [
                {
                    "contact_method": cm or "Unknown",
                    "pct_change": round(float(pct or 0.0), 2),
                    "losses_start": float(ls0 or 0.0),
                    "losses_end": float(ls1 or 0.0),
                    "window_years": last5,   # returned so UI can label the period
                }
                for (cm, pct, ls0, ls1) in cur3.fetchall()
            ]

    return {
        "kpis": {
            "total_losses": round(total_losses, 2),
            "reports": total_reports,
            "avg_loss": round((total_losses / total_reports), 2) if total_reports else 0.0
        },
        "series": series,
        "breakdown": breakdown,

        # New tiles for the frontend
        "likelihood": {
            "state_population_used": POPULATION.get(state) if state else None,
            "likelihood_scammed_pct": likelihood_scammed_pct,   # null if no/unknown state
            "likelihood_loss_per_10": likelihood_loss_per_10     # null if no/unknown state
        },

        # Always-year-locked sections
        "top3_by_loss": top3,              # locked to 2025 (or max year)
        "breaking_news": breaking_news     # locked to last 5 years
    }


# ---------- scambot /detect ----------
app.include_router(detect_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "ScamBot Backend", "version": "0.1.0"}