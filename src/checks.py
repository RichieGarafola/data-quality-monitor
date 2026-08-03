"""
Individual data quality checks.

Each check function returns a list of CheckResult dicts:
  { check, column, status, score, detail, affected_rows, total_rows }

status: "PASS" | "WARN" | "FAIL"
score:  0–100 (100 = perfect)
"""

from __future__ import annotations

import re
import pandas as pd

# ── Thresholds ─────────────────────────────────────────────────────────────────
NULL_WARN  = 5.0    # %
NULL_FAIL  = 15.0
DUP_WARN   = 2.0
DUP_FAIL   = 5.0
OUTLIER_Z  = 3.0    # std deviations
EMAIL_RE   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE   = re.compile(r"^\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$")
US_STATES  = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}


def _result(check, column, affected, total, warn_pct, fail_pct, detail_tmpl) -> dict:
    pct = affected / max(total, 1) * 100
    if pct == 0:
        status, score = "PASS", 100.0
    elif pct <= warn_pct:
        status, score = "WARN", round(100 - pct * 3, 1)
    elif pct <= fail_pct:
        status, score = "WARN", round(100 - pct * 4, 1)
    else:
        status, score = "FAIL", round(max(0, 100 - pct * 5), 1)
    return {
        "check":         check,
        "column":        column,
        "status":        status,
        "score":         max(0.0, score),
        "detail":        detail_tmpl.format(n=affected, pct=round(pct, 1), total=total),
        "affected_rows": int(affected),
        "total_rows":    int(total),
    }


# ── Dataset-level checks ───────────────────────────────────────────────────────

def check_duplicates(df: pd.DataFrame) -> list[dict]:
    n_dup  = int(df.duplicated().sum())
    total  = len(df)
    return [_result("Duplicate Rows", "(dataset)", n_dup, total,
                    DUP_WARN, DUP_FAIL,
                    "{n} duplicate row(s) found ({pct}% of {total})")]


# ── Column-level checks ────────────────────────────────────────────────────────

def check_nulls(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict]:
    results = []
    cols = columns or df.columns.tolist()
    for col in cols:
        if col not in df.columns:
            continue
        blank = df[col].apply(lambda v: str(v).strip() in ("", "nan", "None")).sum()
        results.append(_result("Null / Empty", col, blank, len(df),
                               NULL_WARN, NULL_FAIL,
                               "{n} null/empty value(s) ({pct}% of {total})"))
    return results


def check_numeric_range(df: pd.DataFrame, col: str,
                         min_val: float | None = None,
                         max_val: float | None = None) -> list[dict]:
    if col not in df.columns:
        return []
    series = pd.to_numeric(df[col].replace("", float("nan")), errors="coerce").dropna()
    out_of_range = 0
    if min_val is not None:
        out_of_range += int((series < min_val).sum())
    if max_val is not None:
        out_of_range += int((series > max_val).sum())
    return [_result("Range Check", col, out_of_range, len(df), 1, 5,
                    "{n} value(s) outside expected range ({pct}% of {total})")]


def check_outliers(df: pd.DataFrame, columns: list[str] | None = None) -> list[dict]:
    results = []
    for col in (columns or df.columns):
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col].replace("", float("nan")), errors="coerce").dropna()
        if len(series) < 4:
            continue
        z = (series - series.mean()) / series.std()
        n_out = int((z.abs() > OUTLIER_Z).sum())
        if n_out > 0:
            z_label = f">{OUTLIER_Z:.0f}σ"
            results.append(_result("Outlier (>3σ)", col, n_out, len(df), 2, 8,
                                   "{{n}} outlier(s) detected ({z} from mean) ({{pct}}%)".format(z=z_label)))
    return results


def check_email_format(df: pd.DataFrame, col: str) -> list[dict]:
    if col not in df.columns:
        return []
    non_blank = df[col][df[col].apply(lambda v: str(v).strip() not in ("", "nan", "None"))]
    invalid   = non_blank[~non_blank.apply(lambda v: bool(EMAIL_RE.match(str(v).strip())))]
    return [_result("Email Format", col, len(invalid), len(df), 3, 10,
                    "{n} invalid email address(es) ({pct}% of {total})")]


def check_phone_format(df: pd.DataFrame, col: str) -> list[dict]:
    if col not in df.columns:
        return []
    non_blank = df[col][df[col].apply(lambda v: str(v).strip() not in ("", "nan", "None"))]
    invalid   = non_blank[~non_blank.apply(lambda v: bool(PHONE_RE.match(str(v).strip())))]
    return [_result("Phone Format", col, len(invalid), len(df), 5, 15,
                    "{n} non-standard phone number(s) ({pct}% of {total})")]


def check_categorical_values(df: pd.DataFrame, col: str,
                              allowed: set[str]) -> list[dict]:
    if col not in df.columns:
        return []
    non_blank = df[col][df[col].apply(lambda v: str(v).strip() not in ("", "nan", "None"))]
    invalid   = non_blank[~non_blank.apply(lambda v: str(v).strip().upper() in allowed)]
    return [_result("Allowed Values", col, len(invalid), len(df), 1, 5,
                    "{n} value(s) not in allowed set ({pct}% of {total})")]


def check_uniqueness(df: pd.DataFrame, col: str) -> list[dict]:
    """Flag a column that should be a unique identifier if it has duplicates."""
    if col not in df.columns:
        return []
    n_dup = int(df[col].duplicated(keep=False).sum())
    return [_result("Uniqueness", col, n_dup, len(df), 0, 1,
                    "{n} non-unique value(s) in ID column ({pct}% of {total})")]


# ── Full suite ─────────────────────────────────────────────────────────────────

def run_all_checks(df: pd.DataFrame,
                   email_col:  str | None = None,
                   phone_col:  str | None = None,
                   id_col:     str | None = None,
                   state_col:  str | None = None,
                   numeric_cols: list[str] | None = None) -> list[dict]:
    results = []
    results += check_duplicates(df)
    results += check_nulls(df)
    if email_col:
        results += check_email_format(df, email_col)
    if phone_col:
        results += check_phone_format(df, phone_col)
    if id_col:
        results += check_uniqueness(df, id_col)
    if state_col:
        results += check_categorical_values(df, state_col, US_STATES)
    if numeric_cols:
        results += check_outliers(df, numeric_cols)
        for col in numeric_cols:
            results += check_numeric_range(df, col, min_val=0)
    return results
