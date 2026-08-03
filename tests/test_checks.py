"""
Tests for src/checks.py
"""

import pandas as pd
import pytest

from src.checks import (
    check_duplicates,
    check_email_format,
    check_nulls,
    check_numeric_range,
    check_outliers,
    check_phone_format,
    check_categorical_values,
    check_uniqueness,
    run_all_checks,
    US_STATES,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _df(**kwargs):
    return pd.DataFrame(kwargs)


def _first(results):
    assert results, "Expected at least one result dict"
    return results[0]


# ── check_duplicates ───────────────────────────────────────────────────────────

class TestCheckDuplicates:
    def test_no_duplicates_pass(self):
        df = _df(a=["x", "y", "z"])
        r = _first(check_duplicates(df))
        assert r["status"] == "PASS"
        assert r["affected_rows"] == 0
        assert r["score"] == 100.0

    def test_few_duplicates_warn(self):
        df = _df(a=["x", "y", "x", "y", "z"] * 20)
        r = _first(check_duplicates(df))
        assert r["status"] in ("WARN", "FAIL")
        assert r["affected_rows"] > 0

    def test_many_duplicates_fail(self):
        df = _df(a=["x"] * 100)
        r = _first(check_duplicates(df))
        assert r["status"] == "FAIL"
        assert r["score"] < 50

    def test_column_is_dataset(self):
        df = _df(a=["x", "y"])
        r = _first(check_duplicates(df))
        assert r["column"] == "(dataset)"

    def test_result_keys(self):
        df = _df(a=["x"])
        r = _first(check_duplicates(df))
        for key in ("check", "column", "status", "score", "detail", "affected_rows", "total_rows"):
            assert key in r


# ── check_nulls ────────────────────────────────────────────────────────────────

class TestCheckNulls:
    def test_no_nulls_pass(self):
        df = _df(name=["Alice", "Bob", "Carol"])
        results = check_nulls(df, ["name"])
        r = _first(results)
        assert r["status"] == "PASS"

    def test_empty_string_counted(self):
        df = _df(name=["Alice", "", "Carol"])
        results = check_nulls(df, ["name"])
        r = _first(results)
        assert r["affected_rows"] >= 1

    def test_high_null_rate_fail(self):
        df = _df(name=["Alice"] + [""] * 50)
        results = check_nulls(df, ["name"])
        r = _first(results)
        assert r["status"] == "FAIL"

    def test_column_not_in_df_skipped(self):
        df = _df(a=["x"])
        results = check_nulls(df, ["nonexistent"])
        assert results == []

    def test_all_columns_if_none_specified(self):
        df = _df(a=["", "x"], b=["y", ""])
        results = check_nulls(df)
        assert len(results) == 2


# ── check_numeric_range ────────────────────────────────────────────────────────

class TestCheckNumericRange:
    def test_all_in_range_pass(self):
        df = _df(salary=["50000", "75000", "100000"])
        r = _first(check_numeric_range(df, "salary", min_val=0))
        assert r["status"] == "PASS"

    def test_negative_values_flagged(self):
        df = _df(salary=["50000", "-1000", "80000"])
        r = _first(check_numeric_range(df, "salary", min_val=0))
        assert r["affected_rows"] >= 1

    def test_col_not_found_returns_empty(self):
        df = _df(a=["x"])
        assert check_numeric_range(df, "missing_col") == []

    def test_max_val(self):
        df = _df(score=["50", "101", "80"])
        r = _first(check_numeric_range(df, "score", max_val=100))
        assert r["affected_rows"] == 1


# ── check_outliers ─────────────────────────────────────────────────────────────

class TestCheckOutliers:
    def test_no_outliers(self):
        df = _df(x=[str(v) for v in range(50, 60)])
        results = check_outliers(df, ["x"])
        assert results == []   # within 3σ → no outlier

    def test_detects_obvious_outlier(self):
        # 30 normal values + 1 extreme outlier; outlier inflates std less at n=31
        vals = [str(v) for v in ([10] * 30 + [500])]
        df = _df(x=vals)
        results = check_outliers(df, ["x"])
        assert len(results) == 1
        assert results[0]["affected_rows"] >= 1

    def test_too_few_rows_skipped(self):
        df = _df(x=["1", "2", "3"])
        results = check_outliers(df, ["x"])
        assert results == []

    def test_missing_col_skipped(self):
        df = _df(a=["1", "2"])
        results = check_outliers(df, ["nonexistent"])
        assert results == []


# ── check_email_format ─────────────────────────────────────────────────────────

class TestCheckEmailFormat:
    def test_valid_emails_pass(self):
        df = _df(email=["alice@example.com", "bob@gov.org"])
        r = _first(check_email_format(df, "email"))
        assert r["status"] == "PASS"
        assert r["affected_rows"] == 0

    def test_invalid_emails_flagged(self):
        df = _df(email=["alice@example.com", "notanemail", "@missing.com"])
        r = _first(check_email_format(df, "email"))
        assert r["affected_rows"] == 2

    def test_blanks_ignored(self):
        df = _df(email=["alice@example.com", ""])
        r = _first(check_email_format(df, "email"))
        assert r["affected_rows"] == 0

    def test_col_not_found(self):
        df = _df(a=["x"])
        assert check_email_format(df, "missing") == []


# ── check_phone_format ─────────────────────────────────────────────────────────

class TestCheckPhoneFormat:
    def test_valid_phone_pass(self):
        df = _df(phone=["(555) 123-4567", "555-123-4567"])
        r = _first(check_phone_format(df, "phone"))
        assert r["status"] == "PASS"

    def test_invalid_phone_flagged(self):
        df = _df(phone=["(555) 123-4567", "12345"])
        r = _first(check_phone_format(df, "phone"))
        assert r["affected_rows"] == 1

    def test_blanks_ignored(self):
        df = _df(phone=["(555) 123-4567", ""])
        r = _first(check_phone_format(df, "phone"))
        assert r["affected_rows"] == 0

    def test_col_not_found(self):
        df = _df(a=["x"])
        assert check_phone_format(df, "missing") == []


# ── check_categorical_values ───────────────────────────────────────────────────

class TestCheckCategoricalValues:
    def test_all_allowed(self):
        df = _df(state=["VA", "MD", "DC"])
        r = _first(check_categorical_values(df, "state", US_STATES))
        assert r["status"] == "PASS"

    def test_invalid_value_flagged(self):
        df = _df(state=["VA", "ZZ", "XY"])
        r = _first(check_categorical_values(df, "state", US_STATES))
        assert r["affected_rows"] == 2

    def test_case_insensitive_comparison(self):
        df = _df(state=["va", "md"])
        r = _first(check_categorical_values(df, "state", US_STATES))
        assert r["affected_rows"] == 0

    def test_blanks_not_counted(self):
        df = _df(state=["VA", ""])
        r = _first(check_categorical_values(df, "state", US_STATES))
        assert r["affected_rows"] == 0

    def test_col_not_found(self):
        df = _df(a=["x"])
        assert check_categorical_values(df, "missing", US_STATES) == []


# ── check_uniqueness ───────────────────────────────────────────────────────────

class TestCheckUniqueness:
    def test_all_unique_pass(self):
        df = _df(id=["A", "B", "C"])
        r = _first(check_uniqueness(df, "id"))
        assert r["status"] == "PASS"
        assert r["affected_rows"] == 0

    def test_duplicates_fail(self):
        df = _df(id=["A", "A", "B"])
        r = _first(check_uniqueness(df, "id"))
        assert r["status"] == "FAIL"
        assert r["affected_rows"] == 2

    def test_col_not_found(self):
        df = _df(a=["x"])
        assert check_uniqueness(df, "missing") == []


# ── run_all_checks ─────────────────────────────────────────────────────────────

class TestRunAllChecks:
    def _sample_df(self):
        return pd.DataFrame({
            "employee_id": ["E001", "E002", "E003"],
            "email":       ["alice@example.com", "bob@example.com", "bad-email"],
            "phone":       ["(555) 123-4567", "555-000-1111", "12345"],
            "state":       ["VA", "MD", "ZZ"],
            "salary":      ["80000", "90000", "75000"],
        })

    def test_returns_list_of_dicts(self):
        df = self._sample_df()
        results = run_all_checks(df, email_col="email", phone_col="phone",
                                  id_col="employee_id", state_col="state",
                                  numeric_cols=["salary"])
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_all_checks_run(self):
        df = self._sample_df()
        results = run_all_checks(df, email_col="email", phone_col="phone",
                                  id_col="employee_id", state_col="state",
                                  numeric_cols=["salary"])
        check_names = {r["check"] for r in results}
        assert "Duplicate Rows" in check_names
        assert "Null / Empty"   in check_names
        assert "Email Format"   in check_names
        assert "Phone Format"   in check_names
        assert "Uniqueness"     in check_names
        assert "Allowed Values" in check_names

    def test_optional_cols_skipped_when_none(self):
        df = self._sample_df()
        results = run_all_checks(df)
        check_names = {r["check"] for r in results}
        assert "Email Format" not in check_names
        assert "Phone Format" not in check_names

    def test_score_in_range(self):
        df = self._sample_df()
        results = run_all_checks(df, email_col="email")
        for r in results:
            assert 0.0 <= r["score"] <= 100.0

    def test_status_values_valid(self):
        df = self._sample_df()
        results = run_all_checks(df)
        valid = {"PASS", "WARN", "FAIL"}
        for r in results:
            assert r["status"] in valid
