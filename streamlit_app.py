import streamlit as st
import pandas as pd
from rules import analyze_device


# -----------------------------
# Configuration
# -----------------------------

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


# -----------------------------
# Data Loading and Analysis
# -----------------------------

def load_devices(csv_file):
    """Load device inventory data from a CSV file."""
    return pd.read_csv(csv_file)


def analyze_dataframe(df):
    """Run readiness checks against every device in the dataframe."""
    return [analyze_device(row) for _, row in df.iterrows()]


def summarize_results(results):
    """Return total, ready, and not-ready device counts."""
    total = len(results)
    ready = sum(1 for result in results if result["Ready"])
    not_ready = total - ready
    return total, ready, not_ready


def build_failure_counts(results):
    """Build a count of all readiness blockers."""
    all_failures = [
        failure
        for result in results
        for failure in result["Failures"]
    ]

    return pd.Series(all_failures).value_counts()


# -----------------------------
# Categorization and Risk
# -----------------------------

def categorize_device(failures):
    """
    Categorize a device into:
    - Ready
    - Fixable
    - Replacement Required
    """
    if not failures:
        return "Ready"

    replacement_blockers = {
        "Unsupported CPU",
        "RAM below 4 GB",
        "Storage below 64 GB",
    }

    if any(failure in replacement_blockers for failure in failures):
        return "Replacement Required"

    return "Fixable"


def calculate_device_risk(failures):
    """Calculate risk score for a single device."""
    return sum(RISK_WEIGHTS.get(failure, 1) for failure in failures)


def calculate_overall_risk_score(results):
    """Calculate overall risk score from 0 to 100. Higher means more risk."""
    if not results:
        return 0

    total_risk = sum(calculate_device_risk(result["Failures"]) for result in results)
    max_reasonable_risk = len(results) * 10

    return min(round((total_risk / max_reasonable_risk) * 100), 100)


def get_risk_label(risk_score):
    """Return a friendly risk label."""
    if risk_score >= 70:
        return "High Risk"

    if risk_score >= 40:
        return "Moderate Risk"

    return "Low Risk"


# -----------------------------
# DataFrame Builders
# -----------------------------

def format_result_row(result, source_row=None):
    """Convert an analyzer result into a clean table row."""
    failures = result["Failures"]
    category = categorize_device(failures)
    risk_score = calculate_device_risk(failures)

    row = {
        "ComputerName": result["ComputerName"],
        "Status": "Ready" if result["Ready"] else "Blocked",
        "Category": category,
        "Ready": "Yes" if result["Ready"] else "No",
        "RiskScore": risk_score,
        "Failures": ", ".join(failures) or "None",
    }

    if source_row is not None:
        row["Manufacturer"] = source_row.get("Manufacturer", "Unknown")
        row["Model"] = source_row.get("Model", "Unknown")
        row["Processor"] = source_row.get("Processor", "Unknown")
        row["RAM_GB"] = source_row.get("RAM_GB", "Unknown")
        row["Storage_GB"] = source_row.get("Storage_GB", "Unknown")
        row["TPM_Version"] = source_row.get("TPM_Version", "Unknown")
        row["SecureBoot"] = source_row.get("SecureBoot", "Unknown")
        row["Disk_Free_GB"] = source_row.get("Disk_Free_GB", "Unknown")
        row["OSVersion"] = source_row.get("OSVersion", "Unknown")

    return row


def build_details_dataframe(results, df):
    """Build the detailed device readiness dataframe."""
    rows = []

    for index, result in enumerate(results):
        source_row = df.iloc[index] if index < len(df) else None
        rows.append(format_result_row(result, source_row))

    return pd.DataFrame(rows)


def build_category_counts(details_df):
    """Build category counts."""
    if "Category" not in details_df.columns:
        return pd.Series(dtype="int64")

    return details_df["Category"].value_counts()


def build_summary_by_column(details_df, column_name):
    """Build readiness summary by a selected column like Manufacturer or Model."""
    if column_name not in details_df.columns:
        return pd.DataFrame()

    summary = (
        details_df
        .groupby(column_name)
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

    return summary.sort_values(
        by=["ReplacementRequired", "Blocked", "AverageRisk"],
        ascending=[False, False, False],
    )


def build_remediation_dataframe(failure_counts):
    """Build remediation guidance dataframe from blocker counts."""
    rows = []

    for blocker, count in failure_counts.items():
        remediation = REMEDIATIONS.get(
            blocker,
            {
                "action": "Review this blocker and define a remediation path.",
                "priority": "Medium",
                "category": "Fixable",
            },
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


# -----------------------------
# Filtering
# -----------------------------

def filter_details_dataframe(details_df, search, status_filter, category_filter):
    """Filter readiness details by computer name, readiness status, and category."""
    filtered_df = details_df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["ComputerName"].str.contains(
                search,
                case=False,
                na=False,
            )
        ]

    if status_filter == "Ready":
        filtered_df = filtered_df[filtered_df["Ready"] == "Yes"]
    elif status_filter == "Blocked":
        filtered_df = filtered_df[filtered_df["Ready"] == "No"]

    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["Category"] == category_filter]

    return filtered_df


# -----------------------------
# Display Helpers
# -----------------------------

def get_readiness_message(readiness_score):
    """Return a Streamlit alert method and message based on readiness score."""
    if readiness_score >= 90:
        return (
            st.success,
            f"Readiness Score: {readiness_score}% - Strong readiness for Windows 11 deployment.",
        )

    if readiness_score >= 70:
        return (
            st.warning,
            f"Readiness Score: {readiness_score}% - Some remediation is needed before deployment.",
        )

    return (
        st.error,
        f"Readiness Score: {readiness_score}% - Significant remediation is needed before deployment.",
    )


def show_score_cards(total, ready, not_ready, readiness_score, overall_risk_score, estimated_replacement_cost):
    """Display the main score cards."""
    score_cols = st.columns(6)

    score_cols[0].metric("Total devices", total)
    score_cols[1].metric("Ready", ready)
    score_cols[2].metric("Blocked", not_ready)
    score_cols[3].metric("Readiness score", f"{readiness_score}%")
    score_cols[4].metric("Risk score", f"{overall_risk_score}/100")
    score_cols[5].metric("Est. replacement cost", f"${estimated_replacement_cost:,.0f}")

    alert_method, readiness_message = get_readiness_message(readiness_score)
    alert_method(readiness_message)

    risk_label = get_risk_label(overall_risk_score)

    if overall_risk_score >= 70:
        st.error(f"Overall Risk: {risk_label}")
    elif overall_risk_score >= 40:
        st.warning(f"Overall Risk: {risk_label}")
    else:
        st.success(f"Overall Risk: {risk_label}")


def show_executive_summary(total, ready, not_ready, readiness_score, failure_counts, category_counts, replacement_count, fixable_count, estimated_replacement_cost):
    """Display a plain-English executive summary."""
    st.subheader("Executive summary")

    if total == 0:
        st.info("No devices were found in the uploaded inventory.")
        return

    if failure_counts.empty:
        st.write(
            f"{total} devices were assessed. "
            f"All devices are currently ready for Windows 11. "
            f"The readiness score is {readiness_score}%."
        )
        return

    top_blocker = failure_counts.index[0]
    top_blocker_count = int(failure_counts.iloc[0])

    st.write(
        f"{total} devices were assessed. "
        f"{ready} devices are ready for Windows 11 and {not_ready} require remediation. "
        f"The current readiness score is {readiness_score}%. "
        f"{fixable_count} device(s) appear fixable through remediation, while "
        f"{replacement_count} device(s) may require replacement. "
        f"Estimated replacement cost is **${estimated_replacement_cost:,.0f}**. "
        f"The most common blocker is **{top_blocker}**, affecting {top_blocker_count} device(s)."
    )

    if not category_counts.empty:
        category_text = ", ".join(
            f"{category}: {count}"
            for category, count in category_counts.items()
        )
        st.caption(f"Category breakdown: {category_text}")


def show_category_breakdown(category_counts):
    """Display readiness category breakdown."""
    st.subheader("Readiness categories")

    if category_counts.empty:
        st.info("No category data available.")
        return

    category_df = category_counts.rename_axis("Category").reset_index(name="Count")

    st.bar_chart(category_df.set_index("Category"))
    st.table(category_df)


def show_top_blockers(failure_counts):
    """Display top readiness blockers as a chart and table."""
    st.subheader("Top blockages")

    if failure_counts.empty:
        st.success("No blockers found - all devices are ready.")
        return

    blockers_df = failure_counts.rename_axis("Blocker").reset_index(name="Count")

    st.bar_chart(blockers_df.set_index("Blocker"))
    st.table(blockers_df)


def show_remediation_panel(failure_counts):
    """Display remediation guidance."""
    st.subheader("Remediation recommendations")

    if failure_counts.empty:
        st.success("No remediation needed based on the current rules.")
        return

    remediation_df = build_remediation_dataframe(failure_counts)
    st.dataframe(remediation_df, use_container_width=True)


def show_manufacturer_and_model_breakdowns(details_df):
    """Display manufacturer and model readiness summaries."""
    st.subheader("Hardware breakdown")

    manufacturer_summary = build_summary_by_column(details_df, "Manufacturer")
    model_summary = build_summary_by_column(details_df, "Model")

    tab1, tab2 = st.tabs(["Manufacturer summary", "Model summary"])

    with tab1:
        if manufacturer_summary.empty:
            st.info("Manufacturer data was not found in the uploaded CSV.")
        else:
            st.dataframe(manufacturer_summary, use_container_width=True)

    with tab2:
        if model_summary.empty:
            st.info("Model data was not found in the uploaded CSV.")
        else:
            st.dataframe(model_summary, use_container_width=True)


def show_device_details(details_df):
    """Display searchable and filterable device readiness results."""
    st.subheader("Device readiness details")

    filter_cols = st.columns(3)

    with filter_cols[0]:
        search = st.text_input("Search computer name")

    with filter_cols[1]:
        status_filter = st.selectbox(
            "Show devices",
            ["All", "Ready", "Blocked"],
        )

    with filter_cols[2]:
        category_filter = st.selectbox(
            "Category",
            ["All", "Ready", "Fixable", "Replacement Required"],
        )

    filtered_df = filter_details_dataframe(
        details_df,
        search,
        status_filter,
        category_filter,
    )

    st.dataframe(filtered_df, use_container_width=True)

    return filtered_df


def show_device_drilldown(details_df):
    """Display a drill-down view for a selected device."""
    st.subheader("Device drill-down")

    if details_df.empty:
        st.info("No device details available.")
        return

    device_names = details_df["ComputerName"].dropna().astype(str).tolist()

    selected_device = st.selectbox(
        "Select a device",
        device_names,
    )

    device_row = details_df[details_df["ComputerName"] == selected_device].iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric("Status", device_row.get("Status", "Unknown"))
    col2.metric("Category", device_row.get("Category", "Unknown"))
    col3.metric("Risk score", device_row.get("RiskScore", 0))

    st.write("### Device information")

    device_info_columns = [
        "Manufacturer",
        "Model",
        "Processor",
        "RAM_GB",
        "Storage_GB",
        "TPM_Version",
        "SecureBoot",
        "Disk_Free_GB",
        "OSVersion",
    ]

    device_info = {
        column: device_row.get(column, "Unknown")
        for column in device_info_columns
        if column in details_df.columns
    }

    st.table(pd.DataFrame(device_info.items(), columns=["Field", "Value"]))

    st.write("### Failures and recommendations")

    failures_text = device_row.get("Failures", "None")

    if failures_text == "None":
        st.success("This device is ready for Windows 11.")
        return

    failures = [failure.strip() for failure in failures_text.split(",")]

    for failure in failures:
        remediation = REMEDIATIONS.get(
            failure,
            {
                "action": "Review this blocker and define a remediation path.",
                "priority": "Medium",
                "category": "Fixable",
            },
        )

        st.markdown(f"**{failure}**")
        st.write(f"Priority: {remediation['priority']}")
        st.write(f"Recommended action: {remediation['action']}")


def show_failed_devices_expander(results):
    """Display a simple expanded view of devices with failures."""
    with st.expander("Show devices with failures"):
        failed_devices = [result for result in results if not result["Ready"]]

        if not failed_devices:
            st.write("No failed devices found.")
            return

        for result in failed_devices:
            st.markdown(f"**{result['ComputerName']}**")
            for failure in result["Failures"]:
                st.write(f"- {failure}")


def show_export_buttons(filtered_df, details_df):
    """Allow the user to export filtered or full readiness results."""
    export_cols = st.columns(2)

    filtered_csv = filtered_df.to_csv(index=False).encode("utf-8")
    full_csv = details_df.to_csv(index=False).encode("utf-8")

    with export_cols[0]:
        st.download_button(
            label="Download filtered results as CSV",
            data=filtered_csv,
            file_name="windows11_readiness_filtered_results.csv",
            mime="text/csv",
        )

    with export_cols[1]:
        st.download_button(
            label="Download full results as CSV",
            data=full_csv,
            file_name="windows11_readiness_full_results.csv",
            mime="text/csv",
        )


# -----------------------------
# Main App
# -----------------------------

def main():
    st.set_page_config(
        page_title="Windows 11 Readiness",
        layout="wide",
    )

    st.title("Windows 11 Readiness Checker")
    st.write(
        "Upload a device inventory CSV or use the sample data to see which machines "
        "are ready for Windows 11 and which ones need fixes."
    )

    with st.sidebar:
        st.header("Assessment settings")

        replacement_cost_per_device = st.number_input(
            "Estimated replacement cost per device",
            min_value=0,
            value=1000,
            step=100,
        )

        st.caption(
            "Used for budget forecasting when devices are categorized as replacement required."
        )

    uploaded_file = st.file_uploader(
        "Upload a device CSV",
        type=["csv"],
    )

    use_sample = st.checkbox(
        "Use sample data",
        value=uploaded_file is None,
    )

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

    results = analyze_dataframe(df)
    total, ready, not_ready = summarize_results(results)

    readiness_score = round((ready / total) * 100) if total > 0 else 0
    overall_risk_score = calculate_overall_risk_score(results)

    failure_counts = build_failure_counts(results)
    details_df = build_details_dataframe(results, df)
    category_counts = build_category_counts(details_df)

    replacement_count = int(category_counts.get("Replacement Required", 0))
    fixable_count = int(category_counts.get("Fixable", 0))
    estimated_replacement_cost = replacement_count * replacement_cost_per_device

    show_score_cards(
        total,
        ready,
        not_ready,
        readiness_score,
        overall_risk_score,
        estimated_replacement_cost,
    )

    show_executive_summary(
        total,
        ready,
        not_ready,
        readiness_score,
        failure_counts,
        category_counts,
        replacement_count,
        fixable_count,
        estimated_replacement_cost,
    )

    overview_tab, hardware_tab, remediation_tab, devices_tab, drilldown_tab = st.tabs(
        [
            "Overview",
            "Hardware",
            "Remediation",
            "Devices",
            "Drill-down",
        ]
    )

    with overview_tab:
        show_category_breakdown(category_counts)
        show_top_blockers(failure_counts)

    with hardware_tab:
        show_manufacturer_and_model_breakdowns(details_df)

    with remediation_tab:
        show_remediation_panel(failure_counts)

    with devices_tab:
        filtered_df = show_device_details(details_df)
        show_failed_devices_expander(results)
        show_export_buttons(filtered_df, details_df)

    with drilldown_tab:
        show_device_drilldown(details_df)


if __name__ == "__main__":
    main()
