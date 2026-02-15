#!/usr/bin/env python3
"""
Verify onboarding skills in database after test run

Usage:
    python verify_onboarding_skills.py <user_email>

Example:
    python verify_onboarding_skills.py pwt.k1sqx1@f1stteam.hu
"""

import sys
import psycopg2
import json
from app.skills_config import get_all_skill_keys

def verify_onboarding_skills(user_email: str):
    """Verify that user has all 29 skills saved after onboarding"""

    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Get user's LFA_FOOTBALL_PLAYER license
    cur.execute("""
        SELECT ul.id, ul.football_skills, ul.onboarding_completed, ul.onboarding_completed_at
        FROM user_licenses ul
        JOIN users u ON ul.user_id = u.id
        WHERE u.email = %s
        AND ul.specialization_type = 'LFA_FOOTBALL_PLAYER'
        AND ul.is_active = true
        ORDER BY ul.created_at DESC
        LIMIT 1
    """, (user_email,))

    result = cur.fetchone()

    if not result:
        print(f"❌ No active LFA_FOOTBALL_PLAYER license found for {user_email}")
        cur.close()
        conn.close()
        return False

    license_id, football_skills, onboarding_completed, onboarding_completed_at = result

    print(f"\n{'='*80}")
    print(f"🔍 ONBOARDING SKILLS VERIFICATION")
    print(f"{'='*80}")
    print(f"User: {user_email}")
    print(f"License ID: {license_id}")
    print(f"Onboarding Completed: {onboarding_completed}")
    print(f"Completed At: {onboarding_completed_at}")
    print(f"{'='*80}\n")

    if not onboarding_completed:
        print(f"⚠️  WARNING: Onboarding not marked as completed!")

    if not football_skills:
        print(f"❌ FAILED: No football_skills data found!")
        cur.close()
        conn.close()
        return False

    # Get expected skills
    expected_skills = set(get_all_skill_keys())
    actual_skills = set(football_skills.keys())

    print(f"📊 SKILL COUNT SUMMARY")
    print(f"   Expected skills: {len(expected_skills)}")
    print(f"   Actual skills:   {len(actual_skills)}")
    print()

    # Check for missing skills
    missing_skills = expected_skills - actual_skills
    if missing_skills:
        print(f"❌ MISSING SKILLS ({len(missing_skills)}):")
        for skill in sorted(missing_skills):
            print(f"   - {skill}")
        print()

    # Check for extra skills
    extra_skills = actual_skills - expected_skills
    if extra_skills:
        print(f"⚠️  EXTRA SKILLS ({len(extra_skills)}):")
        for skill in sorted(extra_skills):
            print(f"   - {skill}")
        print()

    # Show skill values
    print(f"📋 SKILL VALUES (showing first 10 and last 10):")
    print()

    sorted_skills = sorted(actual_skills)

    # First 10
    for i, skill_key in enumerate(sorted_skills[:10]):
        skill_data = football_skills[skill_key]
        if isinstance(skill_data, dict):
            current = skill_data.get('current_level', 'N/A')
            baseline = skill_data.get('baseline', 'N/A')
            print(f"   {i+1:2d}. {skill_key:25s} current={current:6.1f}, baseline={baseline:6.1f}")
        else:
            print(f"   {i+1:2d}. {skill_key:25s} value={skill_data}")

    if len(sorted_skills) > 20:
        print(f"   ... ({len(sorted_skills) - 20} more skills) ...")

    # Last 10
    for i, skill_key in enumerate(sorted_skills[-10:]):
        skill_data = football_skills[skill_key]
        idx = len(sorted_skills) - 10 + i + 1
        if isinstance(skill_data, dict):
            current = skill_data.get('current_level', 'N/A')
            baseline = skill_data.get('baseline', 'N/A')
            print(f"   {idx:2d}. {skill_key:25s} current={current:6.1f}, baseline={baseline:6.1f}")
        else:
            print(f"   {idx:2d}. {skill_key:25s} value={skill_data}")

    print()

    # Calculate statistics
    values = []
    for skill_key in actual_skills:
        skill_data = football_skills[skill_key]
        if isinstance(skill_data, dict):
            values.append(skill_data.get('current_level', 0))
        elif isinstance(skill_data, (int, float)):
            values.append(skill_data)

    if values:
        avg = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)

        print(f"📈 STATISTICS")
        print(f"   Average: {avg:.1f}")
        print(f"   Min:     {min_val:.1f}")
        print(f"   Max:     {max_val:.1f}")
        print()

    # Final verdict
    if len(actual_skills) == len(expected_skills) and not missing_skills:
        print(f"✅ VERIFICATION PASSED: All {len(expected_skills)} skills present!")
        success = True
    else:
        print(f"❌ VERIFICATION FAILED: Expected {len(expected_skills)} skills, found {len(actual_skills)}")
        success = False

    print(f"{'='*80}\n")

    cur.close()
    conn.close()

    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_onboarding_skills.py <user_email>")
        print("Example: python verify_onboarding_skills.py pwt.k1sqx1@f1stteam.hu")
        sys.exit(1)

    user_email = sys.argv[1]
    success = verify_onboarding_skills(user_email)

    sys.exit(0 if success else 1)
