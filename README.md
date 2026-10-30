# AI Trainer Performance Analyzer

A Python + SQL project that analyzes **AI trainer performance data** — quality scores, throughput, rejection rates — and produces actionable insights for project leads.

Built for AI training operations, QA managers, and anyone running annotation or evaluation projects at scale.

---

## What It Does

Given a CSV of daily trainer performance data, this tool produces:

| Output | What It Reveals |
|---|---|
| **Quality trend report** | Are quality scores improving, drifting, or stable? |
| **Throughput KPIs** | Tasks/day, average time-per-task, completion rate |
| **Anomaly detection** | Which days had unusual quality or throughput patterns? |
| **Root-cause analysis** | Why did rejection rates spike? What happened on outlier days? |
| **Tableau-ready CSV export** | Clean output for dashboard building |
| **Matplotlib chart** | Quality + throughput trend over time |

---

## Why I Built This

As an AI trainer and former Network Operations Data Analyst, I've worked on both sides of the data:

1. I've done the training work — evaluating LLM outputs, writing annotations, maintaining quality scores.
2. I've analyzed operational KPIs — monitoring network performance, building dashboards, running root-cause analysis on anomalies.

This project combines both. It's the kind of analysis that **project leads actually run** when they need to know: *"Is this trainer's quality improving? Why did rejection rates spike last week? Which days need review?"*

Most AI training projects are evaluated as *"can you follow a rubric?"* This one asks a higher-level question: *"Can you analyze the data that emerges from AI training itself?"*

---

## Data Format

The tool reads a CSV with this structure:

| Column | Description |
|---|---|
| `date` | YYYY-MM-DD |
| `tasks_completed` | Tasks submitted that day |
| `tasks_rejected` | Tasks rejected by QA that day |
| `avg_quality_score` | 1–5 scale, average across tasks |
| `avg_time_per_task_min` | Average minutes per task |
| `rejection_rate` | tasks_rejected / tasks_completed |

---

## How to Run It

Install dependencies:

    pip install -r requirements.txt

Run the analysis:

    python analyzer.py

Optionally pass a custom file:

    python analyzer.py my_data.csv

---

## Output Example

The tool prints a summary to the console and exports two files.

**Console summary shows:**

- Date range and total days
- Total tasks completed and rejected
- Overall rejection rate and average quality score
- Weekly quality trend
- Anomaly detection (z-score > 2)
- Root-cause analysis for anomaly days

**Exports:**

- `report.csv` — Tableau-ready summary table
- `chart.png` — Quality and throughput trend chart

---

## Files in This Repo

| File | Purpose |
|---|---|
| `analyzer.py` | Main analysis script |
| `queries.sql` | SQL queries used against the SQLite database |
| `sample_data.csv` | 60-day sample dataset with intentional anomalies |
| `requirements.txt` | pandas, matplotlib |

---

## Tech Stack

- **Language:** Python 3
- **Data:** pandas + SQLite (via `sqlite3` standard library)
- **Visualization:** matplotlib
- **Export formats:** CSV, PNG

---

## Future Improvements

- Streamlit dashboard for interactive exploration
- Comparison mode (multiple trainers side-by-side)
- Automatic guideline-change detection from text logs
- Integration with Tableau Server for live refresh

---

## About the Author

**Samuel Eno Sunday** — AI Training Specialist & Data Analyst

- LinkedIn: [linkedin.com/in/samuelenosunday001](https://www.linkedin.com/in/samuelenosunday001/)
- GitHub: [github.com/samuelenosunday](https://github.com/samuelenosunday)
- Email: samuelenosunday@gmail.com

*Open to remote contract, part-time, and project-based AI training roles.*
