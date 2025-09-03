# app/services/sql_schema.py
# SQL schema definition for ScamBot data.
# Includes raw table for CSV ingestion, materialized view for reporting,
# and indexes to support efficient dashboard queries.

SCHEMA_SQL = """
-- Enable UUID support if not already available
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================================================
-- 1) Raw table (directly stores CSV-derived fields)
-- =========================================================
CREATE TABLE IF NOT EXISTS SCAM_DATA_RAW (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  date                    DATE,      -- original "Date"
  state                   TEXT,      -- original "State"
  contact_method          TEXT,      -- original "Contact Method"
  age_group               TEXT,      -- original "Age Group"
  gender                  TEXT,      -- original "Gender"
  scam_category           TEXT,      -- original "Scam Category"
  scam_type               TEXT,      -- original "Scam Type"
  aggregated_amount_lost  NUMERIC,   -- original "Aggregated Amount Lost"
  number_of_reports       INT,       -- original "Number of Reports"
  year                    INT        -- original "Year"
);

-- Indexes on raw table
CREATE INDEX IF NOT EXISTS idx_raw_year      ON SCAM_DATA_RAW(year);
CREATE INDEX IF NOT EXISTS idx_raw_date      ON SCAM_DATA_RAW(date);
CREATE INDEX IF NOT EXISTS idx_raw_state     ON SCAM_DATA_RAW(state);
CREATE INDEX IF NOT EXISTS idx_raw_category  ON SCAM_DATA_RAW(scam_category);
CREATE INDEX IF NOT EXISTS idx_raw_type      ON SCAM_DATA_RAW(scam_type);
CREATE INDEX IF NOT EXISTS idx_raw_contact   ON SCAM_DATA_RAW(contact_method);
CREATE INDEX IF NOT EXISTS idx_raw_age       ON SCAM_DATA_RAW(age_group);
CREATE INDEX IF NOT EXISTS idx_raw_gender    ON SCAM_DATA_RAW(gender);

-- =========================================================
-- 2) Materialized view for dashboard queries
--    Aggregated by year, month, state, category, type, contact method, age, gender
-- =========================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS SCAM_STATS AS
SELECT
  COALESCE(year, EXTRACT(YEAR FROM date)::INT) AS year,
  EXTRACT(MONTH FROM date)::INT                AS month,
  state,
  scam_category                                AS category,
  scam_type,
  contact_method,
  age_group,
  gender,
  SUM(number_of_reports)                       AS reports,
  SUM(aggregated_amount_lost)::NUMERIC         AS losses,
  CASE WHEN SUM(number_of_reports) > 0
       THEN SUM(aggregated_amount_lost) / SUM(number_of_reports)
       ELSE 0
  END                                          AS avg_loss
FROM SCAM_DATA_RAW
GROUP BY
  COALESCE(year, EXTRACT(YEAR FROM date)::INT),
  EXTRACT(MONTH FROM date)::INT,
  state, scam_category, scam_type, contact_method, age_group, gender;

-- =========================================================
-- 3) Indexes on materialized view
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_stats_year_month ON SCAM_STATS(year, month);
CREATE INDEX IF NOT EXISTS idx_stats_state      ON SCAM_STATS(state);
CREATE INDEX IF NOT EXISTS idx_stats_category   ON SCAM_STATS(category);
CREATE INDEX IF NOT EXISTS idx_stats_type       ON SCAM_STATS(scam_type);
CREATE INDEX IF NOT EXISTS idx_stats_contact    ON SCAM_STATS(contact_method);
CREATE INDEX IF NOT EXISTS idx_stats_age        ON SCAM_STATS(age_group);
CREATE INDEX IF NOT EXISTS idx_stats_gender     ON SCAM_STATS(gender);

-- =========================================================
-- 4) Unique index on materialized view grain
--    Required for concurrent refresh
-- =========================================================
CREATE UNIQUE INDEX IF NOT EXISTS uq_stats_grain
  ON SCAM_STATS(year, month, state, category, scam_type, contact_method, age_group, gender);

-- =========================================================
-- 5) Initial refresh (blocking)
--    Safe to run after first load
-- =========================================================
REFRESH MATERIALIZED VIEW SCAM_STATS;

-- =========================================================
-- 6) Recommended refresh after subsequent loads:
--    REFRESH MATERIALIZED VIEW CONCURRENTLY SCAM_STATS;
--    (enabled by the unique index on the view grain)
-- =========================================================
"""
