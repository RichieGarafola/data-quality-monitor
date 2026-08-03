# Engineering Decisions — Data Quality Monitor

---

## ED-1: Read-only architecture — check functions never modify input data

**Decision:** Every check function in `checks.py` accepts a DataFrame, inspects it, and returns a list of result dictionaries. The DataFrame is never modified. `run_all_checks()` passes the same unmodified DataFrame to every check function.

**Alternative considered:** Coerce data types before checking (e.g., convert all numeric columns to float before running outlier checks) and mutate the DataFrame in place across checks.

**Why this was rejected:** Mutation before checking changes what is being checked. A cell that is `"N/A"` as a string is a format violation; coercing it to NaN before the null check fires changes the failure mode from "format issue" to "missing value" — two different problems with different remediation paths. The read-only design ensures every check reports on the raw source data, not a partially-processed version of it. This is especially important for the string-typed load choice (see ED-4): the same raw string that came from the CSV is what all checks see.

---

## ED-2: Configurable column roles instead of fixed column names

**Decision:** The sidebar lets the user designate which column is the email address, ID, phone number, state code, and numeric values. These designations are passed to `run_all_checks()` as keyword arguments. Checks for unassigned roles are skipped entirely.

**Alternative considered:** Guess column roles by name pattern (e.g., any column named "email" or "Email" automatically triggers the email format check).

**Why configurable roles were chosen:** Name-based guessing fails on real datasets where column names are inconsistent (`"Agency_Email"`, `"contact_email_address"`, `"email_addr"`). A configurable role assignment takes 10 seconds in the sidebar and works correctly regardless of naming convention. Skipping unassigned checks also avoids false positives: if no ID column is designated, the uniqueness check does not fire on an arbitrary column and report spurious duplicate issues.

---

## ED-3: Weighted composite score over simple pass/fail aggregate

**Decision:** Each check carries a configurable weight (Duplicate Rows: 1.5, Uniqueness: 1.5, Range Check: 1.3, Null/Empty: 1.2, Allowed Values: 1.2, Email: 1.0, Outlier: 1.0, Phone: 0.8). The composite score is `Σ(check_score × weight) / Σ(weights)`.

**Alternative considered:** Count passing checks / total checks, or classify the dataset as PASS/FAIL based on any single FAIL result.

**Why weighted scoring was chosen:** A pass/fail aggregate obscures severity. A dataset with 25% null IDs and a dataset with 3% malformed phone numbers both "fail" equally in a binary model, but they represent different levels of pipeline risk. Weights encode domain priorities (duplicate and uniqueness failures cause double-counting in financial reporting; phone formatting does not). The letter grade (A–F) translates the numeric score into a communicable summary for non-technical stakeholders who need a yes/no signal without the numeric detail.

---

## ED-4: `dtype=str` load for all columns

**Decision:** `pd.read_csv(..., dtype=str)` is used for both the sample data load and the uploaded file load. No automatic type coercion occurs before the profiler or checks run.

**Alternative considered:** Let pandas infer column types with `dtype=None` (the default).

**Why str-typed load was chosen:** Pandas auto-inference changes values before checks see them. A blank string `""` becomes `NaN` on load (because `keep_default_na=True`); an `"N/A"` string becomes `NaN` on load. The null / empty check is designed to detect blank strings and N/A as intentional data quality issues — not to catch values that pandas silently converted. Loading as `str` ensures the profiler and checks operate on what the COR or analyst actually stored in the file, not what pandas decided it should mean.

---

## ED-5: Check weight rationale encoded in architecture documentation

**Decision:** The numeric weights assigned to each check type are documented in `docs/ARCHITECTURE.md` with an explicit rationale for each weight differential.

**Alternative considered:** Define weights as magic numbers in `scorer.py` without documentation.

**Why the rationale was documented:** Weights are judgment calls about business risk priority, not mathematical constants. Without documentation, a future reviewer would see `"Duplicate Rows": 1.5` and have no context for why duplicates are weighted higher than email format errors. Documenting the rationale — duplicate data causes double-counting in financial reports; phone formatting is cosmetic — makes the weight choices auditable and defensible, which is appropriate for a tool used in data governance contexts.

---

## ED-6: Grade scale tied to a standard A–F academic grading model

**Decision:** The letter grade is assigned by: A ≥ 95, B ≥ 85, C ≥ 70, D ≥ 55, F < 55.

**Alternative considered:** Custom naming conventions like "Acceptable/Marginal/Unacceptable" or color-only feedback.

**Why the standard grade scale was chosen:** Non-technical stakeholders understand A–F immediately. A data steward reporting to leadership does not need to explain what "Quality Tier 2" means; they say "the procurement dataset is a B." The thresholds were set conservatively: an A requires ≥ 95 because a dataset with even 5% quality issues (about 50 rows in a 1,000-row file) should not receive a perfect grade in a data pipeline context. The F threshold at 55 mirrors the academic convention where below 55% represents failure at a fundamental level.

---

*This document is a repository artifact and may be committed to the published repository.*
