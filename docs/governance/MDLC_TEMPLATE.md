# Model Development Life-Cycle (MDLC) Template

Fill out **every** section prior to production deployment.

---
## 1. Model Overview
* **Model ID**:
* **Name**:
* **Owner**:
* **Business Purpose / Use-case**:
* **Stakeholders**:

## 2. Data Sources
List and describe all raw datasets, including licensing constraints and refresh cadence.

| Source | Description | Point-in-time? | Refresh | Usage |
|--------|-------------|---------------|---------|-------|

## 3. Feature Engineering
Describe transformations, filtering, and aggregation logic. Attach dbt model links when applicable.

## 4. Model Training
* **Algorithm / Library**:
* **Training window**:
* **Hyper-parameters**:
* **Code repo / commit SHA**:

## 5. Validation & Testing
Summarize backtest, out-of-sample, stress, and sensitivity testing results. Attach notebooks or PDFs.

## 6. Deployment
* **Environment**: dev / staging / prod
* **CI/CD pipeline link**:
* **Approval date & sign-off**:

## 7. Monitoring & Performance
Define metrics (IR, factor drift, latency) and thresholds. Include alert routing.

## 8. Documentation & Explainability
Links to SHAP reports, dashboards, and regulatory disclosures.

## 9. Retirement Criteria
Describe triggers and procedures for decommissioning.