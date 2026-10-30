"""
AI Trainer Performance Analyzer
================================
Analyzes daily trainer performance data (quality, throughput,
rejection rates) and produces:
- Console report with KPIs, trends, anomalies, root-cause analysis
- report.csv (Tableau-ready summary)
- chart.png (quality + throughput trend chart)

Author: Samuel Eno Sunday
License: MIT
"""

import csv
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend for headless environments
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# -------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------

def load_csv_into_sqlite(csv_path):
    """Load a CSV file into an in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE trainer_data (
            date TEXT PRIMARY KEY,
            tasks_completed INTEGER,
            tasks_rejected INTEGER,
            avg_quality_score REAL,
            avg_time_per_task_min REAL,
            rejection_rate REAL
        )
    """)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["date"],
                int(r["tasks_completed"]),
                int(r["tasks_rejected"]),
                float(r["avg_quality_score"]),
                float(r["avg_time_per_task_min"]),
                float(r["rejection_rate"]),
            )
            for r in reader
        ]

    cur.executemany(
        "INSERT INTO trainer_data VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn


def load_queries(sql_path):
    """
    Load named queries from queries.sql.
    Queries are delimited by the marker '-- QUERY <N>:' at the start of a line.
    Returns a dict: { 'N': 'SELECT ...' }
    """
    queries = {}
    current_id = None
    current_lines = []

    with open(sql_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("-- QUERY") and ":" in stripped:
                # Save previous query
                if current_id is not None and current_lines:
                    queries[current_id] = "\n".join(current_lines).strip()
                # Start new query
                current_id = stripped.split("QUERY")[1].split(":")[0].strip()
                current_lines = []
            elif current_id is not None:
                current_lines.append(line.rstrip())

    if current_id is not None and current_lines:
        queries[current_id] = "\n".join(current_lines).strip()

    return queries


# -------------------------------------------------------------
# REPORTING — CONSOLE
# -------------------------------------------------------------

def print_header(title):
    print("=" * 50)
    print(title)
    print("=" * 50)


def report_overall(conn, queries):
    """Print overall KPI summary."""
    print_header("AI TRAINER PERFORMANCE REPORT")

    row = conn.execute(queries["1"]).fetchone()
    (start, end, days, completed, rejected,
     rej_rate, quality, time_per, tasks_per) = row

    print(f"Date range: {start} to {end} ({days} days)")
    print(f"Total tasks completed: {completed}")
    print(f"Total tasks rejected: {rejected}")
    print(f"Overall rejection rate: {rej_rate:.2%}")
    print(f"Average quality score: {quality:.2f} / 5")
    print(f"Average time per task: {time_per:.2f} min")
    print(f"Average tasks per day: {tasks_per:.2f}")
    print()


def report_weekly_quality(conn, queries):
    """Print weekly quality trend."""
    print("--- QUALITY TREND (weekly avg) ---")
    rows = conn.execute(queries["2"]).fetchall()
    if not rows:
        print("No weekly data.")
        print()
        return

    values = []
    for week, avg_q, _days in rows:
        print(f"{week}: {avg_q:.2f}")
        values.append(avg_q)

    # Compute a simple trend signal
    if len(values) >= 4:
        first_half = sum(values[: len(values) // 2]) / (len(values) // 2)
        second_half = sum(values[len(values) // 2:]) / (
            len(values) - len(values) // 2
        )
        diff = second_half - first_half
        if diff > 0.1:
            trend = "IMPROVING"
        elif diff < -0.1:
            trend = "DECLINING"
        else:
            trend = "STABLE"
        print(f"Trend: {trend}")
    print()


def report_weekly_rejection(conn, queries):
    """Print weekly rejection rate trend."""
    print("--- REJECTION RATE TREND (weekly) ---")
    rows = conn.execute(queries["3"]).fetchall()
    for week, rate, _tasks, _rejected in rows:
        print(f"{week}: {rate:.2%}")
    print()


def report_anomalies(conn, queries):
    """Detect and print anomalies across three metrics."""
    print("--- ANOMALY DETECTION (z-score > |2|) ---")

    anomalies = []

    # Rejection rate anomalies (query 4)
    for date, value, z in conn.execute(queries["4"]).fetchall():
        print(f"{date}: rejection_rate={value:.2f} (z={z}) — REJECTION SPIKE")
        anomalies.append({"date": date, "type": "rejection_spike"})

    # Quality drop anomalies (query 5)
    for date, value, z in conn.execute(queries["5"]).fetchall():
        print(f"{date}: avg_quality_score={value:.2f} (z={z}) — QUALITY DROP")
        anomalies.append({"date": date, "type": "quality_drop"})

    # Time-per-task anomalies (query 6)
    for date, value, z in conn.execute(queries["6"]).fetchall():
        print(f"{date}: avg_time_per_task={value:.2f} (z={z}) — TIME SPIKE")
        anomalies.append({"date": date, "type": "time_spike"})

    if not anomalies:
        print("No anomalies detected.")
    print()

    return anomalies


def report_root_cause(conn, queries, anomalies):
    """For each anomaly, print the 3 days before it."""
    print("--- ROOT-CAUSE ANALYSIS (3-day window before each anomaly) ---")

    if not anomalies:
        print("No anomalies to analyze.")
        print()
        return

    for a in anomalies:
        date = a["date"]
        anomaly_type = a["type"]

        print(f"\n{date} ({anomaly_type}):")
        print("  Prior 3 days:")

        try:
            rows = conn.execute(
                queries["7"], {"anomaly_date": date}
            ).fetchall()
        except sqlite3.Error as e:
            print(f"  Query error: {e}")
            continue

        if not rows:
            print("    (no prior data in window)")
            continue

        for (d, completed, rejected, quality, time_per, rej_rate) in rows:
            print(
                f"    {d}: quality={quality:.2f}, "
                f"rejection_rate={rej_rate:.2%}, "
                f"time_per_task={time_per:.2f} min"
            )

    print()


# -------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------

def export_tableau_csv(conn, output_path):
    """
    Export a Tableau-ready summary CSV: one row per day with
    all metrics, so a Tableau dashboard can be built from it.
    """
    rows = conn.execute("""
        SELECT
            date,
            tasks_completed,
            tasks_rejected,
            avg_quality_score,
            avg_time_per_task_min,
            rejection_rate
        FROM trainer_data
        ORDER BY date
    """).fetchall()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "tasks_completed", "tasks_rejected",
            "avg_quality_score", "avg_time_per_task_min", "rejection_rate",
        ])
        writer.writerows(rows)

    print(f"Exported Tableau-ready data to: {output_path}")


def export_chart(conn, output_path):
    """Generate a quality + throughput trend chart."""
    if not HAS_MATPLOTLIB:
        print("Skipping chart: matplotlib not installed.")
        return

    rows = conn.execute("""
        SELECT date, avg_quality_score, tasks_completed, rejection_rate
        FROM trainer_data
        ORDER BY date
    """).fetchall()

    dates = [r[0] for r in rows]
    quality = [r[1] for r in rows]
    throughput = [r[2] for r in rows]
    rejection = [r[3] * 100 for r in rows]  # to percent

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    # Quality trend
    axes[0].plot(dates, quality, color="#1f77b4", linewidth=2)
    axes[0].set_ylabel("Quality (1-5)")
    axes[0].set_title("AI Trainer Performance — Quality, Throughput, Rejection")
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(
        sum(quality) / len(quality), color="gray",
        linestyle="--", alpha=0.6, label="Mean"
    )
    axes[0].legend()

    # Throughput
    axes[1].plot(dates, throughput, color="#2ca02c", linewidth=2)
    axes[1].set_ylabel("Tasks/day")
    axes[1].grid(True, alpha=0.3)

    # Rejection rate
    axes[2].plot(dates, rejection, color="#d62728", linewidth=2)
    axes[2].set_ylabel("Rejection rate (%)")
    axes[2].set_xlabel("Date")
    axes[2].grid(True, alpha=0.3)

    # Only label every 7th date to avoid overlap
    step = max(1, len(dates) // 10)
    axes[2].set_xticks(range(0, len(dates), step))
    axes[2].set_xticklabels(
        [dates[i] for i in range(0, len(dates), step)],
        rotation=45, ha="right"
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    print(f"Exported chart to: {output_path}")


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------

def main():
    data_path = "sample_data.csv"
    queries_path = "queries.sql"

    if len(sys.argv) > 1:
        data_path = sys.argv[1]

    if not Path(data_path).exists():
        print(f"Error: Data file not found -> {data_path}")
        sys.exit(1)

    if not Path(queries_path).exists():
        print(f"Error: Queries file not found -> {queries_path}")
        sys.exit(1)

    print(f"Loading data from: {data_path}")
    print(f"Loading queries from: {queries_path}\n")

    conn = load_csv_into_sqlite(data_path)
    queries = load_queries(queries_path)

    # Console report
    report_overall(conn, queries)
    report_weekly_quality(conn, queries)
    report_weekly_rejection(conn, queries)
    anomalies = report_anomalies(conn, queries)
    report_root_cause(conn, queries, anomalies)

    print("=" * 50)

    # Exports
    export_tableau_csv(conn, "report.csv")
    export_chart(conn, "chart.png")

    conn.close()


if __name__ == "__main__":
    main()
