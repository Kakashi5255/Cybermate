SCHEMA_SQL = """
-- Enable UUIDs if not already done
create extension if not exists pgcrypto;

-- 1) RAW TABLE mirroring your CSV columns (snake_case)
create table if not exists SCAM_DATA_RAW (
  id uuid primary key default gen_random_uuid(),

  -- your columns:
  date                  date,          -- from "Date"
  state                 text,          -- from "State"
  contact_method        text,          -- from "Contact Method"
  age_group             text,          -- from "Age Group"
  gender                text,          -- from "Gender"
  scam_category         text,          -- from "Scam Category"
  scam_type             text,          -- from "Scam Type"
  aggregated_amount_lost numeric,      -- from "Aggregated Amount Lost"
  number_of_reports     int,           -- from "Number of Reports"
  year                  int            -- from "Year" (keep as provided)
);

-- Helpful raw indexes (optional but good for big files)
create index if not exists idx_raw_year on SCAM_DATA_RAW(year);
create index if not exists idx_raw_date on SCAM_DATA_RAW(date);
create index if not exists idx_raw_state on SCAM_DATA_RAW(state);
create index if not exists idx_raw_category on SCAM_DATA_RAW(scam_category);

-- 2) MATERIALIZED VIEW for fast dashboard queries
--    We keep your extra dimensions (scam_type, contact_method, age_group, gender)
--    so you can filter by them later if needed.
create materialized view if not exists SCAM_STATS as
select
  coalesce(year, extract(year from date)::int) as year,
  extract(month from date)::int                as month,
  state,
  scam_category       as category,
  scam_type,
  contact_method,
  age_group,
  gender,
  sum(number_of_reports)           as reports,
  sum(aggregated_amount_lost)::numeric as losses,
  case
    when sum(number_of_reports) > 0
      then sum(aggregated_amount_lost) / sum(number_of_reports)
    else 0
  end as avg_loss
from SCAM_DATA_RAW
group by
  coalesce(year, extract(year from date)::int),
  extract(month from date)::int,
  state, scam_category, scam_type, contact_method, age_group, gender;

-- Indexes to speed up filters on the materialized view
create index if not exists idx_stats_year_month on SCAM_STATS(year, month);
create index if not exists idx_stats_state on SCAM_STATS(state);
create index if not exists idx_stats_category on SCAM_STATS(category);

-- If you need to refresh after loading new CSV rows:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY SCAM_STATS;
"""
