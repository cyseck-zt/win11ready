from cpu_support import is_cpu_supported


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_truthy(value):
    return str(value).strip().lower() in ["true", "yes", "1", "enabled", "present"]


def analyze_device(device):
    failures = []

    if _safe_float(device.get("RAM_GB", 0)) < 4:
        failures.append("RAM below 4 GB")

    if _safe_float(device.get("Storage_GB", 0)) < 64:
        failures.append("Storage below 64 GB")

    if not _is_truthy(device.get("TPM_Present", "")):
        failures.append("TPM missing")

    if _safe_float(device.get("TPM_Version", 0)) < 2.0:
        failures.append("TPM version below 2.0")

    if not _is_truthy(device.get("SecureBoot", "")):
        failures.append("Secure Boot disabled")

    processor_name = device.get("Processor", "")
    cpu_supported, cpu_reason = is_cpu_supported(processor_name)
    if not cpu_supported:
        failures.append("Unsupported CPU")

    if _safe_float(device.get("Disk_Free_GB", 0)) < 20:
        failures.append("Low free disk space")

    return {
        "ComputerName": device.get("ComputerName", "Unknown"),
        "Ready": len(failures) == 0,
        "Failures": failures,
        "CpuSupportReason": cpu_reason,
    }
