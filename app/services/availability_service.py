"""
Instructor Availability Matching Service

Checks if instructor's availability windows match contract periods.
Returns advisory information - does NOT block offers.
"""

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from ..models.instructor_assignment import InstructorAvailabilityWindow
from ..schemas.instructor_management import AvailabilityCheckResult


def parse_date_to_quarters(start_date: datetime, end_date: datetime) -> List[str]:
    """
    Parse contract dates to quarter codes (Q1-Q4).

    Q1: Jan-Mar
    Q2: Apr-Jun
    Q3: Jul-Sep
    Q4: Oct-Dec
    """
    quarters = set()

    # Determine quarters covered by the contract period
    start_month = start_date.month
    end_month = end_date.month
    start_year = start_date.year
    end_year = end_date.year

    # Map months to quarters
    month_to_quarter = {
        1: 'Q1', 2: 'Q1', 3: 'Q1',
        4: 'Q2', 5: 'Q2', 6: 'Q2',
        7: 'Q3', 8: 'Q3', 9: 'Q3',
        10: 'Q4', 11: 'Q4', 12: 'Q4'
    }

    # For same year contract
    if start_year == end_year:
        for month in range(start_month, end_month + 1):
            quarters.add(month_to_quarter[month])
    else:
        # Multi-year contract - cover all quarters from start to end
        # Start year: from start_month to December
        for month in range(start_month, 13):
            quarters.add(month_to_quarter[month])

        # End year: from January to end_month
        for month in range(1, end_month + 1):
            quarters.add(month_to_quarter[month])

        # If contract spans more than 2 years, include all quarters for middle years
        for year in range(start_year + 1, end_year):
            quarters.update(['Q1', 'Q2', 'Q3', 'Q4'])

    return sorted(list(quarters))


def calculate_quarter_overlap(
    instructor_quarters: List[str],
    contract_quarters: List[str]
) -> int:
    """
    Calculate percentage overlap between instructor availability and contract coverage.

    Returns:
        int: Percentage match (0-100)
    """
    if not contract_quarters:
        return 100  # No contract coverage needed

    if not instructor_quarters:
        return 0  # Instructor has no availability

    instructor_set = set(instructor_quarters)
    contract_set = set(contract_quarters)

    overlap = instructor_set.intersection(contract_set)
    match_score = int((len(overlap) / len(contract_set)) * 100)

    return match_score


def generate_availability_warnings(
    instructor_quarters: List[str],
    contract_quarters: List[str],
    match_score: int
) -> List[str]:
    """
    Generate human-readable warnings about availability mismatches.
    """
    warnings = []

    if match_score == 0:
        warnings.append(
            f"⚠️ CRITICAL: Instructor has NO availability for contract period. "
            f"Instructor available: {', '.join(instructor_quarters) if instructor_quarters else 'NONE'}. "
            f"Contract covers: {', '.join(contract_quarters)}."
        )
    elif match_score < 50:
        instructor_set = set(instructor_quarters)
        contract_set = set(contract_quarters)
        missing = contract_set - instructor_set
        warnings.append(
            f"⚠️ LOW MATCH ({match_score}%): Instructor missing availability for {', '.join(sorted(missing))}. "
            f"Instructor will need to update availability or discuss with admin."
        )
    elif match_score < 100:
        instructor_set = set(instructor_quarters)
        contract_set = set(contract_quarters)
        missing = contract_set - instructor_set
        warnings.append(
            f"⚠️ PARTIAL MATCH ({match_score}%): Contract extends to {', '.join(sorted(missing))}, "
            f"but instructor only available for {', '.join(sorted(instructor_quarters))}."
        )
    # No warning if 100% match

    return warnings


def check_availability_match(
    instructor_id: int,
    year: int,
    contract_start: datetime,
    contract_end: datetime,
    db: Session
) -> AvailabilityCheckResult:
    """
    Check if instructor's availability matches contract period.

    Returns advisory information - does NOT block offers.

    Args:
        instructor_id: ID of instructor
        year: Primary year of contract (e.g., 2026)
        contract_start: Contract start date
        contract_end: Contract end date
        db: Database session

    Returns:
        AvailabilityCheckResult with match score and warnings
    """
    # Fetch instructor's availability windows for the year
    availability_windows = db.query(InstructorAvailabilityWindow).filter(
        InstructorAvailabilityWindow.instructor_id == instructor_id,
        InstructorAvailabilityWindow.year == year,
        InstructorAvailabilityWindow.is_available == True
    ).all()

    # Extract available quarters
    instructor_quarters = []
    for window in availability_windows:
        period = window.time_period
        if period in ['Q1', 'Q2', 'Q3', 'Q4']:
            instructor_quarters.append(period)

    # Parse contract dates to quarters
    contract_quarters = parse_date_to_quarters(contract_start, contract_end)

    # Calculate match score
    match_score = calculate_quarter_overlap(instructor_quarters, contract_quarters)

    # Generate warnings
    warnings = generate_availability_warnings(
        instructor_quarters,
        contract_quarters,
        match_score
    )

    return AvailabilityCheckResult(
        match_score=match_score,
        warnings=warnings,
        instructor_availability=instructor_quarters,
        contract_coverage=contract_quarters
    )


def check_instructor_has_active_master_position(
    instructor_id: int,
    db: Session
) -> bool:
    """
    Check if instructor already has an active master position at ANY location.

    Business rule: Instructor can only be master at ONE location at a time.

    Args:
        instructor_id: ID of instructor
        db: Database session

    Returns:
        True if instructor has active master position, False otherwise
    """
    from ..models.instructor_assignment import LocationMasterInstructor, MasterOfferStatus

    # Check for:
    # 1. Legacy active contracts (offer_status = NULL, is_active = True)
    # 2. New accepted contracts (offer_status = ACCEPTED, is_active = True)
    active_master = db.query(LocationMasterInstructor).filter(
        LocationMasterInstructor.instructor_id == instructor_id,
        LocationMasterInstructor.is_active == True,
        (
            (LocationMasterInstructor.offer_status == None) |  # Legacy
            (LocationMasterInstructor.offer_status == MasterOfferStatus.ACCEPTED)  # New accepted
        )
    ).first()

    return active_master is not None


def get_instructor_active_master_location(
    instructor_id: int,
    db: Session
) -> str:
    """
    Get location name where instructor is currently active master.

    Returns:
        Location name or None if not a master anywhere
    """
    from ..models.instructor_assignment import LocationMasterInstructor, MasterOfferStatus
    from ..models.location import Location

    active_master = db.query(LocationMasterInstructor).join(
        Location, LocationMasterInstructor.location_id == Location.id
    ).filter(
        LocationMasterInstructor.instructor_id == instructor_id,
        LocationMasterInstructor.is_active == True,
        (
            (LocationMasterInstructor.offer_status == None) |
            (LocationMasterInstructor.offer_status == MasterOfferStatus.ACCEPTED)
        )
    ).first()

    if active_master:
        return active_master.location.name
    return None
