# Onboarding Skill Logic Analysis

**Date:** 2026-02-08
**Status:** ⚠️ **CRITICAL ISSUE IDENTIFIED**
**Severity:** HIGH (Test does NOT match backend requirements)

---

## Executive Summary

**PROBLEM IDENTIFIED:** The onboarding test currently assigns **RANDOM skill values (1-10)** for **6 skills**, but the backend **expects ALL 29 skills (0-100 scale)**.

**Impact:**
- ✅ Test still PASSES (backend doesn't fail on missing skills)
- ⚠️ **Test data quality is POOR** (only 6/29 skills set, rest default to 50.0)
- ⚠️ **Data inconsistency** between test and production onboarding
- ⚠️ **Regression risk** if backend validation tightens

---

## Backend Requirements

### From `app/api/web_routes/onboarding.py:249-267`

**Backend expects:**
```python
skills = body.get("skills", {})  # NEW: All 36 skills, 0-100 scale
print(f"📥 Onboarding submit for {user.email}: {len(skills)} skills received")

# Validate skills (must have all 36 skills)
from app.skills_config import get_all_skill_keys
expected_skills = set(get_all_skill_keys())
received_skills = set(skills.keys())

if received_skills != expected_skills:
    missing = expected_skills - received_skills
    extra = received_skills - expected_skills
    print(f"⚠️ Skill mismatch: missing={missing}, extra={extra}")
    # Don't fail, just log - allow submission with whatever skills we have
```

**Key Observations:**
1. Backend LOGS skill mismatch but **DOES NOT FAIL** submission
2. Backend is **lenient** (allows partial skill data)
3. Comment says "All 36 skills" but code says 29 (`get_all_skill_keys()`)

### From `app/skills_config.py`

**Total Skills: 29 skills across 4 categories**

```python
SKILL_CATEGORIES = [
    {
        "key": "outfield",
        "name_en": "Outfield",
        "skills": [
            "ball_control", "dribbling", "finishing", "shot_power",
            "long_shots", "volleys", "crossing", "passing",
            "heading", "tackle", "marking"
        ]  # 11 skills
    },
    {
        "key": "set_pieces",
        "name_en": "Set Pieces",
        "skills": ["free_kicks", "corners", "penalties"]  # 3 skills
    },
    {
        "key": "mental",
        "name_en": "Mental",
        "skills": [
            "positioning_off", "positioning_def", "vision",
            "aggression", "reactions", "composure",
            "consistency", "tactical_awareness"
        ]  # 8 skills
    },
    {
        "key": "physical",
        "name_en": "Physical Fitness",
        "skills": [
            "acceleration", "sprint_speed", "agility",
            "jumping", "strength", "stamina", "balance"
        ]  # 7 skills
    }
]

# TOTAL: 11 + 3 + 8 + 7 = 29 skills
```

**Value Range:** 0-100 scale

**Backend Storage Format:**
```python
football_skills[skill_key] = {
    "current_level": float(baseline_value),   # 0-100
    "baseline": float(baseline_value),        # 0-100
    "total_delta": 0.0,
    "tournament_delta": 0.0,
    "assessment_delta": 0.0,
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "assessment_count": 0,
    "tournament_count": 0
}
```

---

## Current Test Implementation

### From `tests/e2e_frontend/user_lifecycle/onboarding/test_onboarding_with_coupon.py:187-222`

**What the test ACTUALLY does:**

```python
# Step 2: Skills Assessment (RANDOM VALUES)
print(f"  ⚡ Step 2: Skills Assessment")
page.wait_for_timeout(2000)

sliders = page.locator('div[role="slider"]')
slider_count = sliders.count()
print(f"     Found {slider_count} sliders")

# PROBLEM: Only 6 skill names, NOT 29!
skill_names = ["Heading", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]

for i in range(min(slider_count, len(skill_names))):
    slider = sliders.nth(i)
    random_value = random.randint(1, 10)  # ❌ RANDOM 1-10, NOT 0-100!
    current_value = slider.get_attribute("aria-valuenow")
    skill_name = skill_names[i]

    # Use arrow keys to set slider value
    current = int(current_value) if current_value else 5
    diff = random_value - current

    if diff > 0:
        for _ in range(diff):
            page.keyboard.press("ArrowRight")
    elif diff < 0:
        for _ in range(abs(diff)):
            page.keyboard.press("ArrowLeft")

    print(f"       {skill_name}: {random_value}/10")
```

**Issues:**

1. ❌ **Wrong skill count**: 6 skills vs 29 required
2. ❌ **Wrong value range**: 1-10 vs 0-100 required
3. ❌ **Random values**: Not deterministic for test reproducibility
4. ❌ **No test data source**: Should use JSON fixtures
5. ⚠️ **Lenient backend**: Test still passes (backend doesn't reject)

---

## What Actually Happens

### Scenario: User completes onboarding via test

**Step 1: UI sets 6 random sliders (1-10)**
```
Heading: 7/10
Shooting: 3/10
Passing: 9/10
Dribbling: 2/10
Defending: 5/10
Physical: 8/10
```

**Step 2: Streamlit submits to backend**
```python
# Frontend likely sends (GUESSING - need to verify):
{
  "heading": 70,       # 7/10 scaled to 0-100
  "shooting": 30,
  "passing": 90,
  "dribbling": 20,
  "defending": 50,
  "physical": 80
}
```

**Step 3: Backend logs warning**
```
⚠️ Skill mismatch:
  missing={'ball_control', 'finishing', 'shot_power', ... (23 more)},
  extra={}
```

**Step 4: Backend saves partial data**
```python
# In UserLicense.football_skills:
{
  "heading": {"current_level": 70.0, "baseline": 70.0, ...},
  "shooting": {"current_level": 30.0, "baseline": 30.0, ...},
  "passing": {"current_level": 90.0, "baseline": 90.0, ...},
  "dribbling": {"current_level": 20.0, "baseline": 20.0, ...},
  "defending": {"current_level": 50.0, "baseline": 50.0, ...},
  "physical": {"current_level": 80.0, "baseline": 80.0, ...}
  # Missing: 23 other skills!
}
```

**Step 5: Skill progression engine uses DEFAULT_BASELINE (50.0) for missing skills**

From `app/services/skill_progression_service.py:147-164`:
```python
def get_baseline_skills(db: Session, user_id: int) -> Dict[str, float]:
    """
    Get baseline skill values from UserLicense.football_skills (onboarding).

    ⚠️ FALLBACK BEHAVIOR FOR MISSING SKILLS:
        If a skill is NOT found in UserLicense.football_skills,
        it defaults to DEFAULT_BASELINE (50.0).

        This is INTENTIONAL and handles cases where:
        - User completed onboarding with old skill set (before migration to 29 skills)
        - User's onboarding data is incomplete
        - New skills were added to system after user onboarding
    """
    if not license or not license.football_skills:
        # No onboarding data at all → return all skills at DEFAULT_BASELINE
        return {skill_key: DEFAULT_BASELINE for skill_key in get_all_skill_keys()}

    # Return stored skills + fallback to 50.0 for missing
    baseline_skills = {}
    for skill_key in get_all_skill_keys():
        if skill_key in stored_skills:
            baseline_skills[skill_key] = stored_skills[skill_key]["baseline"]
        else:
            baseline_skills[skill_key] = DEFAULT_BASELINE  # ← 50.0
```

**Final Result:**
- 6 skills: random values (e.g., 70, 30, 90, 20, 50, 80)
- 23 skills: **default 50.0** (not actually assessed during onboarding)

---

## Test vs Production Behavior

### Production Onboarding UI (Streamlit)

**ASSUMPTION:** The Streamlit onboarding UI likely:
1. Renders sliders for **ALL 29 skills** (grouped by category)
2. Uses **0-100 scale** with step=1
3. Submits ALL 29 skill values to backend
4. May have default values (e.g., 50) for each slider

**TO VERIFY:** Need to inspect the Streamlit onboarding UI code.

### Test Onboarding Behavior

**CURRENT:**
1. Renders unknown number of sliders (test finds them dynamically)
2. Sets **ONLY first 6 sliders** to random 1-10 values
3. Submits partial data (6 skills)
4. Backend accepts it (no validation failure)

**RISK:** If Streamlit UI changes (adds/removes skills), test may break or submit incorrect data.

---

## Root Cause Analysis

### Why is the test like this?

**Hypothesis 1: Test predates 29-skill system**
- Test was written when system had only 6 skills
- System later migrated to 29 skills
- Test was NOT updated

**Hypothesis 2: Test copied from legacy code**
- Test copied from `tests/playwright/` or `tests/e2e/`
- Legacy code used 6-skill system
- Migration preserved legacy logic

**Hypothesis 3: Intentional simplification**
- Test intentionally sets only 6 skills to speed up execution
- Assumes backend fallback (DEFAULT_BASELINE) is acceptable
- NOT a valid assumption for E2E test (should match production)

### Migration Evidence

From `MIGRATION_COMPLETE_REPORT.md`:
```
tests/playwright/test_complete_onboarding_with_coupon_ui.py
  → tests/e2e_frontend/user_lifecycle/onboarding/test_onboarding_with_coupon.py
```

**Conclusion:** Test was migrated from `tests/playwright/` WITHOUT updating skill logic.

---

## Recommended Fixes

### Option 1: Dynamic Skill Discovery (RECOMMENDED)

**Approach:** Make test discover ALL sliders dynamically and set ALL of them.

**Implementation:**
```python
# Step 2: Skills Assessment (ALL SKILLS, DETERMINISTIC VALUES)
print(f"  ⚡ Step 2: Skills Assessment")
page.wait_for_timeout(2000)

# Get all sliders (should be 29 for 29 skills)
sliders = page.locator('div[role="slider"]')
slider_count = sliders.count()
print(f"     Found {slider_count} sliders (expected 29)")

# Use deterministic values for test reproducibility
# Strategy: Set all skills to 60 (above average baseline)
BASELINE_SKILL_VALUE = 60

for i in range(slider_count):
    try:
        slider = sliders.nth(i)
        target_value = BASELINE_SKILL_VALUE
        current_value = slider.get_attribute("aria-valuenow")

        slider.click()
        page.wait_for_timeout(200)

        # Calculate difference and use arrow keys
        current = int(current_value) if current_value else 50
        diff = target_value - current

        if diff > 0:
            for _ in range(diff):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(50)
        elif diff < 0:
            for _ in range(abs(diff)):
                page.keyboard.press("ArrowLeft")
                page.wait_for_timeout(50)

        print(f"       Skill {i+1}: {target_value}/100")
        page.wait_for_timeout(200)
    except Exception as e:
        print(f"       ❌ Error setting slider {i+1}: {e}")

print(f"     ✅ Set {slider_count} skills to baseline {BASELINE_SKILL_VALUE}/100")
```

**Pros:**
- ✅ Handles any number of skills (29, 36, or future count)
- ✅ Deterministic values (reproducible tests)
- ✅ Matches production behavior (all skills set)
- ✅ Simple implementation (no JSON fixtures needed)

**Cons:**
- ⚠️ Slower execution (sets all sliders vs 6)
- ⚠️ No position-specific skill values (all same baseline)

---

### Option 2: JSON Test Data Fixtures (IDEAL)

**Approach:** Create JSON fixtures with predefined skill values for different test scenarios.

**Implementation:**

1. **Create test data file:** `tests/fixtures/onboarding_skills.json`
```json
{
  "player_balanced": {
    "description": "Balanced player with average skills",
    "position": "MIDFIELDER",
    "skills": {
      "ball_control": 65,
      "dribbling": 60,
      "finishing": 55,
      "shot_power": 50,
      "long_shots": 45,
      "volleys": 50,
      "crossing": 60,
      "passing": 70,
      "heading": 55,
      "tackle": 65,
      "marking": 60,
      "free_kicks": 50,
      "corners": 55,
      "penalties": 60,
      "positioning_off": 65,
      "positioning_def": 60,
      "vision": 70,
      "aggression": 55,
      "reactions": 65,
      "composure": 60,
      "consistency": 65,
      "tactical_awareness": 70,
      "acceleration": 60,
      "sprint_speed": 65,
      "agility": 70,
      "jumping": 55,
      "strength": 60,
      "stamina": 65,
      "balance": 60
    }
  },
  "player_striker": {
    "description": "Striker with high attacking skills",
    "position": "STRIKER",
    "skills": {
      "ball_control": 70,
      "dribbling": 75,
      "finishing": 85,
      "shot_power": 80,
      "long_shots": 70,
      "volleys": 75,
      "crossing": 55,
      "passing": 60,
      "heading": 70,
      "tackle": 40,
      "marking": 35,
      "free_kicks": 60,
      "corners": 45,
      "penalties": 80,
      "positioning_off": 85,
      "positioning_def": 40,
      "vision": 65,
      "aggression": 70,
      "reactions": 75,
      "composure": 70,
      "consistency": 65,
      "tactical_awareness": 60,
      "acceleration": 80,
      "sprint_speed": 85,
      "agility": 75,
      "jumping": 70,
      "strength": 65,
      "stamina": 70,
      "balance": 70
    }
  }
}
```

2. **Update test to load JSON data:**
```python
import json
from pathlib import Path

def load_player_skills(player_type: str = "player_balanced"):
    """Load predefined skill values from JSON fixture"""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "onboarding_skills.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data[player_type]

def user_unlock_and_complete_onboarding(page: Page) -> bool:
    # ... (position selection) ...

    # Step 2: Skills Assessment (FROM JSON FIXTURE)
    print(f"  ⚡ Step 2: Skills Assessment (loading from fixture)")
    player_data = load_player_skills("player_balanced")
    skills = player_data["skills"]

    page.wait_for_timeout(2000)

    # Get all sliders
    sliders = page.locator('div[role="slider"]')
    slider_count = sliders.count()
    print(f"     Found {slider_count} sliders (expected {len(skills)})")

    # Get skill keys in UI order (need to inspect Streamlit code for exact order)
    skill_keys = list(skills.keys())

    for i in range(min(slider_count, len(skill_keys))):
        try:
            slider = sliders.nth(i)
            skill_key = skill_keys[i]
            target_value = skills[skill_key]
            current_value = slider.get_attribute("aria-valuenow")

            slider.click()
            page.wait_for_timeout(200)

            # Set to target value using arrow keys
            current = int(current_value) if current_value else 50
            diff = target_value - current

            if diff > 0:
                for _ in range(diff):
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(50)
            elif diff < 0:
                for _ in range(abs(diff)):
                    page.keyboard.press("ArrowLeft")
                    page.wait_for_timeout(50)

            print(f"       {skill_key}: {target_value}/100")
            page.wait_for_timeout(200)
        except Exception as e:
            print(f"       ❌ Error setting {skill_key}: {e}")

    print(f"     ✅ Set {len(skill_keys)} skills from fixture")
```

**Pros:**
- ✅ **Realistic test data** (position-specific skills)
- ✅ **Deterministic** (reproducible)
- ✅ **Reusable** (can use same fixtures for API tests)
- ✅ **Maintainable** (central place to update skill values)
- ✅ **Multiple scenarios** (balanced, striker, defender, etc.)

**Cons:**
- ⚠️ Requires mapping UI slider order to skill keys (fragile if UI changes)
- ⚠️ More setup overhead (create/maintain JSON files)
- ⚠️ Slower execution (sets all 29 sliders)

---

### Option 3: API-Based Onboarding Completion (FASTEST)

**Approach:** Skip UI skill input, directly POST to onboarding endpoint with complete skill data.

**Implementation:**
```python
def complete_onboarding_via_api(user_email: str, user_password: str, player_type: str = "balanced"):
    """Complete onboarding via API instead of UI (faster, more reliable)"""

    # Login to get auth token
    login_response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": user_email, "password": user_password}
    )
    token = login_response.json()["access_token"]

    # Load skill fixture
    player_data = load_player_skills(player_type)

    # Submit onboarding
    response = requests.post(
        f"{API_BASE_URL}/onboarding/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "position": player_data["position"],
            "goals": "Test player goals",
            "motivation": "Test player motivation",
            "skills": player_data["skills"]
        }
    )

    assert response.status_code == 200
    return response.json()

def test_onboarding_with_coupon_api_hybrid(page: Page):
    """Hybrid test: UI for coupon, API for onboarding"""

    # Step 1: Apply coupon via UI
    apply_coupon_via_ui(page, email, password, coupon_code)

    # Step 2: Unlock specialization via UI
    unlock_via_ui(page)

    # Step 3: Complete onboarding via API (FASTER!)
    complete_onboarding_via_api(email, password, "player_balanced")

    # Step 4: Verify onboarding completion via UI
    verify_onboarding_completion(page)
```

**Pros:**
- ✅ **Fastest** (no UI interaction for 29 sliders)
- ✅ **Most reliable** (no UI flakiness)
- ✅ **Deterministic** (API guarantees data format)
- ✅ **Complete test coverage** (all 29 skills guaranteed)

**Cons:**
- ⚠️ **Not a true E2E test** (skips UI interaction)
- ⚠️ **Doesn't validate UI** (slider rendering, interaction)
- ⚠️ **Hybrid approach** (mix of UI and API)

**Use Case:** Good for **testing business logic** (coupon + onboarding), not for **testing UI**.

---

## Decision Matrix

| Approach | Speed | Realism | Maintenance | Coverage | Recommendation |
|----------|-------|---------|-------------|----------|----------------|
| **Option 1: Dynamic Discovery** | Medium | Medium | Low | High | ✅ **QUICK FIX** |
| **Option 2: JSON Fixtures** | Slow | High | Medium | High | ✅ **IDEAL LONG-TERM** |
| **Option 3: API Hybrid** | Fast | Low | Low | Medium | ⚠️ **SPECIALIZED USE** |

---

## Immediate Action Plan

### Phase 1: Quick Fix (Option 1) - 30 minutes

1. Update `test_onboarding_with_coupon.py` to set ALL sliders dynamically
2. Use deterministic baseline value (e.g., 60/100)
3. Run test to verify ALL 29 skills are set
4. Commit fix with message: "fix(test): Set all 29 skills in onboarding test (was 6)"

### Phase 2: Validation (1 hour)

1. **Inspect Streamlit onboarding UI code** to verify:
   - How many sliders are rendered (should be 29)
   - Slider value range (0-100)
   - Skill order in UI
2. **Verify backend logs** during test run:
   - Check if "⚠️ Skill mismatch" warning disappears
   - Confirm `{len(skills)} skills received` shows 29
3. **Inspect database after test**:
   - Verify `UserLicense.football_skills` has all 29 skills
   - Confirm no DEFAULT_BASELINE (50.0) fallbacks

### Phase 3: Long-Term (Option 2) - 4 hours

1. Create `tests/fixtures/onboarding_skills.json` with:
   - Balanced player (MIDFIELDER)
   - Striker (STRIKER)
   - Defender (DEFENDER)
   - Goalkeeper (GOALKEEPER)
2. Map Streamlit UI slider order to skill keys
3. Update test to load and use JSON fixtures
4. Run test suite to verify all onboarding tests pass
5. Document fixture format in `tests/fixtures/README.md`

---

## Open Questions

### 1. Streamlit UI Skill Rendering

**Question:** How many sliders does the Streamlit onboarding UI actually render?

**Action:** Inspect Streamlit onboarding page code to confirm:
- Slider count (should be 29)
- Skill order
- Value range (0-100)

**File to check:** `app/templates/onboarding_lfa_player.html` or equivalent Streamlit page

---

### 2. Backend Validation Behavior

**Question:** Why does backend LOG skill mismatch but NOT FAIL?

**Answer:** Backend is lenient for backward compatibility (handles old data).

**Risk:** If backend tightens validation in future, test will FAIL.

**Mitigation:** Update test NOW to submit all 29 skills.

---

### 3. Test Data Strategy

**Question:** Should we use:
- Fixed baseline (all skills = 60)?
- Position-specific values (striker high finishing, defender high tackle)?
- Random values (current approach)?

**Recommendation:**
- **Quick fix:** Fixed baseline (60/100) for ALL skills
- **Long-term:** Position-specific JSON fixtures

---

### 4. Headed vs Headless

**Question:** Should test run headed or headless?

**Current:** Headed (visible browser)

**User Suggestion:** Convert to headless for stability

**Recommendation:** Convert to headless AFTER skill logic is fixed and stabilized.

---

## Conclusion

**CRITICAL FINDING:** Test currently sets **ONLY 6/29 skills** with **RANDOM values (1-10)** instead of **ALL 29 skills (0-100)**.

**Impact:**
- ✅ Test still passes (lenient backend)
- ⚠️ Poor test data quality (23 skills default to 50.0)
- ⚠️ Test does NOT match production onboarding
- ⚠️ Regression risk if backend validation tightens

**Recommended Fix:** **Option 1 (Dynamic Discovery)** as quick fix, then **Option 2 (JSON Fixtures)** for long-term maintainability.

**Timeline:**
- Phase 1 (Quick Fix): 30 minutes
- Phase 2 (Validation): 1 hour
- Phase 3 (JSON Fixtures): 4 hours

**Priority:** HIGH (production-critical onboarding flow)

---

**Next Step:** Implement Phase 1 quick fix and validate with backend logs.

---

**Prepared by:** Claude Code (Sonnet 4.5)
**Date:** 2026-02-08
**Version:** 1.0
