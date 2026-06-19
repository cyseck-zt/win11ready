/*
Win11Ready - SCCM Windows 11 Readiness Export Query

Purpose:
Export common hardware inventory data for Win11Ready analysis.

Notes:
- Run from SQL Server Management Studio against the ConfigMgr site database.
- Export results to CSV.
- Secure Boot inventory varies by environment and hardware inventory configuration.
- CPU support is derived inside Win11Ready from the Processor column.
*/

SELECT
    sys.Name0 AS ComputerName,
    cs.Manufacturer0 AS Manufacturer,
    cs.Model0 AS Model,
    pr.Name0 AS Processor,
    ROUND(cs.TotalPhysicalMemory0 / 1024.0 / 1024.0 / 1024.0, 2) AS RAM_GB,
    ROUND(ld.Size0 / 1024.0, 2) AS Storage_GB,
    ROUND(ld.FreeSpace0 / 1024.0, 2) AS Disk_Free_GB,
    CASE
        WHEN tpm.SpecVersion0 IS NULL THEN 'False'
        ELSE 'True'
    END AS TPM_Present,
    COALESCE(tpm.SpecVersion0, '0') AS TPM_Version,
    CASE
        WHEN fw.SecureBoot0 = 1 THEN 'Enabled'
        ELSE 'Disabled'
    END AS SecureBoot,
    os.Caption0 AS OSVersion
FROM v_R_System sys
LEFT JOIN v_GS_COMPUTER_SYSTEM cs
    ON sys.ResourceID = cs.ResourceID
LEFT JOIN v_GS_PROCESSOR pr
    ON sys.ResourceID = pr.ResourceID
LEFT JOIN v_GS_LOGICAL_DISK ld
    ON sys.ResourceID = ld.ResourceID
LEFT JOIN v_GS_TPM tpm
    ON sys.ResourceID = tpm.ResourceID
LEFT JOIN v_GS_FIRMWARE fw
    ON sys.ResourceID = fw.ResourceID
LEFT JOIN v_GS_OPERATING_SYSTEM os
    ON sys.ResourceID = os.ResourceID
WHERE ld.DeviceID0 = 'C:'
ORDER BY sys.Name0;
