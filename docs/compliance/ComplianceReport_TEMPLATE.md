# Compliance Report – {{ model_name }}

**Report Date**: {{ report_date }}

## 1. Overview
* **Model ID**: {{ model_id }}
* **Version**: {{ version }}
* **Owner**: {{ owner }}
* **Purpose**: {{ purpose }}

## 2. Performance Snapshot
| Metric | Value |
|--------|-------|
| Total Return | {{ total_return }} |
| Annualized Return | {{ annualized_return }} |
| Annualized Volatility | {{ annualized_vol }} |
| Sharpe Ratio | {{ sharpe }} |
| Max Drawdown | {{ max_drawdown }} |

## 3. Alerts & Threshold Breaches
{{ alerts_section }}

## 4. Data Quality Summary
* Columns tested: {{ columns_tested }}
* Failed expectations: {{ failed_expectations }}

## 5. Model Changes Since Last Report
{{ changes_log }}

---
Generated automatically via `compliance/generate_report.py`.