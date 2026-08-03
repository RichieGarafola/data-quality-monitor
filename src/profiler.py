"""
Column-level statistical profiling — the first pass before quality checks.
"""

import re
import pandas as pd

EMAIL_RE   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE    = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}")
PHONE_RE   = re.compile(r"^\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$")


def profile_column(series: pd.Series) -> dict:
    """Return a dict of descriptive stats for a single column."""
    total   = len(series)
    blank   = series.apply(lambda v: str(v).strip() in ("", "nan", "None")).sum()
    unique  = series.nunique(dropna=False)
    numeric = pd.to_numeric(series.replace("", float("nan")), errors="coerce")
    n_numeric = numeric.notna().sum()

    stats: dict = {
        "column":        series.name,
        "total_rows":    total,
        "null_count":    int(blank),
        "null_pct":      round(blank / total * 100, 2) if total else 0,
        "unique_count":  int(unique),
        "uniqueness_pct":round(unique / total * 100, 2) if total else 0,
        "is_numeric":    n_numeric / max(total - blank, 1) >= 0.80,
        "inferred_type": _infer_type(series, numeric, blank, total),
    }

    if stats["is_numeric"] and n_numeric > 0:
        stats["min"]    = round(float(numeric.min()), 2)
        stats["max"]    = round(float(numeric.max()), 2)
        stats["mean"]   = round(float(numeric.mean()), 2)
        stats["std"]    = round(float(numeric.std()), 2)
    else:
        stats["min"] = stats["max"] = stats["mean"] = stats["std"] = None

    return stats


def profile_dataframe(df: pd.DataFrame) -> list[dict]:
    return [profile_column(df[col]) for col in df.columns]


def _infer_type(series: pd.Series, numeric: pd.Series,
                blank_count: int, total: int) -> str:
    non_blank = series[series.apply(lambda v: str(v).strip() not in ("", "nan", "None"))]
    if len(non_blank) == 0:
        return "empty"
    n = len(non_blank)
    if numeric.notna().sum() / max(n, 1) >= 0.80:
        return "numeric"
    dates = non_blank.apply(lambda v: bool(DATE_RE.search(str(v))))
    if dates.sum() / n >= 0.70:
        return "date"
    emails = non_blank.apply(lambda v: bool(EMAIL_RE.match(str(v).strip())))
    if emails.sum() / n >= 0.50:
        return "email"
    phones = non_blank.apply(lambda v: bool(PHONE_RE.match(str(v).strip())))
    if phones.sum() / n >= 0.50:
        return "phone"
    if non_blank.nunique() / n <= 0.15:
        return "categorical"
    return "text"
