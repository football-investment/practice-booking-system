#!/usr/bin/env python3
"""
Test script for Sandbox Phase 1 Read-Only APIs
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def get_admin_token():
    """Get admin authentication token"""
    print("1️⃣  Authenticating as admin...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@lfa.com", "password": "admin123"}
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    print("✅ Token obtained\n")
    return token

def test_get_users(token):
    """Test GET /sandbox/users"""
    print("2️⃣  Testing GET /sandbox/users (limit=3)...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/sandbox/users?limit=3",
        headers=headers
    )
    response.raise_for_status()
    users = response.json()
    print(f"✅ Returned {len(users)} users")
    print("📄 Sample response:")
    print(json.dumps(users[:1], indent=2))
    print()
    return users

def test_get_instructors(token):
    """Test GET /sandbox/instructors"""
    print("3️⃣  Testing GET /sandbox/instructors (limit=2)...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/sandbox/instructors?limit=2",
        headers=headers
    )
    response.raise_for_status()
    instructors = response.json()
    print(f"✅ Returned {len(instructors)} instructors")
    print("📄 Sample response:")
    print(json.dumps(instructors[:1], indent=2))
    print()
    return instructors

def test_get_user_skills(token, user_id=4):
    """Test GET /sandbox/users/{id}/skills"""
    print(f"4️⃣  Testing GET /sandbox/users/{user_id}/skills...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/sandbox/users/{user_id}/skills",
        headers=headers
    )
    response.raise_for_status()
    skill_profile = response.json()
    print(f"✅ Skill profile retrieved for user {skill_profile['user_id']}")
    print("📄 Sample response (user info + skill keys):")
    print(json.dumps({
        "user_id": skill_profile["user_id"],
        "email": skill_profile["email"],
        "name": skill_profile["name"],
        "skills": list(skill_profile["skills"].keys()) if skill_profile["skills"] else []
    }, indent=2))
    print()
    return skill_profile

def main():
    print("🧪 Testing Sandbox Phase 1: Read-Only APIs")
    print("=" * 50)
    print()

    try:
        # Get admin token
        token = get_admin_token()

        # Test all three endpoints
        users = test_get_users(token)
        instructors = test_get_instructors(token)
        skill_profile = test_get_user_skills(token)

        # Summary
        print("=" * 50)
        print("✅ All Phase 1 endpoints tested successfully!")
        print()
        print("Summary:")
        print(f"- GET /sandbox/users: {len(users)} users returned")
        print(f"- GET /sandbox/instructors: {len(instructors)} instructors returned")
        print(f"- GET /sandbox/users/4/skills: Full skill profile retrieved")
        print()

        # Additional validation
        print("🔍 Validation:")
        if users and "skill_preview" in users[0]:
            print("  ✅ Users endpoint includes skill_preview")
        if instructors and "permissions" in instructors[0]:
            print("  ✅ Instructors endpoint includes permissions")
        if skill_profile and "skills" in skill_profile:
            print("  ✅ User skills endpoint includes full skill profile")

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
