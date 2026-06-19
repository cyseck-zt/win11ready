import pandas as pd
from rules import analyze_device
from collections import Counter


def main():
    try:
        input_file = "data/sample_devices.csv"
        print(f"Looking for CSV at: {input_file}")
        
        df = pd.read_csv(input_file)
        print(f"Successfully loaded {len(df)} devices")

        results = []
        all_failures = []

        for _, row in df.iterrows():
            result = analyze_device(row)
            results.append(result)
            all_failures.extend(result["Failures"])

        total_devices = len(results)
        ready_devices = sum(1 for r in results if r["Ready"])
        not_ready_devices = total_devices - ready_devices

        print("\nWindows 11 Readiness Report")
        print("=" * 32)
        print(f"Total Devices: {total_devices}")
        print(f"Ready: {ready_devices}")
        print(f"Not Ready: {not_ready_devices}")

        print("\nTop Blockers:")
        blocker_counts = Counter(all_failures)

        if blocker_counts:
            for blocker, count in blocker_counts.most_common():
                print(f"- {blocker}: {count}")
        else:
            print("- No blockers found")

        print("\nDevice Failures:")
        for result in results:
            if not result["Ready"]:
                print(f"\n{result['ComputerName']}")
                for failure in result["Failures"]:
                    print(f"  - {failure}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()