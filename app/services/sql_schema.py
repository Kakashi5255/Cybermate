# app/services/sql_schema.py

SCHEMA_SQL = """
-- Enable UUIDs if not already done
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 1) RAW TABLE (mirrors your CSV columns; unquoted -> lowercased identifiers)
-- =========================================================
CREATE TABLE IF NOT EXISTS SCAM_DATA_RAW (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- CSV-derived columns
  date                    DATE,         -- from "Date"
  state                   TEXT,         -- from "State"
  contact_method          TEXT,         -- from "Contact Method"
  age_group               TEXT,         -- from "Age Group"
  gender                  TEXT,         -- from "Gender"
  scam_category           TEXT,         -- from "Scam Category"
  scam_type               TEXT,         -- from "Scam Type"
  aggregated_amount_lost  NUMERIC,      -- from "Aggregated Amount Lost"
  number_of_reports       INT,          -- from "Number of Reports"
  year                    INT           -- from "Year" (as provided)
);

-- Helpful indexes on RAW (idempotent)
CREATE INDEX IF NOT EXISTS idx_raw_year      ON SCAM_DATA_RAW(year);
CREATE INDEX IF NOT EXISTS idx_raw_date      ON SCAM_DATA_RAW(date);
CREATE INDEX IF NOT EXISTS idx_raw_state     ON SCAM_DATA_RAW(state);
CREATE INDEX IF NOT EXISTS idx_raw_category  ON SCAM_DATA_RAW(scam_category);
CREATE INDEX IF NOT EXISTS idx_raw_type      ON SCAM_DATA_RAW(scam_type);
CREATE INDEX IF NOT EXISTS idx_raw_contact   ON SCAM_DATA_RAW(contact_method);
CREATE INDEX IF NOT EXISTS idx_raw_age       ON SCAM_DATA_RAW(age_group);
CREATE INDEX IF NOT EXISTS idx_raw_gender    ON SCAM_DATA_RAW(gender);

-- =========================================================
-- 2) MATERIALIZED VIEW for fast dashboard queries
--    Grain: year, month, state, category, scam_type, contact_method, age_group, gender
-- =========================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS SCAM_STATS AS
SELECT
  COALESCE(year, EXTRACT(YEAR FROM date)::INT)       AS year,
  EXTRACT(MONTH FROM date)::INT                      AS month,
  state,
  scam_category                                      AS category,
  scam_type,
  contact_method,
  age_group,
  gender,
  SUM(number_of_reports)                             AS reports,
  SUM(aggregated_amount_lost)::NUMERIC               AS losses,
  CASE WHEN SUM(number_of_reports) > 0
       THEN SUM(aggregated_amount_lost) / SUM(number_of_reports)
       ELSE 0
  END                                                AS avg_loss
FROM SCAM_DATA_RAW
GROUP BY
  COALESCE(year, EXTRACT(YEAR FROM date)::INT),
  EXTRACT(MONTH FROM date)::INT,
  state, scam_category, scam_type, contact_method, age_group, gender;

-- =========================================================
-- 3) Indexes on the MATERIALIZED VIEW (speed up filters)
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_stats_year_month   ON SCAM_STATS(year, month);
CREATE INDEX IF NOT EXISTS idx_stats_state        ON SCAM_STATS(state);
CREATE INDEX IF NOT EXISTS idx_stats_category     ON SCAM_STATS(category);
CREATE INDEX IF NOT EXISTS idx_stats_type         ON SCAM_STATS(scam_type);
CREATE INDEX IF NOT EXISTS idx_stats_contact      ON SCAM_STATS(contact_method);
CREATE INDEX IF NOT EXISTS idx_stats_age          ON SCAM_STATS(age_group);
CREATE INDEX IF NOT EXISTS idx_stats_gender       ON SCAM_STATS(gender);

-- =========================================================
-- 4) Unique index on MV grain (required for CONCURRENT refresh)
-- =========================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_stats_grain
  ON SCAM_STATS(year, month, state, category, scam_type, contact_method, age_group, gender);

-- =========================================================
-- 5) Initial refresh (blocking) — safe to run after first load
--    For subsequent loads, prefer the CONCURRENTLY form below.
-- =========================================================
REFRESH MATERIALIZED VIEW SCAM_STATS;

-- =========================================================
-- 6) Recommended (after each CSV load/merge):
--    REFRESH MATERIALIZED VIEW CONCURRENTLY SCAM_STATS;
--    (works because we created a UNIQUE index on the MV grain)
-- =========================================================
"""
