"""
Final re-distribution for TOURN-20260125-001 and TOURN-20260125-002
with updated reward configs matching admin guide examples.
"""
import requests
from config import API_BASE_URL

# Admin token (replace with actual admin token)
ADMIN_TOKEN = input("Enter admin token: ").strip()

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# Tournament IDs
tournaments = [
    {"id": 18, "code": "TOURN-20260125-001", "name": "NIKE Speed Test"},
    {"id": 19, "code": "TOURN-20260125-002", "name": "Plank Competition"}
]

print("=" * 80)
print("FINAL REWARD RE-DISTRIBUTION")
print("=" * 80)

for tournament in tournaments:
    print(f"\n🏆 {tournament['name']} ({tournament['code']})")
    print("-" * 80)

    # Call re-distribution endpoint
    url = f"{API_BASE_URL}/api/v1/tournaments/{tournament['id']}/rewards-v2/redistribute"

    try:
        response = requests.post(url, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Re-distribution successful!")
            print(f"   - Participants processed: {result.get('participants_processed', 'N/A')}")
            print(f"   - Total credits: {result.get('total_credits_awarded', 'N/A')}")
            print(f"   - Total XP: {result.get('total_xp_awarded', 'N/A')}")

            # Show skill breakdown
            if 'skill_breakdown' in result:
                print(f"\n   📊 Skill Points Breakdown:")
                for skill, points in result['skill_breakdown'].items():
                    print(f"      - {skill}: {points:.1f} points")
        else:
            print(f"❌ Re-distribution failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 80)
print("✅ Re-distribution complete!")
print("=" * 80)
