import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiler import profile_column, profile_dataframe


class TestProfileColumn:
    def test_returns_dict(self):
        s = pd.Series(["a", "b", "c"], name="col")
        assert isinstance(profile_column(s), dict)

    def test_null_count_correct(self):
        s = pd.Series(["a", None, "c", None], name="col")
        assert profile_column(s)["null_count"] == 2

    def test_null_pct_correct(self):
        s = pd.Series(["a", None, "c", None], name="col")
        assert abs(profile_column(s)["null_pct"] - 50.0) < 0.01

    def test_numeric_column_has_stats(self):
        s = pd.Series(["10", "20", "30", "40"], name="amount")
        result = profile_column(s)
        assert result["is_numeric"] == True
        assert result["mean"] is not None
        assert result["std"] is not None
        assert result["min"] is not None
        assert result["max"] is not None

    def test_text_column_no_stats(self):
        s = pd.Series(["alpha", "beta", "gamma"], name="label")
        result = profile_column(s)
        assert result["is_numeric"] == False
        assert result["mean"] is None
        assert result["std"] is None

    def test_infers_numeric(self):
        s = pd.Series(["100", "200", "300"], name="value")
        assert profile_column(s)["inferred_type"] == "numeric"

    def test_infers_categorical(self):
        s = pd.Series(["A", "B", "A", "B", "A", "B"] * 10, name="category")
        assert profile_column(s)["inferred_type"] == "categorical"

    def test_infers_email(self):
        s = pd.Series(["alice@example.com", "bob@test.org", "carol@gov.com"], name="email")
        assert profile_column(s)["inferred_type"] == "email"

    def test_infers_date(self):
        s = pd.Series(["2024-01-01", "2024-02-15", "2024-03-20"], name="date")
        assert profile_column(s)["inferred_type"] == "date"


class TestProfileDataframe:
    def test_returns_list(self):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["1", "2"]})
        assert isinstance(profile_dataframe(df), list)

    def test_length_matches_columns(self):
        df = pd.DataFrame({"a": ["x"], "b": ["1"], "c": ["2024-01-01"]})
        assert len(profile_dataframe(df)) == 3

    def test_column_name_in_each_dict(self):
        df = pd.DataFrame({"alpha": ["x", "y"], "beta": ["1", "2"]})
        names = [d["column"] for d in profile_dataframe(df)]
        assert "alpha" in names
        assert "beta" in names
