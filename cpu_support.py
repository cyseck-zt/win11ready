import re


SUPPORTED_INTEL_CORE_MIN_GENERATION = 8
SUPPORTED_AMD_RYZEN_MIN_GENERATION = 2


def _extract_intel_core_generation(processor_name):
    """Extract Intel Core generation from common names like i5-8350U or i7-1165G7."""
    processor_name = str(processor_name)
    match = re.search(r"i[3579][-\s]?(\d{4,5})", processor_name, flags=re.IGNORECASE)
    if not match:
        return None

    model_number = match.group(1)

    if len(model_number) == 4:
        return int(model_number[0])

    if len(model_number) == 5:
        return int(model_number[:2])

    return None


def _extract_amd_ryzen_generation(processor_name):
    """Extract AMD Ryzen generation from common names like Ryzen 5 2600 or Ryzen 7 3700U."""
    processor_name = str(processor_name)
    match = re.search(r"ryzen\s+[3579]\s+(\d{4})", processor_name, flags=re.IGNORECASE)
    if not match:
        return None

    model_number = match.group(1)
    return int(model_number[0])


def is_cpu_supported(processor_name):
    """
    Best-effort CPU support check based on processor name.

    This is intentionally conservative and should eventually be replaced or supplemented
    by Microsoft's official supported processor lists.
    """
    processor_name = str(processor_name or "").strip()

    if not processor_name or processor_name.lower() in ["unknown", "nan", "none"]:
        return False, "Processor name missing"

    lowered = processor_name.lower()

    if "intel" in lowered and "core" in lowered:
        generation = _extract_intel_core_generation(processor_name)
        if generation is None:
            return False, "Unable to determine Intel Core generation"
        return generation >= SUPPORTED_INTEL_CORE_MIN_GENERATION, f"Detected Intel Core generation {generation}"

    if "amd" in lowered and "ryzen" in lowered:
        generation = _extract_amd_ryzen_generation(processor_name)
        if generation is None:
            return False, "Unable to determine AMD Ryzen generation"
        return generation >= SUPPORTED_AMD_RYZEN_MIN_GENERATION, f"Detected AMD Ryzen generation {generation}"

    if "intel" in lowered and any(token in lowered for token in ["celeron", "pentium", "xeon"]):
        return False, "Processor family requires manual validation"

    return False, "Processor family not recognized"
