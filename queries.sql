-- =============================================================
-- AI Trainer Performance Analyzer — SQL Queries
-- =============================================================
-- These queries run against a SQLite in-memory database created
-- by analyzer.py from sample_data.csv.
--
-- The table is named "trainer_data" and has these columns:
--   date (TEXT), tasks_completed (INT), tasks_rejected (INT),
--   avg_quality_score (REAL), avg_time_per_task_min (REAL),
--   rejection_rate (REAL)
-- =============================================================


-- -------------------------------------------------------------
-- QUERY 1: Overall KPIs
-- -------------------------------------------------------------
-- Purpose: Summarize the entire time period into headline numbers.
-- This is the "executive summary" a project lead would see first.
-- -------------------------------------------------------------
SELECT
    MIN(date)                              AS start_date,
    MAX(date)                              AS end_date,
    COUNT(*)                               AS total_days,
    SUM(tasks_completed)                   AS total_tasks_completed,
    SUM(tasks_rejected)                    AS total_tasks_rejected,
    ROUND(
        CAST(SUM(tasks_rejected) AS REAL) / SUM(tasks_completed),
        4
    )                                      AS overall_rejection_rate,
    ROUND(AVG(avg_quality_score), 2)       AS avg_quality_score,
    ROUND(AVG(avg_time_per_task_min), 2)   AS avg_time_per_task_min,
    ROUND(AVG(tasks_completed), 2)         AS avg_tasks_per_day
FROM trainer_data;


-- -------------------------------------------------------------
-- QUERY 2: Weekly Quality Trend
-- -------------------------------------------------------------
-- Purpose: Bucket days into ISO weeks and compute the average
-- quality score per week. Reveals drift, dips, and recoveries.
-- -------------------------------------------------------------
-- SQLite doesn't have ISO week built in, so we derive it from
-- the date using strftime('%Y-%W', date) — year + week number.
-- -------------------------------------------------------------
SELECT
    strftime('%Y-W%W', date)               AS week,
    ROUND(AVG(avg_quality_score), 2)       AS avg_quality_score,
    COUNT(*)                               AS days_in_week
FROM trainer_data
GROUP BY week
ORDER BY week;


-- -------------------------------------------------------------
-- QUERY 3: Weekly Rejection Rate Trend
-- -------------------------------------------------------------
-- Purpose: Same weekly bucketing, but for rejection rate.
-- Complements the quality trend — they usually move together.
-- -------------------------------------------------------------
SELECT
    strftime('%Y-W%W', date)               AS week,
    ROUND(
        CAST(SUM(tasks_rejected) AS REAL) / SUM(tasks_completed),
        4
    )                                      AS weekly_rejection_rate,
    SUM(tasks_completed)                   AS total_tasks,
    SUM(tasks_rejected)                    AS total_rejected
FROM trainer_data
GROUP BY week
ORDER BY week;


-- -------------------------------------------------------------
-- QUERY 4: Rejection Rate Anomalies (z-score > 2)
-- -------------------------------------------------------------
-- Purpose: Flag days where the rejection rate is more than
-- 2 standard deviations above the mean.
--
-- Approach: subquery computes mean and stddev, then outer query
-- joins back and calculates z-score per day.
-- -------------------------------------------------------------
WITH stats AS (
    SELECT
        AVG(rejection_rate) AS mean_rate,
        -- SQLite has no STDDEV, so we compute it manually via
        -- sqrt(avg(x^2) - avg(x)^2)
        SQRT(
            AVG(rejection_rate * rejection_rate) -
            (AVG(rejection_rate) * AVG(rejection_rate))
        ) AS stddev_rate
    FROM trainer_data
)
SELECT
    t.date,
    t.rejection_rate,
    ROUND((t.rejection_rate - s.mean_rate) / s.stddev_rate, 2) AS z_score
FROM trainer_data t, stats s
WHERE s.stddev_rate > 0
  AND (t.rejection_rate - s.mean_rate) / s.stddev_rate > 2
ORDER BY z_score DESC;


-- -------------------------------------------------------------
-- QUERY 5: Quality Score Anomalies (z-score < -2)
-- -------------------------------------------------------------
-- Purpose: Flag days where quality dropped more than 2 standard
-- deviations BELOW the mean (negative outliers).
-- -------------------------------------------------------------
WITH stats AS (
    SELECT
        AVG(avg_quality_score) AS mean_q,
        SQRT(
            AVG(avg_quality_score * avg_quality_score) -
            (AVG(avg_quality_score) * AVG(avg_quality_score))
        ) AS stddev_q
    FROM trainer_data
)
SELECT
    t.date,
    t.avg_quality_score,
    ROUND((t.avg_quality_score - s.mean_q) / s.stddev_q, 2) AS z_score
FROM trainer_data t, stats s
WHERE s.stddev_q > 0
  AND (t.avg_quality_score - s.mean_q) / s.stddev_q < -2
ORDER BY z_score ASC;


-- -------------------------------------------------------------
-- QUERY 6: Time-Per-Task Anomalies (z-score > 2)
-- -------------------------------------------------------------
-- Purpose: Flag days where time-per-task was unusually high —
-- a signal of unfamiliar tasks, guideline confusion, or
-- increased complexity.
-- -------------------------------------------------------------
WITH stats AS (
    SELECT
        AVG(avg_time_per_task_min) AS mean_t,
        SQRT(
            AVG(avg_time_per_task_min * avg_time_per_task_min) -
            (AVG(avg_time_per_task_min) * AVG(avg_time_per_task_min))
        ) AS stddev_t
    FROM trainer_data
)
SELECT
    t.date,
    t.avg_time_per_task_min,
    ROUND((t.avg_time_per_task_min - s.mean_t) / s.stddev_t, 2) AS z_score
FROM trainer_data t, stats s
WHERE s.stddev_t > 0
  AND (t.avg_time_per_task_min - s.mean_t) / s.stddev_t > 2
ORDER BY z_score DESC;


-- -------------------------------------------------------------
-- QUERY 7: Root-Cause — Pre-Anomaly Window
-- -------------------------------------------------------------
-- Purpose: For each anomaly date, pull the 3 days BEFORE it,
-- so we can see whether the anomaly was preceded by warning
-- signs (declining quality, rising rejection rate, etc.).
-- -------------------------------------------------------------
-- Anomaly dates identified by any of the three queries above.
-- We use parameter placeholders (:anomaly_dates) that
-- analyzer.py fills in programmatically.
-- -------------------------------------------------------------
SELECT
    date,
    tasks_completed,
    tasks_rejected,
    avg_quality_score,
    avg_time_per_task_min,
    rejection_rate
FROM trainer_data
WHERE date BETWEEN date(:anomaly_date, '-3 days')
               AND date(:anomaly_date, '-1 day')
ORDER BY date;
