# Data Dictionary — Data Quality Monitor

## Sample Input Schema

**File:** `data/sample/sample_procurement.csv`
**Rows:** 128 (120 generated + 8 injected duplicates, shuffled)
**Domain:** Government procurement reporting (FPDS-NG submission readiness)

| Column | Type | Description | Quality Issues Injected |
|---|---|---|---|
| `contract_id` | string | Unique contract identifier (CON-YYYYMM-NNNN format) | ~3% blank; checked for uniqueness |
| `vendor_name` | string | Prime contractor legal name | ~4% blank |
| `agency_name` | string | Awarding federal agency name | ~5% blank |
| `naics_code` | string | 6-digit NAICS industry code | ~6% malformed (5-digit, 7-digit, non-numeric prefix, or blank) |
| `contract_value` | numeric | Total contract ceiling value in USD | ~20% outliers (10M–50M) and ~20% negatives in outlier selection; ~4% blank |
| `award_date` | string | Contract award date | Mixed formats: `YYYY-MM-DD` and `MM/DD/YYYY` |
| `period_end_date` | string | Contract period of performance end date | Mixed formats: `YYYY-MM-DD` and `MM/DD/YYYY` |
| `set_aside_type` | string | Small business set-aside designation | ~4% "Unknown" (invalid value) |
| `vendor_email` | string | Vendor point-of-contact email address | ~12% malformed (missing @, missing local part, double dot, or blank) |
| `vendor_phone` | string | Vendor point-of-contact phone number | ~18% non-standard (10-digit run-on, missing area code, or blank) |
| `state_code` | string | US state/territory code where work is performed | ~4% invalid ("ZZ") |
| `obligation_amount` | numeric | Total obligation amount in USD (≤ contract value) | ~20% outliers and ~20% negatives in outlier selection; ~4% blank |

**Data note:** This dataset is synthetically generated with `random.seed(99)` for reproducibility. It is designed to surface realistic data quality issues encountered in federal procurement data submissions. It does not represent any real contracts or vendors.

---

## CheckResult Schema

Each quality check function returns a list of dicts with the following schema.

| Field | Type | Description |
|---|---|---|
| `check` | str | Check type name (e.g., "Null / Empty", "Email Format") |
| `column` | str | Column the check was applied to; "(dataset)" for duplicate check |
| `status` | str | `"PASS"`, `"WARN"`, or `"FAIL"` |
| `score` | float | 0–100; 100 = no issues found |
| `detail` | str | Human-readable summary (e.g., "3 null/empty value(s) (2.3% of 128)") |
| `affected_rows` | int | Number of rows that triggered the check |
| `total_rows` | int | Total rows evaluated (denominator for percentage) |

---

## Column Profile Output Schema

`profile_column(series)` returns a dict; `profile_dataframe(df)` returns a list of these dicts.

| Field | Type | Present When | Description |
|---|---|---|---|
| `column` | str | Always | Column name from `series.name` |
| `total_rows` | int | Always | Total rows in the column |
| `null_count` | int | Always | Count of blank/null/None values |
| `null_pct` | float | Always | `null_count / total_rows × 100`, rounded to 2 decimal places |
| `unique_count` | int | Always | `series.nunique(dropna=False)` |
| `uniqueness_pct` | float | Always | `unique_count / total_rows × 100`, rounded to 2 decimal places |
| `is_numeric` | bool | Always | True if ≥80% of non-blank values parse as numeric |
| `inferred_type` | str | Always | One of: `"empty"`, `"numeric"`, `"date"`, `"categorical"`, `"email"`, `"phone"`, `"text"` |
| `min` | float | is_numeric=True | Minimum numeric value |
| `max` | float | is_numeric=True | Maximum numeric value |
| `mean` | float | is_numeric=True | Mean of numeric values |
| `std` | float | is_numeric=True | Standard deviation of numeric values |
| `min/max/mean/std` | None | is_numeric=False | Explicitly set to None for non-numeric columns |

**Type inference order** (first match wins):
1. `"empty"` — if all non-blank values are absent
2. `"numeric"` — if ≥80% of non-blank values parse as numeric
3. `"date"` — if ≥70% of non-blank values match `\d{4}-\d{2}-\d{2}` or `\d{1,2}/\d{1,2}/\d{2,4}`
4. `"email"` — if ≥50% of non-blank values match `^[^@\s]+@[^@\s]+\.[^@\s]+$`
5. `"phone"` — if ≥50% of non-blank values match `^\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$`
6. `"categorical"` — if `unique_count / non_blank_count ≤ 0.15`
7. `"text"` — all other cases

---

## Thresholds Reference

| Constant | Value | Used By |
|---|---|---|
| `NULL_WARN` | 5.0% | `check_nulls` — WARN boundary |
| `NULL_FAIL` | 15.0% | `check_nulls` — FAIL boundary |
| `DUP_WARN` | 2.0% | `check_duplicates` — WARN boundary |
| `DUP_FAIL` | 5.0% | `check_duplicates` — FAIL boundary |
| `OUTLIER_Z` | 3.0 | `check_outliers` — Z-score threshold |

Check-specific thresholds (warn_pct, fail_pct) are passed directly to `_result()`:

| Check | warn_pct | fail_pct |
|---|---|---|
| Email Format | 3% | 10% |
| Phone Format | 5% | 15% |
| Allowed Values | 1% | 5% |
| Range Check | 1% | 5% |
| Outlier (>3σ) | 2% | 8% |
| Uniqueness | 0% | 1% |

---

## Export Schema

### CSV Export (`quality_checks.csv`)

Produced by `results_to_df(results).to_csv(index=False)`. Columns: `check`, `column`, `status`, `score`, `detail`, `affected_rows`, `total_rows`. Sorted: FAIL first, then WARN, then PASS; within each group, ascending by score.

### Excel Export (`quality_report.xlsx`)

Two sheets produced by `pd.ExcelWriter` with openpyxl engine:

**Sheet 1 — Summary:**

| Column | Description |
|---|---|
| Metric | "Overall Score", "Grade", "PASS", "WARN", "FAIL", "Total Checks" |
| Value | Corresponding value for each metric |

**Sheet 2 — Check Results:**

Same columns as the CSV export. Designed for audit review: FAR/DFARS audit teams can open the Excel file and filter or sort the Check Results sheet by status or score.
