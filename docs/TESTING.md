# Testing — Data Quality Monitor

## Overview

**79 tests / 79 passing** (`pytest tests/ -v`, Python 3.11)

Tests are organized by module. All test files are in `tests/`. The test suite covers the three `src/` modules that contain business logic. `app/main.py` is a Streamlit presentation layer and is not unit-tested.

---

## Test Structure

| File | Classes | Tests | Module Under Test |
|---|---|---|---|
| `tests/test_checks.py` | 9 | 39 | `src/checks.py` |
| `tests/test_scorer.py` | 5 | 28 | `src/scorer.py` |
| `tests/test_profiler.py` | 2 | 12 | `src/profiler.py` |
| **Total** | **16** | **79** | |

---

## test_checks.py (39 tests)

| Class | Tests | Coverage Focus |
|---|---|---|
| `TestCheckDuplicates` | 5 | PASS (no dups), WARN (< DUP_FAIL), FAIL (> DUP_FAIL), dataset-scope column, result dict keys |
| `TestCheckNulls` | 5 | PASS (no nulls), empty string counted as null, FAIL (high null rate), missing column skipped, all-columns default |
| `TestCheckNumericRange` | 4 | PASS (all in range), negatives flagged, missing column returns empty, max_val boundary |
| `TestCheckOutliers` | 4 | No outliers PASS, obvious outlier detected, fewer than 4 rows skipped, missing column skipped |
| `TestCheckEmailFormat` | 4 | Valid emails PASS, invalid emails flagged, blank values not counted, missing column empty |
| `TestCheckPhoneFormat` | 4 | Valid phone PASS, invalid flagged, blank values not counted, missing column empty |
| `TestCheckCategoricalValues` | 5 | All allowed PASS, invalid flagged, case-insensitive comparison, blanks excluded, missing column |
| `TestCheckUniqueness` | 3 | All unique PASS, duplicates FAIL, missing column empty |
| `TestRunAllChecks` | 5 | Returns list of dicts, all checks run, optional cols skipped when None, score in 0–100, status values valid |

---

## test_scorer.py (28 tests)

| Class | Tests | Coverage Focus |
|---|---|---|
| `TestOverallScore` | 6 | Empty results = 100, all PASS = 100, all FAIL = low score, mixed is between extremes, returns float, known weights applied |
| `TestColumnScores` | 6 | No column checks → empty DataFrame, required columns present, worst_status=FAIL when any FAIL, average score correct, sorted ascending, check counts |
| `TestResultsToDf` | 4 | Returns DataFrame, all keys become columns, FAIL sorted first, empty list → empty DataFrame |
| `TestGrade` | 10 | Parametrized boundary values: 100→A, 95→A, 94.9→B, 85→B, 84.9→C, 70→C, 69.9→D, 55→D, 54.9→F, 0→F |
| `TestStatusColor` | 2 | All three statuses present in STATUS_COLOR, values are hex strings |

---

## test_profiler.py (12 tests)

| Class | Tests | Coverage Focus |
|---|---|---|
| `TestProfileColumn` | 9 | Returns dict, null_count correct (None→"nan" counted), null_pct correct, numeric column has stats (mean/std/min/max), text column stats = None, infers numeric, infers categorical, infers email, infers date |
| `TestProfileDataframe` | 3 | Returns list, length matches column count, column name in each result dict |

**Implementation note:** `is_numeric` is a NumPy boolean (`np.bool_`), not a Python `bool`. Tests use `==` not `is` for these assertions to avoid identity comparison failure.

---

## Known Gaps

| Gap | Risk | Notes |
|---|---|---|
| `app/main.py` not tested | Low | Streamlit UI layer; business logic is in `src/`; UI testing requires a running browser |
| `_infer_type("phone")` not directly tested | Low | Phone inference requires ≥50% of non-blank values to match PHONE_RE; edge case not exercised |
| `_infer_type("empty")` not directly tested | Low | Requires a column where all values are blank or None |
| `check_outliers` does not test mixed-type columns | Low | `pd.to_numeric(..., errors="coerce")` handles mixed types gracefully |
| `check_nulls` does not test "None" string values | Low | `str(v).strip() in ("", "nan", "None")` covers it but not tested explicitly |

---

## Running Tests

```bash
pytest tests/ -v
```

To run a single test class:

```bash
pytest tests/test_profiler.py::TestProfileColumn -v
```

To run with coverage (requires pytest-cov):

```bash
pytest tests/ --cov=src --cov-report=term-missing
```
