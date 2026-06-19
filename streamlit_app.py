import streamlit as st
import pandas as pd
from rules import analyze_device


def load_devices(csv_file):
    """Load device inventory data from a CSV file."""
    return pd.read_csv(csv_file)


def summarize_results(results):
    """Return total, ready, and not-ready device counts."""
    total = len(results)
    ready = sum(1 for result in results if result["Ready"])
    not_ready = total - ready
    return total, ready, not_ready


def format_result_row(result):
    """Convert an analyzer result into a clean table row."""
    return {
        "ComputerName": result["ComputerName"],
        "Ready": "Yes" if result["Ready"] else "No",
        "Failures": ", ".join(result["Failures"]) or "None",
    }


def analyze_dataframe(df):
    """Run readiness checks against every device in the dataframe."""
    return [analyze_device(row) for _, row in df.iterrows()]


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


def build_failure_counts(results):
    """Build a count of all readiness blockers."""
    all_failures = [
        failure
        for result in results
        for failure in result["Failures"]
    ]

    return pd.Series(all_failures).value_counts()


def build_details_dataframe(results):
    """Build the detailed device readiness dataframe."""
    details_df = pd.DataFrame([format_result_row(result) for result in results])

    details_df["Status"] = details_df["Ready"].apply(
        lambda value: "🟢 Ready" if value == "Yes" else "🔴 Blocked"
    )

    return details_df[["ComputerName", "Status", "Ready", "Failures"]]


def filter_details_dataframe(details_df, search, status_filter):
    """Filter readiness details by computer name and readiness status."""
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

    return filtered_df


def show_executive_summary(total, ready, not_ready, readiness_score, failure_counts):
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
        f"The most common blocker is **{top_blocker}**, affecting {top_blocker_count} device(s)."
    )


def show_top_blockers(failure_counts):
    """Display top readiness blockers as a chart and table."""
    st.subheader("Top blockages")

    if failure_counts.empty:
        st.success("No blockers found — all devices are ready.")
        return

    blockers_df = failure_counts.rename_axis("Blocker").reset_index(name="Count")

    st.bar_chart(blockers_df.set_index("Blocker"))
    st.table(blockers_df)


def show_device_details(details_df):
    """Display searchable and filterable device readiness results."""
    st.subheader("Device readiness details")

    search = st.text_input("Search computer name")

    status_filter = st.selectbox(
        "Show devices",
        ["All", "Ready", "Blocked"],
    )

    filtered_df = filter_details_dataframe(details_df, search, status_filter)

    st.dataframe(filtered_df, use_container_width=True)

    return filtered_df


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


def show_export_button(filtered_df):
    """Allow the user to export the currently filtered readiness results."""
    export_csv = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download filtered readiness results as CSV",
        data=export_csv,
        file_name="windows11_readiness_results.csv",
        mime="text/csv",
    )


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

    score_cols = st.columns(4)
    score_cols[0].metric("Total devices", total)
    score_cols[1].metric("Ready for Windows 11", ready)
    score_cols[2].metric("Not ready", not_ready)
    score_cols[3].metric("Readiness score", f"{readiness_score}%")

    alert_method, readiness_message = get_readiness_message(readiness_score)
    alert_method(readiness_message)

    failure_counts = build_failure_counts(results)
    details_df = build_details_dataframe(results)

    show_executive_summary(
        total,
        ready,
        not_ready,
        readiness_score,
        failure_counts,
    )

    show_top_blockers(failure_counts)

    filtered_df = show_device_details(details_df)

    show_failed_devices_expander(results)

    show_export_button(filtered_df)


if __name__ == "__main__":
    main()
