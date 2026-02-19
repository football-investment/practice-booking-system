"""
Gap Detection Helpers
=====================

Functions for detecting gaps in semester coverage across different age groups.

- Extract existing periods (months, quarters, annual)
- Calculate coverage statistics
- Identify missing periods
"""


def extract_existing_months(semesters: list, spec_type: str, year: int) -> list:
    """
    Extract which months exist for PRE in given year

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_PRE"
        year: Year to check

    Returns:
        List of existing month codes, e.g., ["M01", "M02", "M03", ..., "M08"]
    """
    existing = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_PRE_M03"
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    month_code = parts[-1]  # Extract "M03"
                    if month_code.startswith("M") and len(month_code) == 3:
                        existing.append(month_code)
    return sorted(existing)


def extract_existing_quarters(semesters: list, spec_type: str, year: int) -> list:
    """
    Extract which quarters exist for YOUTH in given year

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_YOUTH"
        year: Year to check

    Returns:
        List of existing quarter codes, e.g., ["Q1", "Q2"]
    """
    existing = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_YOUTH_Q2"
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    quarter_code = parts[-1]  # Extract "Q2"
                    if quarter_code.startswith("Q") and len(quarter_code) == 2:
                        existing.append(quarter_code)
    return sorted(existing)


def check_annual_exists(semesters: list, spec_type: str, year: int) -> bool:
    """
    Check if annual season exists for AMATEUR or PRO

    Args:
        semesters: List of all semesters
        spec_type: "LFA_PLAYER_AMATEUR" or "LFA_PLAYER_PRO"
        year: Year to check

    Returns:
        True if annual season exists, False otherwise
    """
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            # Code format: "2025/LFA_PLAYER_AMATEUR_Season" or "2025/LFA_PLAYER_PRO_Season"
            if code.startswith(f"{year}/"):
                return True
    return False


def get_existing_semester_ids(semesters: list, spec_type: str, year: int, codes: list) -> list:
    """
    Get IDs of existing semesters matching the given codes

    Args:
        semesters: List of all semesters
        spec_type: Specialization type
        year: Year to check
        codes: List of codes to match (e.g., ["M01", "M02"])

    Returns:
        List of semester IDs
    """
    ids = []
    for sem in semesters:
        if sem.get("specialization_type") == spec_type:
            code = sem.get("code", "")
            if code.startswith(f"{year}/"):
                parts = code.split("_")
                if parts:
                    period_code = parts[-1]
                    if period_code in codes:
                        ids.append(sem.get("id"))
    return ids


def calculate_coverage(semesters: list, age_group: str, year: int) -> dict:
    """
    Calculate coverage for a specific age group and year

    Args:
        semesters: List of all semesters
        age_group: "PRE", "YOUTH", "AMATEUR", or "PRO"
        year: Year to check

    Returns:
        {
            "exists": 8,      # Number of periods that exist
            "total": 12,      # Total periods expected
            "missing": 4,     # Number missing
            "missing_codes": ["M09", "M10", "M11", "M12"],  # Which ones missing
            "existing_codes": ["M01", "M02", ...],  # Which ones exist
            "existing_ids": [1, 2, 3, ...],  # IDs of existing periods
            "percentage": 66.67  # Coverage percentage
        }
    """
    spec_type = f"LFA_PLAYER_{age_group}"

    # PRE: Check for M01-M12 (12 monthly periods)
    if age_group == "PRE":
        total = 12
        existing_codes = extract_existing_months(semesters, spec_type, year)
        all_codes = [f"M{i:02d}" for i in range(1, 13)]
        missing_codes = [code for code in all_codes if code not in existing_codes]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, existing_codes)

    # YOUTH: Check for Q1-Q4 (4 quarterly periods)
    elif age_group == "YOUTH":
        total = 4
        existing_codes = extract_existing_quarters(semesters, spec_type, year)
        all_codes = [f"Q{i}" for i in range(1, 5)]
        missing_codes = [code for code in all_codes if code not in existing_codes]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, existing_codes)

    # AMATEUR/PRO: Check for annual season (1 period)
    elif age_group in ["AMATEUR", "PRO"]:
        total = 1
        exists = check_annual_exists(semesters, spec_type, year)
        existing_codes = ["Season"] if exists else []
        missing_codes = [] if exists else ["Season"]
        existing_ids = get_existing_semester_ids(semesters, spec_type, year, ["Season"]) if exists else []

    else:
        return {
            "exists": 0,
            "total": 0,
            "missing": 0,
            "missing_codes": [],
            "existing_codes": [],
            "existing_ids": [],
            "percentage": 0
        }

    exists_count = len(existing_codes)
    percentage = (exists_count / total * 100) if total > 0 else 0

    return {
        "exists": exists_count,
        "total": total,
        "missing": len(missing_codes),
        "missing_codes": missing_codes,
        "existing_codes": existing_codes,
        "existing_ids": existing_ids,
        "percentage": round(percentage, 2)
    }
