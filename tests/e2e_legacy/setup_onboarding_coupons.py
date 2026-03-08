"""
Setup script for onboarding E2E tests - Creates 3 BONUS_CREDITS coupons via API

Run this before running onboarding Playwright tests to ensure coupons exist.

Usage:
    python tests/e2e/setup_onboarding_coupons.py
"""

import sys
sys.path.insert(0, "tests/e2e")

from reward_policy_fixtures import create_admin_token
import psycopg2
import requests


API_BASE_URL = "http://localhost:8000"


def reset_user_credits_and_coupon_usage():
    """Reset test users to 50 credits, delete licenses, and reset coupon usage"""
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
    cur = conn.cursor()

    # Reset user credits to 50
    test_emails = [
        "pwt.k1sqx1@f1stteam.hu",
        "pwt.p3t1k3@f1stteam.hu",
        "pwt.V4lv3rd3jr@f1stteam.hu"
    ]

    for email in test_emails:
        # Delete user licenses (so they start fresh)
        cur.execute(
            "DELETE FROM user_licenses WHERE user_id = (SELECT id FROM users WHERE email = %s)",
            (email,)
        )
        # Reset credit balance to 50
        cur.execute(
            "UPDATE users SET credit_balance = 50, specialization = NULL, onboarding_completed = FALSE WHERE email = %s",
            (email,)
        )

    # Reset coupon usage
    coupon_codes = [
        "E2E-BONUS-50-USER1",
        "E2E-BONUS-50-USER2",
        "E2E-BONUS-50-USER3"
    ]

    for code in coupon_codes:
        # Reset current_uses to 0
        cur.execute(
            "UPDATE coupons SET current_uses = 0 WHERE code = %s",
            (code,)
        )
        # Delete usage records
        cur.execute(
            "DELETE FROM coupon_usages WHERE coupon_id = (SELECT id FROM coupons WHERE code = %s)",
            (code,)
        )

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Reset user credits and coupon usage")


def setup_coupons():
    """Create 3 BONUS_CREDITS coupons for onboarding tests"""

    print("\n" + "="*60)
    print("🎫 ONBOARDING COUPON SETUP")
    print("="*60 + "\n")

    # Get admin token
    print("1️⃣  Getting admin token...")
    admin_token = create_admin_token()
    print("   ✅ Admin authenticated\n")

    # Coupon specifications
    coupons_to_create = [
        {"code": "E2E-BONUS-50-USER1", "credits": 50, "max_uses": 1},
        {"code": "E2E-BONUS-50-USER2", "credits": 50, "max_uses": 1},
        {"code": "E2E-BONUS-50-USER3", "credits": 50, "max_uses": 1}
    ]

    print("2️⃣  Creating BONUS_CREDITS coupons...")

    for coupon_spec in coupons_to_create:
        try:
            # Use new coupon API format
            response = requests.post(
                f"{API_BASE_URL}/api/v1/admin/coupons",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "code": coupon_spec["code"],
                    "type": "BONUS_CREDITS",  # ✅ New type
                    "discount_value": coupon_spec["credits"],
                    "description": f"E2E onboarding test: +{coupon_spec['credits']} bonus credits",
                    "is_active": True,
                    "expires_at": None,
                    "max_uses": coupon_spec["max_uses"]
                }
            )

            if response.status_code == 201:
                coupon = response.json()
                print(f"   ✅ Created: {coupon['code']} (+{coupon_spec['credits']} credits, max_uses={coupon_spec['max_uses']})")
            elif response.status_code == 400 and "already exists" in response.text:
                print(f"   ⚠️  Already exists: {coupon_spec['code']}")
            else:
                print(f"   ❌ Failed to create {coupon_spec['code']}: {response.status_code} - {response.text}")
                response.raise_for_status()
        except Exception as e:
            if "already exists" in str(e):
                print(f"   ⚠️  Already exists: {coupon_spec['code']}")
            else:
                print(f"   ❌ Failed to create {coupon_spec['code']}: {e}")
                raise

    print("\n3️⃣  Resetting test users and coupon usage...")
    reset_user_credits_and_coupon_usage()

    print("\n" + "="*60)
    print("✅ SETUP COMPLETE - Ready for onboarding tests")
    print("="*60 + "\n")

    print("📋 Test users prepared:")
    print("   - pwt.k1sqx1@f1stteam.hu (50 credits)")
    print("   - pwt.p3t1k3@f1stteam.hu (50 credits)")
    print("   - pwt.V4lv3rd3jr@f1stteam.hu (50 credits)")
    print("\n📋 Coupons ready:")
    print("   - E2E-BONUS-50-USER1 (+50 credits, unused)")
    print("   - E2E-BONUS-50-USER2 (+50 credits, unused)")
    print("   - E2E-BONUS-50-USER3 (+50 credits, unused)")
    print()


if __name__ == "__main__":
    setup_coupons()
