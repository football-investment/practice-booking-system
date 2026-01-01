"""
Test EnrollmentResponse Pydantic validation
To debug the 500 error during tournament enrollment
"""
from app.schemas.tournament import EnrollmentResponse, EnrollmentConflict

# Simulate the exact response data structure from enroll.py
test_response_data = {
    "success": True,
    "enrollment": {
        "id": 999,
        "user_id": 2,
        "semester_id": 215,
        "user_license_id": 1,
        "age_category": "AMATEUR",
        "request_status": "APPROVED",
        "payment_verified": True,
        "is_active": True,
        "enrolled_at": "2026-01-01T10:00:00",
        "approved_at": "2026-01-01T10:00:00"
    },
    "tournament": {
        "id": 215,
        "code": "TOURN-20260101",
        "name": "1st 🏐 GānFootvolley battle",
        "start_date": "2026-01-01",
        "end_date": "2026-01-01",
        "age_group": "AMATEUR",
        "enrollment_cost": 1
    },
    "conflicts": [],
    "warnings": [],
    "credits_remaining": 499
}

try:
    # Try to validate with Pydantic
    validated = EnrollmentResponse(**test_response_data)
    print("✅ VALIDATION SUCCESS!")
    print(f"Response data: {validated.model_dump_json(indent=2)}")
except Exception as e:
    print(f"❌ VALIDATION FAILED!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")

    import traceback
    print("\n🔍 FULL TRACEBACK:")
    traceback.print_exc()
