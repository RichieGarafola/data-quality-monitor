"""
Tests for src/scorer.py
"""

import pandas as pd
import pytest

from src.scorer import overall_score, column_scores, results_to_df, grade, STATUS_COLOR


# ── Fixtures / helpers ─────────────────────────────────────────────────────────

def _result(check="Null / Empty", column="a", status="PASS", score=100.0):
    return {
        "check":         check,
        "column":        column,
        "status":        status,
        "score":         score,
        "detail":        "test",
        "affected_rows": 0,
        "total_rows":    100,
    }


PERFECT = [_result(score=100.0)]
FAILED  = [_result(status="FAIL", score=10.0)]
MIXED   = [
    _result(column="a", status="PASS", score=100.0),
    _result(column="b", status="FAIL", score=20.0),
    _result(column="c", status="WARN", score=70.0),
]


# ── overall_score ──────────────────────────────────────────────────────────────

class TestOverallScore:
    def test_empty_results_is_100(self):
        assert overall_score([]) == 100.0

    def test_perfect_results(self):
        assert overall_score(PERFECT) == 100.0

    def test_all_failed(self):
        score = overall_score(FAILED)
        assert score < 50

    def test_mixed_is_between_extremes(self):
        score = overall_score(MIXED)
        assert 20 < score < 100

    def test_returns_float(self):
        assert isinstance(overall_score(MIXED), float)

    def test_known_weights_applied(self):
        dup = _result(check="Duplicate Rows", score=50.0)   # weight 1.5
        null = _result(check="Null / Empty", score=100.0)   # weight 1.2
        score = overall_score([dup, null])
        # Expect weighted average closer to dup (lower weight is 1.5 vs 1.2)
        manual = (50.0 * 1.5 + 100.0 * 1.2) / (1.5 + 1.2)
        assert abs(score - round(manual, 1)) < 0.01


# ── column_scores ──────────────────────────────────────────────────────────────

class TestColumnScores:
    def test_no_column_checks_empty_df(self):
        results = [_result(column="(dataset)")]
        df = column_scores(results)
        assert df.empty

    def test_columns_present(self):
        df = column_scores(MIXED)
        assert set(df.columns) >= {"column", "score", "worst_status", "checks"}

    def test_worst_status_is_fail(self):
        results = [
            _result(column="x", status="PASS", score=100.0),
            _result(column="x", status="FAIL", score=10.0),
        ]
        df = column_scores(results)
        row = df[df["column"] == "x"].iloc[0]
        assert row["worst_status"] == "FAIL"

    def test_average_score(self):
        results = [
            _result(column="x", score=80.0),
            _result(column="x", score=60.0),
        ]
        df = column_scores(results)
        assert df[df["column"] == "x"]["score"].iloc[0] == pytest.approx(70.0)

    def test_sorted_ascending(self):
        results = [
            _result(column="good", score=100.0),
            _result(column="bad",  score=10.0),
        ]
        df = column_scores(results)
        assert df.iloc[0]["column"] == "bad"

    def test_checks_count(self):
        results = [
            _result(column="x"),
            _result(column="x"),
            _result(column="x"),
        ]
        df = column_scores(results)
        assert df.iloc[0]["checks"] == 3


# ── results_to_df ──────────────────────────────────────────────────────────────

class TestResultsToDf:
    def test_returns_dataframe(self):
        assert isinstance(results_to_df(MIXED), pd.DataFrame)

    def test_all_keys_become_columns(self):
        df = results_to_df(MIXED)
        for key in ("check", "column", "status", "score", "detail", "affected_rows", "total_rows"):
            assert key in df.columns

    def test_fail_sorted_first(self):
        df = results_to_df(MIXED)
        assert df.iloc[0]["status"] == "FAIL"

    def test_empty_list_empty_df(self):
        df = results_to_df([])
        assert df.empty


# ── grade ──────────────────────────────────────────────────────────────────────

class TestGrade:
    @pytest.mark.parametrize("score,expected", [
        (100.0, "A"),
        (95.0,  "A"),
        (94.9,  "B"),
        (85.0,  "B"),
        (84.9,  "C"),
        (70.0,  "C"),
        (69.9,  "D"),
        (55.0,  "D"),
        (54.9,  "F"),
        (0.0,   "F"),
    ])
    def test_grade_boundaries(self, score, expected):
        assert grade(score) == expected


# ── STATUS_COLOR ───────────────────────────────────────────────────────────────

class TestStatusColor:
    def test_all_statuses_present(self):
        for s in ("PASS", "WARN", "FAIL"):
            assert s in STATUS_COLOR

    def test_values_are_hex(self):
        for v in STATUS_COLOR.values():
            assert v.startswith("#")
