from datetime import date, timedelta
import json

import pandas as pd


def build_history_dataframe(uploaded_json_files):
    """Build an assessment history dataframe from exported assessment JSON files."""
    rows = []

    for uploaded_file in uploaded_json_files or []:
        try:
            summary = json.load(uploaded_file)
            summary_data = summary.get("summary", {})
            rows.append(
                {
                    "Assessment": summary.get("assessment_name", uploaded_file.name),
                    "Organization": summary.get("organization_name", ""),
                    "CreatedAt": summary.get("created_at", ""),
                    "TotalDevices": summary_data.get("total_devices", 0),
                    "ReadinessScore": summary_data.get("readiness_score", 0),
                    "ReadinessGrade": summary_data.get("readiness_grade", ""),
                    "RiskScore": summary_data.get("overall_risk_score", 0),
                    "ReplacementRequired": summary_data.get("replacement_required", 0),
                    "Fixable": summary_data.get("fixable", 0),
                    "EstimatedReplacementCost": summary_data.get("estimated_replacement_cost", 0),
                }
            )
        except Exception:
            rows.append(
                {
                    "Assessment": uploaded_file.name,
                    "Organization": "Unable to parse",
                    "CreatedAt": "",
                    "TotalDevices": 0,
                    "ReadinessScore": 0,
                    "ReadinessGrade": "",
                    "RiskScore": 0,
                    "ReplacementRequired": 0,
                    "Fixable": 0,
                    "EstimatedReplacementCost": 0,
                }
            )

    return pd.DataFrame(rows)


def build_refresh_plan(details_df, replacement_cost_per_device):
    """Build a hardware refresh plan grouped by manufacturer and model."""
    if details_df.empty or "Category" not in details_df.columns:
        return pd.DataFrame()

    replacement_df = details_df[details_df["Category"] == "Replacement Required"].copy()
    if replacement_df.empty:
        return pd.DataFrame()

    plan = (
        replacement_df.groupby(["Manufacturer", "Model"])
        .agg(
            DeviceCount=("ComputerName", "count"),
            AverageRisk=("RiskScore", "mean"),
        )
        .reset_index()
    )

    plan["AverageRisk"] = round(plan["AverageRisk"], 1)
    plan["EstimatedCost"] = plan["DeviceCount"] * replacement_cost_per_device

    return plan.sort_values(
        by=["DeviceCount", "AverageRisk", "EstimatedCost"],
        ascending=[False, False, False],
    )


def build_remediation_work_queue(details_df):
    """Create one row per device/blocker so IT can export actionable work queues."""
    rows = []

    if details_df.empty:
        return pd.DataFrame()

    for _, row in details_df.iterrows():
        failures_text = row.get("Failures", "None")
        if failures_text == "None":
            continue

        for blocker in [failure.strip() for failure in str(failures_text).split(",")]:
            rows.append(
                {
                    "ComputerName": row.get("ComputerName", "Unknown"),
                    "Manufacturer": row.get("Manufacturer", "Unknown"),
                    "Model": row.get("Model", "Unknown"),
                    "Category": row.get("Category", "Unknown"),
                    "RiskScore": row.get("RiskScore", 0),
                    "Blocker": blocker,
                }
            )

    return pd.DataFrame(rows)


def forecast_readiness_date(fixable_count, replacement_count, remediations_per_week, replacements_per_month):
    """Estimate when all fixable and replacement-required devices could be resolved."""
    if remediations_per_week <= 0 and fixable_count > 0:
        return None, "Remediation rate must be greater than 0 to forecast fixable devices."

    if replacements_per_month <= 0 and replacement_count > 0:
        return None, "Replacement rate must be greater than 0 to forecast replacement devices."

    remediation_weeks = 0
    if fixable_count > 0:
        remediation_weeks = -(-fixable_count // remediations_per_week)

    replacement_weeks = 0
    if replacement_count > 0:
        replacement_months = -(-replacement_count // replacements_per_month)
        replacement_weeks = replacement_months * 4

    total_weeks = max(remediation_weeks, replacement_weeks)
    estimated_date = date.today() + timedelta(weeks=total_weeks)

    message = (
        f"Estimated readiness date is {estimated_date.isoformat()} based on "
        f"{remediations_per_week} remediations/week and {replacements_per_month} replacements/month."
    )

    return estimated_date, message
