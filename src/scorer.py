"""
Aggregate check results into quality scores.
"""

import pandas as pd

STATUS_COLOR = {"PASS": "#2ECC71", "WARN": "#F39C12", "FAIL": "#E74C3C"}
STATUS_ORDER = {"FAIL": 0, "WARN": 1, "PASS": 2}

# Weight by check type (higher = more critical)
CHECK_WEIGHTS = {
    "Duplicate Rows":  1.5,
    "Null / Empty":    1.2,
    "Uniqueness":      1.5,
    "Email Format":    1.0,
    "Phone Format":    0.8,
    "Allowed Values":  1.2,
    "Outlier (>3σ)":   1.0,
    "Range Check":     1.3,
}


def overall_score(results: list[dict]) -> float:
    """Weighted average score across all checks (0–100)."""
    if not results:
        return 100.0
    total_weight = sum(CHECK_WEIGHTS.get(r["check"], 1.0) for r in results)
    weighted_sum = sum(
        r["score"] * CHECK_WEIGHTS.get(r["check"], 1.0)
        for r in results
    )
    return round(weighted_sum / total_weight, 1) if total_weight else 100.0


def column_scores(results: list[dict]) -> pd.DataFrame:
    """Per-column average quality score."""
    col_results = [r for r in results if r["column"] != "(dataset)"]
    if not col_results:
        return pd.DataFrame(columns=["column", "score", "worst_status", "checks"])

    rows = {}
    for r in col_results:
        col = r["column"]
        if col not in rows:
            rows[col] = {"scores": [], "statuses": [], "checks": 0}
        rows[col]["scores"].append(r["score"])
        rows[col]["statuses"].append(r["status"])
        rows[col]["checks"] += 1

    return pd.DataFrame([{
        "column":       col,
        "score":        round(sum(v["scores"]) / len(v["scores"]), 1),
        "worst_status": min(v["statuses"], key=lambda s: STATUS_ORDER.get(s, 99)),
        "checks":       v["checks"],
    } for col, v in rows.items()]).sort_values("score").reset_index(drop=True)


def results_to_df(results: list[dict]) -> pd.DataFrame:
    """Convert raw check results to a display DataFrame."""
    if not results:
        return pd.DataFrame(columns=["check", "column", "status", "score",
                                     "detail", "affected_rows", "total_rows"])
    return pd.DataFrame(results).sort_values(
        by=["status", "score"],
        key=lambda col: col.map(STATUS_ORDER) if col.name == "status" else col,
    ).reset_index(drop=True)


def grade(score: float) -> str:
    if score >= 95: return "A"
    if score >= 85: return "B"
    if score >= 70: return "C"
    if score >= 55: return "D"
    return "F"
