import streamlit as st
import pandas as pd
from rules import analyze_device


def load_devices(csv_file):
    return pd.read_csv(csv_file)


def analyze_dataframe(df):
    return [analyze_device(row) for _, row in df.iterrows()]


def summarize_results(results):
    total = len(results)
    ready = sum(1 for r in results if r["Ready"])
    not_ready = total - ready
    return total, ready, not_ready


def format_result_row(result):
    return {
        "ComputerName": result["ComputerName"],
        "Ready": "Yes" if result["Ready"] else "No",
        "Failures": ", ".join(result["Failures"]) or "None"
    }


def main():
    st.set_page_config(page_title="Windows 11 Readiness", layout="wide")

    st.title("Windows 11 Readiness Checker")
    st.write(
        "Upload a device inventory CSV or use the sample data to see which machines are ready for Windows 11 and which ones need fixes."
    )

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

    results = analyze_dataframe(df)
    total, ready, not_ready = summarize_results(results)

    readiness_score = round((ready / total) * 100) if total > 0 else 0

    score_cols = st.columns(4)
    score_cols[0].metric("Total devices", total)
    score_cols[1].metric("Ready for Windows 11", ready)
    score_cols[2].metric("Not ready", not_ready)
    score_cols[3].metric("Readiness score", f"{readiness_score}%")

    if readiness_score >= 90:
        st.success(f"Readiness Score: {readiness_score}% - Strong readiness for Windows 11 deployment.")
    elif readiness_score >= 70:
        st.warning(f"Readiness Score: {readiness_score}% - Some remediation is needed before deployment.")
    else:
        st.error(f"Readiness Score: {readiness_score}% - Significant remediation is needed before deployment.")

    all_failures = [failure for result in results for failure in result["Failures"]]
    failure_counts = pd.Series(all_failures).value_counts()

    st.subheader("Executive summary")

    if not failure_counts.empty:
        top_blocker = failure_counts.index[0]
        st.write(
            f"{total} devices were assessed. "
            f"{ready} devices are ready for Windows 11 and {not_ready} require remediation. "
            f"The current readiness score is {readiness_score}%. "
            f"The most common blocker is: **{top_blocker}**."
        )
    else:
        st.write(
            f"{total} devices were assessed. All devices are currently ready for Windows 11."
        )

    st.subheader("Top blockages")

    if not failure_counts.empty:
        blockers_df = failure_counts.rename_axis("Blocker").reset_index(name="Count")

        st.bar_chart(blockers_df.set_index("Blocker"))

        st.table(blockers_df)
    else:
        st.success("No blockers found — all devices are ready.")

    st.subheader("Device readiness details")

    details_df = pd.DataFrame([format_result_row(result) for result in results])

    details_df["Status"] = details_df["Ready"].apply(
        lambda value: "🟢 Ready" if value == "Yes" else "🔴 Blocked"
    )

    details_df = details_df[
        ["ComputerName", "Status", "Ready", "Failures"]
    ]

    search = st.text_input("Search computer name")

    status_filter = st.selectbox(
        "Show devices",
        ["All", "Ready", "Blocked"]
    )

    filtered_df = details_df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["ComputerName"].str.contains(search, case=False, na=False)
        ]

    if status_filter == "Ready":
        filtered_df = filtered_df[filtered_df["Ready"] == "Yes"]
    elif status_filter == "Blocked":
        filtered_df = filtered_df[filtered_df["Ready"] == "No"]

    st.dataframe(filtered_df, use_container_width=True)

    with st.expander("Show devices with failures"):
        for result in results:
            if not result["Ready"]:
                st.markdown(f"**{result['ComputerName']}**")
                for failure in result["Failures"]:
                    st.write(f"- {failure}")

    export_csv = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download filtered readiness results as CSV",
        data=export_csv,
        file_name="windows11_readiness_results.csv",
        mime="text/csv",
    )