import pandas as pd
import streamlit as st

from assessment_export import build_assessment_summary, assessment_summary_to_json
from column_normalizer import get_missing_required_columns, normalize_columns
from recommendation_engine import build_readiness_interpretation, build_rule_based_recommendations
from report_generator import generate_executive_pdf
from rules import analyze_device


APP_VERSION = "0.6"

REMEDIATIONS = {
    "TPM missing": {
        "action": "Check BIOS/UEFI settings and enable TPM if available. If no TPM hardware exists, replace the device.",
        "priority": "High",
        "category": "Fixable",
    },
    "TPM version below 2.0": {
        "action": "Update TPM firmware if supported. If TPM 2.0 is not available, replace the device.",
        "priority": "High",
        "category": "Fixable",
    },
    "Secure Boot disabled": {
        "action": "Enable Secure Boot in BIOS/UEFI after confirming the device is using UEFI boot mode.",
        "priority": "Medium",
        "category": "Fixable",
    },
    "Unsupported CPU": {
        "action": "Plan for device replacement or confirm whether the system has a supported processor upgrade path.",
        "priority": "Critical",
        "category": "Replacement Required",
    },
    "RAM below 4 GB": {
        "action": "Upgrade memory if supported. If memory is soldered or maxed out, replace the device.",
        "priority": "High",
        "category": "Replacement Required",
    },
    "Storage below 64 GB": {
        "action": "Upgrade internal storage if supported. If storage cannot be upgraded, replace the device.",
        "priority": "High",
        "category": "Replacement Required",
    },
    "Low free disk space": {
        "action": "Free disk space, remove unused applications, clean temporary files, or expand storage.",
        "priority": "Medium",
        "category": "Fixable",
    },
}

RISK_WEIGHTS = {
    "Unsupported CPU": 10,
    "RAM below 4 GB": 8,
    "Storage below 64 GB": 8,
    "TPM missing": 7,
    "TPM version below 2.0": 6,
    "Secure Boot disabled": 4,
    "Low free disk space": 3,
}


def load_devices(csv_file):
    return normalize_columns(pd.read_csv(csv_file))


def analyze_dataframe(df):
    return [analyze_device(row) for _, row in df.iterrows()]


def summarize_results(results):
    total = len(results)
    ready = sum(1 for result in results if result["Ready"])
    return total, ready, total - ready


def get_readiness_grade(readiness_score):
    if readiness_score >= 95:
        return "A"
    if readiness_score >= 85:
        return "B"
    if readiness_score >= 70:
        return "C"
    if readiness_score >= 50:
        return "D"
    return "F"


def categorize_device(failures):
    if not failures:
        return "Ready"
    replacement_blockers = {"Unsupported CPU", "RAM below 4 GB", "Storage below 64 GB"}
    return "Replacement Required" if any(failure in replacement_blockers for failure in failures) else "Fixable"


def calculate_device_risk(failures):
    return sum(RISK_WEIGHTS.get(failure, 1) for failure in failures)


def calculate_overall_risk_score(results):
    if not results:
        return 0
    total_risk = sum(calculate_device_risk(result["Failures"]) for result in results)
    return min(round((total_risk / (len(results) * 10)) * 100), 100)


def build_failure_counts(results):
    all_failures = [failure for result in results for failure in result["Failures"]]
    return pd.Series(all_failures).value_counts()


def build_details_dataframe(results, df):
    rows = []
    for index, result in enumerate(results):
        source_row = df.iloc[index] if index < len(df) else {}
        failures = result["Failures"]
        rows.append(
            {
                "ComputerName": result["ComputerName"],
                "Status": "Ready" if result["Ready"] else "Blocked",
                "Category": categorize_device(failures),
                "Ready": "Yes" if result["Ready"] else "No",
                "RiskScore": calculate_device_risk(failures),
                "Failures": ", ".join(failures) or "None",
                "Manufacturer": source_row.get("Manufacturer", "Unknown"),
                "Model": source_row.get("Model", "Unknown"),
                "Processor": source_row.get("Processor", "Unknown"),
                "RAM_GB": source_row.get("RAM_GB", "Unknown"),
                "Storage_GB": source_row.get("Storage_GB", "Unknown"),
                "TPM_Version": source_row.get("TPM_Version", "Unknown"),
                "SecureBoot": source_row.get("SecureBoot", "Unknown"),
                "Disk_Free_GB": source_row.get("Disk_Free_GB", "Unknown"),
                "OSVersion": source_row.get("OSVersion", "Unknown"),
            }
        )
    return pd.DataFrame(rows)


def build_summary_by_column(details_df, column_name):
    if column_name not in details_df.columns:
        return pd.DataFrame()
    summary = (
        details_df.groupby(column_name)
        .agg(
            Total=("ComputerName", "count"),
            Ready=("Ready", lambda values: (values == "Yes").sum()),
            Blocked=("Ready", lambda values: (values == "No").sum()),
            ReplacementRequired=("Category", lambda values: (values == "Replacement Required").sum()),
            Fixable=("Category", lambda values: (values == "Fixable").sum()),
            AverageRisk=("RiskScore", "mean"),
        )
        .reset_index()
    )
    summary["ReadyPercent"] = round((summary["Ready"] / summary["Total"]) * 100, 1)
    summary["AverageRisk"] = round(summary["AverageRisk"], 1)
    return summary.sort_values(by=["ReplacementRequired", "Blocked", "AverageRisk"], ascending=[False, False, False])


def build_remediation_dataframe(failure_counts):
    rows = []
    for blocker, count in failure_counts.items():
        remediation = REMEDIATIONS.get(
            blocker,
            {"action": "Review this blocker and define a remediation path.", "priority": "Medium", "category": "Fixable"},
        )
        rows.append(
            {
                "Blocker": blocker,
                "AffectedDevices": int(count),
                "Priority": remediation["priority"],
                "LikelyCategory": remediation["category"],
                "RecommendedAction": remediation["action"],
            }
        )
    return pd.DataFrame(rows)


def filter_details_dataframe(details_df, search, status_filter, category_filter):
    filtered_df = details_df.copy()
    if search:
        filtered_df = filtered_df[filtered_df["ComputerName"].astype(str).str.contains(search, case=False, na=False)]
    if status_filter == "Ready":
        filtered_df = filtered_df[filtered_df["Ready"] == "Yes"]
    elif status_filter == "Blocked":
        filtered_df = filtered_df[filtered_df["Ready"] == "No"]
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == category_filter]
    return filtered_df


def show_score_cards(total, ready, not_ready, readiness_score, readiness_grade, overall_risk_score, estimated_replacement_cost):
    score_cols = st.columns(7)
    score_cols[0].metric("Total devices", total)
    score_cols[1].metric("Ready", ready)
    score_cols[2].metric("Blocked", not_ready)
    score_cols[3].metric("Readiness", f"{readiness_score}%")
    score_cols[4].metric("Grade", readiness_grade)
    score_cols[5].metric("Risk", f"{overall_risk_score}/100")
    score_cols[6].metric("Replacement Cost", f"${estimated_replacement_cost:,.0f}")


def show_executive_summary(total, ready, not_ready, readiness_score, readiness_grade, failure_counts, replacement_count, fixable_count, estimated_replacement_cost, recommendations):
    st.subheader("Executive summary")
    st.write(build_readiness_interpretation(readiness_score, readiness_grade))
    if failure_counts.empty:
        st.write(f"{total} devices were assessed. All devices are currently ready for Windows 11.")
    else:
        top_blocker = failure_counts.index[0]
        top_blocker_count = int(failure_counts.iloc[0])
        st.write(
            f"{total} devices were assessed. {ready} devices are ready and {not_ready} require remediation. "
            f"{fixable_count} device(s) appear fixable, while {replacement_count} may require replacement. "
            f"Estimated replacement cost is **${estimated_replacement_cost:,.0f}**. "
            f"Top blocker: **{top_blocker}**, affecting {top_blocker_count} device(s)."
        )
    with st.expander("Recommended next steps", expanded=True):
        for index, recommendation in enumerate(recommendations, start=1):
            st.write(f"{index}. {recommendation}")


def show_import_validation(df, missing_columns):
    st.subheader("Import validation")
    st.write("Use this to verify whether the uploaded export mapped cleanly into Win11Ready's expected schema.")
    detected_columns = pd.DataFrame({"Detected Columns": list(df.columns)})
    st.dataframe(detected_columns, width="stretch")
    if missing_columns:
        st.warning("Missing required columns after normalization: " + ", ".join(missing_columns))
    else:
        st.success("All required columns were found after normalization.")


def show_overview(category_counts, failure_counts):
    st.subheader("Readiness categories")
    if not category_counts.empty:
        category_df = category_counts.rename_axis("Category").reset_index(name="Count")
        st.bar_chart(category_df.set_index("Category"))
        st.table(category_df)
    else:
        st.info("No category data available.")
    st.subheader("Top blockages")
    if not failure_counts.empty:
        blockers_df = failure_counts.rename_axis("Blocker").reset_index(name="Count")
        st.bar_chart(blockers_df.set_index("Blocker"))
        st.table(blockers_df)
    else:
        st.success("No blockers found - all devices are ready.")


def show_hardware(details_df):
    st.subheader("Hardware breakdown")
    manufacturer_summary = build_summary_by_column(details_df, "Manufacturer")
    model_summary = build_summary_by_column(details_df, "Model")
    tab1, tab2 = st.tabs(["Manufacturer summary", "Model summary"])
    with tab1:
        st.dataframe(manufacturer_summary, width="stretch") if not manufacturer_summary.empty else st.info("No manufacturer data found.")
    with tab2:
        st.dataframe(model_summary, width="stretch") if not model_summary.empty else st.info("No model data found.")
    return manufacturer_summary, model_summary


def show_remediation(remediation_df, recommendations):
    st.subheader("Remediation recommendations")
    if remediation_df.empty:
        st.success("No remediation needed based on the current rules.")
    else:
        st.dataframe(remediation_df, width="stretch")
    st.subheader("Recommended next steps")
    for index, recommendation in enumerate(recommendations, start=1):
        st.write(f"{index}. {recommendation}")


def show_devices(details_df):
    st.subheader("Device readiness details")
    filter_cols = st.columns(3)
    with filter_cols[0]:
        search = st.text_input("Search computer name")
    with filter_cols[1]:
        status_filter = st.selectbox("Show devices", ["All", "Ready", "Blocked"])
    with filter_cols[2]:
        category_filter = st.selectbox("Category", ["All", "Ready", "Fixable", "Replacement Required"])
    filtered_df = filter_details_dataframe(details_df, search, status_filter, category_filter)
    st.dataframe(filtered_df, width="stretch")
    return filtered_df


def show_drilldown(details_df):
    st.subheader("Device drill-down")
    if details_df.empty:
        st.info("No device details available.")
        return
    selected_device = st.selectbox("Select a device", details_df["ComputerName"].dropna().astype(str).tolist())
    device_row = details_df[details_df["ComputerName"] == selected_device].iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", str(device_row.get("Status", "Unknown")))
    col2.metric("Category", str(device_row.get("Category", "Unknown")))
    col3.metric("Risk score", str(device_row.get("RiskScore", 0)))
    device_info_columns = ["Manufacturer", "Model", "Processor", "RAM_GB", "Storage_GB", "TPM_Version", "SecureBoot", "Disk_Free_GB", "OSVersion"]
    device_info = {column: str(device_row.get(column, "Unknown")) for column in device_info_columns if column in details_df.columns}
    st.table(pd.DataFrame(device_info.items(), columns=["Field", "Value"]))
    failures_text = device_row.get("Failures", "None")
    st.write("### Failures and recommendations")
    if failures_text == "None":
        st.success("This device is ready for Windows 11.")
        return
    for failure in [failure.strip() for failure in failures_text.split(",")]:
        remediation = REMEDIATIONS.get(failure, {"action": "Review this blocker and define a remediation path.", "priority": "Medium"})
        st.markdown(f"**{failure}**")
        st.write(f"Priority: {remediation['priority']}")
        st.write(f"Recommended action: {remediation['action']}")


def show_reports(assessment_summary, assessment_name, organization_name, prepared_by, total, ready, not_ready, readiness_score, readiness_grade, overall_risk_score, replacement_count, fixable_count, estimated_replacement_cost, category_counts, failure_counts, remediation_df, manufacturer_summary, model_summary, details_df, recommendations):
    st.subheader("Reports")
    pdf_bytes = generate_executive_pdf(
        assessment_name=assessment_name,
        organization_name=organization_name,
        prepared_by=prepared_by,
        total=total,
        ready=ready,
        not_ready=not_ready,
        readiness_score=readiness_score,
        readiness_grade=readiness_grade,
        overall_risk_score=overall_risk_score,
        replacement_count=replacement_count,
        fixable_count=fixable_count,
        estimated_replacement_cost=estimated_replacement_cost,
        category_counts=category_counts,
        failure_counts=failure_counts,
        remediation_df=remediation_df,
        manufacturer_summary=manufacturer_summary,
        model_summary=model_summary,
    )
    safe_name = (assessment_name or "windows11_readiness_report").lower().replace(" ", "_")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button("Download Executive PDF", data=pdf_bytes, file_name=f"{safe_name}.pdf", mime="application/pdf")
    with col2:
        st.download_button("Download Full CSV", data=details_df.to_csv(index=False).encode("utf-8"), file_name="windows11_readiness_full_results.csv", mime="text/csv")
    with col3:
        st.download_button("Download Remediation CSV", data=remediation_df.to_csv(index=False).encode("utf-8"), file_name="windows11_readiness_remediation.csv", mime="text/csv")
    with col4:
        st.download_button("Download Assessment JSON", data=assessment_summary_to_json(assessment_summary), file_name="windows11_readiness_assessment.json", mime="application/json")
    st.subheader("Rule-based recommendations")
    for index, recommendation in enumerate(recommendations, start=1):
        st.write(f"{index}. {recommendation}")


def main():
    st.set_page_config(page_title="Win11Ready", layout="wide")
    st.title("Win11Ready")
    st.caption(f"Windows 11 Readiness Analyzer | Version {APP_VERSION}")
    with st.sidebar:
        st.header("Assessment information")
        organization_name = st.text_input("Organization Name", value="")
        assessment_name = st.text_input("Assessment Name", value="Windows 11 Readiness Assessment")
        prepared_by = st.text_input("Prepared By", value="Jason Hamersley")
        st.header("Assessment settings")
        replacement_cost_per_device = st.number_input("Estimated replacement cost per device", min_value=0, value=1000, step=100)
        st.caption("SCCM-style column names are normalized automatically when possible.")
    uploaded_file = st.file_uploader("Upload a device CSV", type=["csv"])
    use_sample = st.checkbox("Use sample data", value=uploaded_file is None)
    df = None
    if uploaded_file is not None:
        try:
            df = load_devices(uploaded_file)
        except Exception as error:
            st.error(f"Unable to read uploaded CSV: {error}")
    elif use_sample:
        try:
            df = load_devices("data/sample_devices.csv")
            st.info("Loaded sample CSV from data/sample_devices.csv")
        except Exception as error:
            st.error(f"Unable to load sample data: {error}")
    if df is None:
        st.stop()
    missing_columns = get_missing_required_columns(df)
    if missing_columns:
        st.warning("Some required columns were not found after normalization: " + ", ".join(missing_columns) + ". Results may be incomplete.")
    results = analyze_dataframe(df)
    total, ready, not_ready = summarize_results(results)
    readiness_score = round((ready / total) * 100) if total > 0 else 0
    readiness_grade = get_readiness_grade(readiness_score)
    overall_risk_score = calculate_overall_risk_score(results)
    failure_counts = build_failure_counts(results)
    details_df = build_details_dataframe(results, df)
    category_counts = details_df["Category"].value_counts()
    remediation_df = build_remediation_dataframe(failure_counts)
    manufacturer_summary = build_summary_by_column(details_df, "Manufacturer")
    model_summary = build_summary_by_column(details_df, "Model")
    replacement_count = int(category_counts.get("Replacement Required", 0))
    fixable_count = int(category_counts.get("Fixable", 0))
    estimated_replacement_cost = replacement_count * replacement_cost_per_device
    recommendations = build_rule_based_recommendations(readiness_score, overall_risk_score, replacement_count, fixable_count, failure_counts)
    assessment_summary = build_assessment_summary(APP_VERSION, assessment_name, organization_name, prepared_by, total, ready, not_ready, readiness_score, readiness_grade, overall_risk_score, replacement_count, fixable_count, estimated_replacement_cost, category_counts, failure_counts, recommendations)
    show_score_cards(total, ready, not_ready, readiness_score, readiness_grade, overall_risk_score, estimated_replacement_cost)
    show_executive_summary(total, ready, not_ready, readiness_score, readiness_grade, failure_counts, replacement_count, fixable_count, estimated_replacement_cost, recommendations)
    overview_tab, import_tab, hardware_tab, remediation_tab, devices_tab, drilldown_tab, reports_tab = st.tabs(["Overview", "Import Validation", "Hardware", "Remediation", "Devices", "Drill-down", "Reports"])
    with overview_tab:
        show_overview(category_counts, failure_counts)
    with import_tab:
        show_import_validation(df, missing_columns)
    with hardware_tab:
        show_hardware(details_df)
    with remediation_tab:
        show_remediation(remediation_df, recommendations)
    with devices_tab:
        filtered_df = show_devices(details_df)
        st.download_button("Download Filtered CSV", data=filtered_df.to_csv(index=False).encode("utf-8"), file_name="windows11_readiness_filtered_results.csv", mime="text/csv")
    with drilldown_tab:
        show_drilldown(details_df)
    with reports_tab:
        show_reports(assessment_summary, assessment_name, organization_name, prepared_by, total, ready, not_ready, readiness_score, readiness_grade, overall_risk_score, replacement_count, fixable_count, estimated_replacement_cost, category_counts, failure_counts, remediation_df, manufacturer_summary, model_summary, details_df, recommendations)


if __name__ == "__main__":
    main()
