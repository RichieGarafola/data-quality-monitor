# Changelog
All notable changes to this project are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [1.0.0] — 2026-06-18

### Added
- Rule-engine quality check architecture with 9 configurable check functions
- Weighted composite quality scoring model (severity-weighted by check type)
- Letter grade computation (A–F) on 0–100 scale
- Z-score outlier detection for numeric columns (>3σ threshold)
- Column-level statistical profiling: null rate, uniqueness, type inference, min/max/mean/std
- Inferred type detection per column: numeric, date, email, phone, categorical, text
- PASS / WARN / FAIL threshold system per check type with per-check score
- Interactive Streamlit dashboard: Check Results, Column Scores, Data Profile, Raw Data tabs
- Configurable column role assignment via sidebar (email, phone, ID, state, numeric)
- CSV export of quality check results
- Audit-ready Excel quality report: Summary sheet (score, grade, counts) + Check Results sheet
- Government procurement sample dataset (128 rows, 12 columns) with injected quality issues
- pytest test suite: 79 tests across checks, scorer, and profiler modules
- GitHub Actions CI workflow (Python 3.11, pytest)
- MIT License
