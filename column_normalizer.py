COLUMN_ALIASES = {
    "ComputerName": [
        "ComputerName",
        "Computer Name",
        "Device Name",
        "DeviceName",
        "Name",
        "Resource Name",
        "Netbios Name",
        "Netbios_Name0",
    ],
    "Manufacturer": [
        "Manufacturer",
        "System Manufacturer",
        "Device Manufacturer",
        "Vendor",
        "Manufacturer0",
    ],
    "Model": [
        "Model",
        "System Model",
        "Device Model",
        "Computer Model",
        "Model0",
    ],
    "Processor": [
        "Processor",
        "CPU",
        "CPU Name",
        "Processor Name",
        "Name0",
        "Processor0",
    ],
    "RAM_GB": [
        "RAM_GB",
        "RAM GB",
        "Memory_GB",
        "Memory GB",
        "Installed Memory",
        "Total Physical Memory",
        "Total Physical Memory GB",
        "TotalPhysicalMemoryGB",
        "TotalPhysicalMemory0",
    ],
    "Storage_GB": [
        "Storage_GB",
        "Storage GB",
        "Disk Size",
        "Disk Size GB",
        "Total Disk Space",
        "Total Storage",
        "Size0",
    ],
    "TPM_Present": [
        "TPM_Present",
        "TPM Present",
        "TPM Enabled",
        "TPM",
        "Is TPM Present",
        "IsEnabled_InitialValue0",
        "IsActivated_InitialValue0",
        "IsOwned_InitialValue0",
    ],
    "TPM_Version": [
        "TPM_Version",
        "TPM Version",
        "TPM Spec Version",
        "TPM SpecVersion",
        "SpecVersion0",
    ],
    "SecureBoot": [
        "SecureBoot",
        "Secure Boot",
        "Secure Boot Enabled",
        "UEFI Secure Boot",
        "SecureBoot0",
    ],
    "Disk_Free_GB": [
        "Disk_Free_GB",
        "Disk Free GB",
        "Free Disk Space",
        "Free Space GB",
        "Available Storage",
        "Available Disk Space",
        "FreeSpace0",
    ],
    "OSVersion": [
        "OSVersion",
        "OS Version",
        "Operating System",
        "OperatingSystem",
        "Windows Version",
        "Caption0",
        "BuildNumber0",
    ],
}


def normalize_column_name(name):
    return str(name).strip().lower().replace("_", " ").replace("-", " ")


def normalize_columns(df):
    """Rename common SCCM/export column names into the app's expected schema."""
    normalized_lookup = {
        normalize_column_name(column): column
        for column in df.columns
    }

    rename_map = {}

    for expected_column, aliases in COLUMN_ALIASES.items():
        if expected_column in df.columns:
            continue

        for alias in aliases:
            alias_key = normalize_column_name(alias)
            if alias_key in normalized_lookup:
                rename_map[normalized_lookup[alias_key]] = expected_column
                break

    return df.rename(columns=rename_map)


def get_missing_required_columns(df):
    required_columns = [
        "ComputerName",
        "RAM_GB",
        "Storage_GB",
        "TPM_Present",
        "TPM_Version",
        "SecureBoot",
        "Disk_Free_GB",
        "Processor",
    ]

    return [column for column in required_columns if column not in df.columns]
