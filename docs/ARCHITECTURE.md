# Architecture — Data Quality Monitor

## System Overview

The Data Quality Monitor is a read-only data quality assessment tool. It accepts any CSV file, profiles each column for statistical properties, applies a configurable set of quality check rules, and produces a scored, auditable quality report. The input data is never modified.

```
┌──────────────────────────────────────────────────────────────┐
│                    Data Quality Monitor                      │
│                     (Streamlit App)                          │
└─────────────────────┬────────────────────────────────────────┘
                      │  CSV file (upload or sample data)
                      ▼
             ┌─────────────────┐
             │   profiler.py   │
             │  profile_column │
             │  profile_df     │
             │  _infer_type    │
             └────────┬────────┘
                      │  list[dict]  (per-column stats)
                      ▼
             ┌─────────────────┐
             │    checks.py    │◄── column roles (sidebar)
             │  run_all_checks │    email, phone, ID,
             │  (8 check fns)  │    state, numeric
             └────────┬────────┘
                      │  list[CheckResult dict]
                      ▼
             ┌─────────────────┐
             │    scorer.py    │
             │  overall_score  │
             │  column_scores  │
             │  grade (A–F)    │
             └────────┬────────┘
                      │  score (float), grade (str), column_scores_df
                      ▼
        ┌─────────────────────────────┐
        │          Dashboard          │
        │  ┌───────────┐ ┌─────────┐ │
        │  │  Check    │ │ Column  │ │
        │  │  Results  │ │ Scores  │ │
        │  └───────────┘ └─────────┘ │
        │  ┌───────────┐ ┌─────────┐ │
        │  │   Data    │ │  Raw    │ │
        │  │  Profile  │ │  Data   │ │
        │  └───────────┘ └─────────┘ │
        └──────────────┬──────────────┘
                       │
          ┌────────────┴──────────────┐
          │                           │
   [CSV Export]               [Excel Export]
   quality_checks.csv         quality_report.xlsx
                               Sheet 1: Summary
                               Sheet 2: Check Results
```

---

## Module Reference

| Module | Location | Responsibility |
|---|---|---|
| `profiler.py` | `src/profiler.py` | Column-level statistical profiling and data type inference |
| `checks.py` | `src/checks.py` | Eight quality check functions; run_all_checks() orchestrator |
| `scorer.py` | `src/scorer.py` | Weighted composite score, per-column scores, letter grade |
| `main.py` | `app/main.py` | Streamlit dashboard; sidebar config; Plotly charts; export buttons |
| `generate_sample_data.py` | `scripts/` | Government procurement sample CSV generator |

---

## Quality Check Definitions

Type F archetype requirement: every check type's scope, weights, and thresholds must be documented.

| Check Type | Check Name | Weight | WARN Threshold | FAIL Threshold | Scope |
|---|---|---|---|---|---|
| Duplicate detection | Duplicate Rows | 1.5 | >2% of rows | >5% of rows | Dataset level |
| Missing values | Null / Empty | 1.2 | >5% per column | >15% per column | All columns |
| ID integrity | Uniqueness | 1.5 | Any duplicate | >1% duplicated | ID column |
| Email validation | Email Format | 1.0 | >3% invalid | >10% invalid | Email column |
| Phone validation | Phone Format | 0.8 | >5% non-standard | >15% non-standard | Phone column |
| Categorical validity | Allowed Values | 1.2 | >1% invalid | >5% invalid | State/categorical column |
| Statistical outliers | Outlier (>3σ) | 1.0 | >2% outliers | >8% outliers | Numeric columns |
| Range validation | Range Check | 1.3 | >1% out-of-range | >5% out-of-range | Numeric columns |

**Weight rationale:** Duplicate Rows and Uniqueness carry the highest weights (1.5×) because duplicate or non-unique IDs cause double-counting in financial reporting systems. Range Check (1.3×) is next because negative contract values corrupt obligation totals. Phone Format carries the lowest weight (0.8×) because format violations are the least consequential for data pipeline integrity.

---

## Composite Score Formula

**Per-check score calculation:**

```
pct = affected_rows / total_rows × 100

if pct == 0:
    status = PASS,  score = 100.0
elif pct <= warn_threshold:
    status = WARN,  score = 100 − pct × 3
elif pct <= fail_threshold:
    status = WARN,  score = 100 − pct × 4
else:
    status = FAIL,  score = max(0, 100 − pct × 5)
```

**Weighted composite score:**

```
overall_score = Σ(check_score × weight) / Σ(weights)
```

Where `weight` is taken from CHECK_WEIGHTS in `scorer.py`:

```python
CHECK_WEIGHTS = {
    "Duplicate Rows": 1.5,
    "Null / Empty":   1.2,
    "Uniqueness":     1.5,
    "Email Format":   1.0,
    "Phone Format":   0.8,
    "Allowed Values": 1.2,
    "Outlier (>3σ)":  1.0,
    "Range Check":    1.3,
}
```

**Grade scale:**

| Grade | Score Range |
|---|---|
| A | ≥ 95 |
| B | ≥ 85 |
| C | ≥ 70 |
| D | ≥ 55 |
| F | < 55 |

---

## Design Decisions

**1. Read-only check architecture — check functions never modify input data.**

Each check function in `checks.py` accepts a DataFrame, reads it, and returns a list of result dicts. The DataFrame is not modified. `run_all_checks()` passes the same DataFrame to every check function. This design means the profiler and checks can be composed in any order without risk of one step affecting another's results. The Streamlit app reinforces this by loading data with `dtype=str` — no automatic type coercion occurs before checks run.

**2. Configurable column roles instead of fixed column names.**

The tool does not assume column names. The sidebar lets the user designate which column is the email address, which is the phone number, which is the ID, which is the state code, and which columns contain numeric values. `run_all_checks()` accepts these as optional keyword arguments. Checks for unassigned roles are skipped entirely — no empty-column runs. This makes the tool work against any CSV schema without code changes.

**3. Weighted composite score instead of simple pass/fail aggregate.**

A single pass/fail gate obscures severity differences between check types. A dataset with 25% null values in a critical ID column and a dataset with 3% malformed phone numbers represent very different levels of data quality risk. The weighted score model encodes these priorities: duplicate rows and ID uniqueness (1.5×) matter more than phone formatting (0.8×). The letter grade maps the score to a familiar scale that is immediately communicable to non-technical stakeholders.

**4. String-typed load for all columns.**

`pd.read_csv(..., dtype=str)` prevents pandas from auto-inferring types on load. This is intentional: the profiler's type inference (`_infer_type`) is the authoritative type detection layer. If pandas coerced a column to float first, null detection via the blank-string check would not work correctly. Loading as strings ensures the raw values reach the profiler and check functions unchanged.
