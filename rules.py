def analyze_device(device):
    failures = []

    if float(device.get("RAM_GB", 0)) < 4:
        failures.append("RAM below 4 GB")

    if float(device.get("Storage_GB", 0)) < 64:
        failures.append("Storage below 64 GB")

    if str(device.get("TPM_Present", "")).lower() not in ["true", "yes", "1"]:
        failures.append("TPM missing")

    if float(device.get("TPM_Version", 0)) < 2.0:
        failures.append("TPM version below 2.0")

    if str(device.get("SecureBoot", "")).lower() not in ["true", "yes", "1", "enabled"]:
        failures.append("Secure Boot disabled")

    if str(device.get("CPU_Supported", "")).lower() not in ["true", "yes", "1"]:
        failures.append("Unsupported CPU")

    if float(device.get("Disk_Free_GB", 0)) < 20:
        failures.append("Low free disk space")

    return {
        "ComputerName": device.get("ComputerName", "Unknown"),
        "Ready": len(failures) == 0,
        "Failures": failures
    }