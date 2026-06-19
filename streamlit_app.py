import streamlit as st
import pandas as pd
from rules import analyze_device


def load_devices(csv_file):
    return pd.read_csv(csv_file)


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


def analyze_dataframe(df):
    results = [analyze_device(row) for _, row in df.iterrows()]
    return results


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

    score_cols = st.columns(3)
    score_cols[0].metric("Total devices", total)
    score_cols[1].metric("Ready for Windows 11", ready)
    score_cols[2].metric("Not ready", not_ready)

    all_failures = [failure for result in results for failure in result["Failures"]]
    failure_counts = pd.Series(all_failures).value_counts()

    st.subheader("Top blockages")
    if not failure_counts.empty:
        st.table(failure_counts.rename_axis("Blocker").reset_index(name="Count"))
    else:
        st.success("No blockers found — all devices are ready.")

    st.subheader("Device readiness details")
    details_df = pd.DataFrame([format_result_row(result) for result in results])
    st.dataframe(details_df, use_container_width=True)

    with st.expander("Show devices with failures"):
        for result in results:
            if not result["Ready"]:
                st.markdown(f"**{result['ComputerName']}**")
                for failure in result["Failures"]:
                    st.write(f"- {failure}")

    if not df.empty:
        export_df = details_df.copy()
        export_csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download readiness results as CSV",
            data=export_csv,
            file_name="windows11_readiness_results.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
