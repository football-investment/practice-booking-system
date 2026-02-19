"""
Quick script to find and delete the INTERNSHIP semester from database
"""
import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"

def find_and_delete_internship_semester():
    """Find and delete the INTERNSHIP semester"""

    # Get all semesters
    print("🔍 Searching for INTERNSHIP semester...")
    response = requests.get(f"{BASE_URL}/semesters/")

    if response.status_code != 200:
        print(f"❌ Error fetching semesters: {response.status_code}")
        return False

    semesters = response.json()

    # Find INTERNSHIP semester
    internship_sem = None
    for sem in semesters:
        if "INTERNSHIP" in sem.get("code", ""):
            internship_sem = sem
            break

    if not internship_sem:
        print("ℹ️  No INTERNSHIP semester found in database")
        return False

    # Display found semester
    print(f"\n✅ Found semester:")
    print(f"   ID: {internship_sem['id']}")
    print(f"   Code: {internship_sem['code']}")
    print(f"   Name: {internship_sem['name']}")
    print(f"   Start: {internship_sem['start_date']}")
    print(f"   End: {internship_sem['end_date']}")

    # Delete semester
    print(f"\n🗑️  Deleting semester ID {internship_sem['id']}...")

    # Note: We need admin auth - let me check if endpoint requires it
    delete_response = requests.delete(f"{BASE_URL}/semesters/{internship_sem['id']}")

    if delete_response.status_code == 200:
        print("✅ Semester deleted successfully!")
        return True
    else:
        print(f"❌ Error deleting semester: {delete_response.status_code}")
        print(f"   Response: {delete_response.text}")
        return False

if __name__ == "__main__":
    success = find_and_delete_internship_semester()
    sys.exit(0 if success else 1)
