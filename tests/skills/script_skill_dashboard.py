"""
Test script for skill profile dashboard
Tests the entire flow: Authentication -> Skill Profile API -> Data validation
"""
import requests
import sys
from pprint import pprint

API_BASE_URL = "http://localhost:8000"

def test_skill_profile():
    print("=" * 60)
    print("SKILL PROFILE DASHBOARD TEST")
    print("=" * 60)

    # Step 1: Login and get Bearer token
    print("\n1. Logging in as junior.intern@lfa.com...")
    login_data = {
        "email": "junior.intern@lfa.com",
        "password": "testpassword123"
    }

    login_response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json=login_data
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False

    login_result = login_response.json()
    access_token = login_result.get("access_token")

    if not access_token:
        print(f"❌ No access token in response")
        return False

    print(f"✅ Login successful: {login_result.get('email')}")
    print(f"✅ Access token obtained: {access_token[:20]}...")

    # Step 2: Fetch skill profile
    print("\n2. Fetching skill profile...")
    profile_response = requests.get(
        f"{API_BASE_URL}/api/v1/progression/skill-profile",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if profile_response.status_code != 200:
        print(f"❌ Failed to fetch skill profile: {profile_response.status_code}")
        print(f"Response: {profile_response.text}")
        return False

    profile_data = profile_response.json()
    print(f"✅ Skill profile fetched successfully")

    # Step 3: Validate data structure
    print("\n3. Validating skill profile data...")

    # Check for required fields
    required_fields = ["skills", "average_level", "total_tournaments", "total_assessments"]
    for field in required_fields:
        if field not in profile_data:
            print(f"❌ Missing required field: {field}")
            return False
        print(f"  ✓ {field}: {type(profile_data[field]).__name__}")

    # Display skill data
    skills = profile_data.get("skills", {})
    print(f"\n4. Skill Profile Summary:")
    print(f"  • Total Skills: {len(skills)}")
    print(f"  • Average Level: {profile_data.get('average_level', 0):.1f}")
    print(f"  • Total Tournaments: {profile_data.get('total_tournaments', 0)}")
    print(f"  • Total Assessments: {profile_data.get('total_assessments', 0)}")

    if skills:
        print(f"\n5. Individual Skills:")
        for skill_name, skill_data in sorted(skills.items()):
            current_level = skill_data.get("current_level", 0.0)
            baseline = skill_data.get("baseline", 0.0)
            total_delta = skill_data.get("total_delta", 0.0)
            tier = skill_data.get("tier", "UNKNOWN")
            tier_emoji = skill_data.get("tier_emoji", "")

            print(f"\n  {tier_emoji} {skill_name.replace('_', ' ').title()}")
            print(f"     Current: {current_level:.1f} | Baseline: {baseline:.1f} | Delta: +{total_delta:.1f}")
            print(f"     Tier: {tier}")

            # Show breakdown if available
            tournament_delta = skill_data.get("tournament_delta", 0.0)
            assessment_delta = skill_data.get("assessment_delta", 0.0)
            if tournament_delta > 0 or assessment_delta > 0:
                print(f"     Tournament: +{tournament_delta:.1f} | Assessment: +{assessment_delta:.1f}")
    else:
        print("\n  ⚠️  No skills found (user may not have completed onboarding)")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_skill_profile()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
