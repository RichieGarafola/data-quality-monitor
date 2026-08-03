"""
Data Quality Monitor
Profile any CSV, run quality checks, score every column, surface issues.
"""

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.profiler import profile_dataframe
from src.checks  import run_all_checks
from src.scorer  import overall_score, column_scores, results_to_df, grade, STATUS_COLOR

SAMPLE_PATH = Path(__file__).parent.parent / "data" / "sample" / "sample_procurement.csv"
NAVY = "#1B2A4A"
BLUE = "#2E5FA3"
FONT = dict(family="Inter, Segoe UI, sans-serif", color="#333333")

st.set_page_config(page_title="Data Quality Monitor", page_icon="Q", layout="wide")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Data Quality Monitor")
    st.markdown("---")

    use_sample = st.toggle("Use sample data", value=True)
    uploaded = None
    if not use_sample:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])

    st.markdown("---")
    st.subheader("Column Roles")
    st.caption("Assign roles to enable format checks.")


# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load(path_or_bytes) -> pd.DataFrame:
    if isinstance(path_or_bytes, bytes):
        return pd.read_csv(io.BytesIO(path_or_bytes), dtype=str)
    return pd.read_csv(path_or_bytes, dtype=str)


if use_sample:
    df = load(str(SAMPLE_PATH))
elif uploaded:
    df = load(uploaded.read())
else:
    st.info("Upload a CSV or enable sample data to begin.")
    st.stop()

cols = ["(none)"] + df.columns.tolist()

with st.sidebar:
    email_col = st.selectbox("Email column",  cols, index=cols.index("vendor_email")  if "vendor_email"  in cols else 0)
    phone_col = st.selectbox("Phone column",  cols, index=cols.index("vendor_phone")  if "vendor_phone"  in cols else 0)
    id_col    = st.selectbox("ID column",     cols, index=cols.index("contract_id")   if "contract_id"   in cols else 0)
    state_col = st.selectbox("State column",  cols, index=cols.index("state_code")    if "state_code"    in cols else 0)
    num_cols  = st.multiselect("Numeric columns", df.columns.tolist(),
                               default=[c for c in ["contract_value", "obligation_amount"] if c in df.columns])

email_col = None if email_col == "(none)" else email_col
phone_col = None if phone_col == "(none)" else phone_col
id_col    = None if id_col    == "(none)" else id_col
state_col = None if state_col == "(none)" else state_col


# ── Run checks ─────────────────────────────────────────────────────────────────
@st.cache_data
def run_checks(df_json, email_col, phone_col, id_col, state_col, num_cols_key):
    _df = pd.read_json(io.StringIO(df_json), dtype=str)
    num_cols = json.loads(num_cols_key)
    return run_all_checks(_df, email_col=email_col, phone_col=phone_col,
                          id_col=id_col, state_col=state_col,
                          numeric_cols=num_cols if num_cols else None)


results = run_checks(
    df.to_json(), email_col, phone_col, id_col, state_col,
    json.dumps(num_cols),
)

score      = overall_score(results)
col_sc     = column_scores(results)
grade_lbl  = grade(score)
results_df = results_to_df(results)
profile    = profile_dataframe(df)


# ── Header ─────────────────────────────────────────────────────────────────────
st.header("Data Quality Monitor")
st.caption(f"{len(df):,} rows  ×  {len(df.columns)} columns  |  {len(results)} checks run")
st.markdown("---")

# ── Score banner ───────────────────────────────────────────────────────────────
s_color = "#2ECC71" if score >= 85 else ("#F39C12" if score >= 65 else "#E74C3C")
pass_ct = sum(1 for r in results if r["status"] == "PASS")
warn_ct = sum(1 for r in results if r["status"] == "WARN")
fail_ct = sum(1 for r in results if r["status"] == "FAIL")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Overall Score", f"{score}/100")
c2.metric("Grade", grade_lbl)
c3.metric("PASS", pass_ct)
c4.metric("WARN", warn_ct)
c5.metric("FAIL", fail_ct)

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Check Results", "Column Scores", "Data Profile", "Raw Data"])


# ── Tab 1: Check results ───────────────────────────────────────────────────────
with tab1:
    st.subheader("Quality Check Results")

    def color_status(val):
        return f"color: {STATUS_COLOR.get(val, '#333')}; font-weight: bold"

    def color_score(val):
        if not isinstance(val, (int, float)):
            return ""
        if val >= 85: return "color: #2ECC71"
        if val >= 65: return "color: #F39C12"
        return "color: #E74C3C"

    st.dataframe(
        results_df.style
            .map(color_status, subset=["status"])
            .map(color_score,  subset=["score"])
            .format({"score": "{:.1f}"}),
        use_container_width=True, height=480,
    )

    # Status breakdown donut
    status_counts = results_df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig_donut = go.Figure(go.Pie(
        labels=status_counts["status"],
        values=status_counts["count"],
        hole=0.55,
        marker=dict(colors=[STATUS_COLOR.get(s, "#CCC") for s in status_counts["status"]]),
        textinfo="label+value",
    ))
    fig_donut.update_layout(
        title="Checks by Status",
        height=280, font=FONT,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=40, b=10, l=10, r=10), showlegend=False,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    st.download_button("Download Check Results (.csv)",
                       results_df.to_csv(index=False),
                       "quality_checks.csv", "text/csv")

    # Audit-ready Excel export (Summary + Check Results sheets)
    _xls_buf = io.BytesIO()
    with pd.ExcelWriter(_xls_buf, engine="openpyxl") as _writer:
        pd.DataFrame({
            "Metric": ["Overall Score", "Grade", "PASS", "WARN", "FAIL", "Total Checks"],
            "Value":  [f"{score:.1f}/100", grade_lbl, pass_ct, warn_ct, fail_ct,
                       pass_ct + warn_ct + fail_ct],
        }).to_excel(_writer, sheet_name="Summary", index=False)
        results_df.to_excel(_writer, sheet_name="Check Results", index=False)
    st.download_button(
        "Download Quality Report (.xlsx)",
        _xls_buf.getvalue(),
        "quality_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Tab 2: Column scores ───────────────────────────────────────────────────────
with tab2:
    st.subheader("Quality Score by Column")
    if col_sc.empty:
        st.info("No column-level checks were run.")
    else:
        bar_colors = [STATUS_COLOR.get(s, "#CCC") for s in col_sc["worst_status"]]
        fig_bar = go.Figure(go.Bar(
            x=col_sc["score"], y=col_sc["column"],
            orientation="h", marker_color=bar_colors,
            text=col_sc["score"].apply(lambda v: f"{v:.0f}"),
            textposition="outside",
        ))
        fig_bar.add_vline(x=85, line_dash="dash", line_color="#AAAAAA",
                          annotation_text="Target (85)", annotation_position="top right")
        fig_bar.update_layout(
            title="Column Quality Score (100 = perfect)",
            plot_bgcolor="white", paper_bgcolor="white", font=FONT,
            margin=dict(t=48, b=30, l=10, r=60),
            xaxis=dict(range=[0, 110], showgrid=True, gridcolor="#EEEEEE"),
            yaxis=dict(showgrid=False, autorange="reversed"),
            height=max(300, len(col_sc) * 35),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(
            col_sc.style
                .map(color_status, subset=["worst_status"])
                .map(color_score,  subset=["score"])
                .format({"score": "{:.1f}"}),
            use_container_width=True,
        )


# ── Tab 3: Data Profile ────────────────────────────────────────────────────────
with tab3:
    st.subheader("Column Profile")
    profile_df = pd.DataFrame(profile)
    fmt = {c: "{:.1f}" for c in ["null_pct", "uniqueness_pct", "mean", "std"]}
    fmt.update({c: "{:,.2f}" for c in ["min", "max"]})
    st.dataframe(
        profile_df.style.format(fmt, na_rep="—"),
        use_container_width=True,
    )

    # Null rate bar chart (green → amber → red)
    null_pcts = profile_df[["column", "null_pct"]].sort_values("null_pct", ascending=False)
    fig_null = px.bar(null_pcts, x="column", y="null_pct",
                      color="null_pct",
                      color_continuous_scale=["#2ECC71", "#F39C12", "#E74C3C"],
                      range_color=[0, 30],
                      labels={"null_pct": "Null %", "column": ""},
                      title="Null / Empty % by Column")
    fig_null.update_layout(
        plot_bgcolor="white", paper_bgcolor="white", font=FONT,
        margin=dict(t=48, b=60, l=40, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#EEEEEE", ticksuffix="%"),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_null, use_container_width=True)


# ── Tab 4: Raw data ────────────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Raw Data ({len(df):,} rows)")
    st.dataframe(df, use_container_width=True, height=500)
