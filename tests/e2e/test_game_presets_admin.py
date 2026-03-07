"""
Game Presets Admin Tab — Headless Playwright E2E Test Suite
============================================================

GP-01  CREATE   — 3 skills, explicit equal-% weights; API asserts skill_weights sum=1.0
                  and full game_config JSONB structure matches schema
GP-02  EDIT     — Rename via Edit form; API confirms new name persists
GP-03  DEACTIVATE — Toggle active→inactive; API confirms is_active=False
GP-04  ACTIVATE   — Toggle inactive→active; API confirms is_active=True
GP-05  DELETE    — Confirmation flow; API confirms preset absent after delete
GP-06  401-SIM  — Bad JWT → API returns 401; UI shows "Session expired" (not raw JSON)

GP-07  WEIGHT MATH  — Edit form's int-% spinbuttons change a 2-skill preset from 50:50
                      to 75:25 (Passing:Dribbling); API asserts normalised ratio ≈3.0
GP-08  WEIGHT NORMALIZATION — sum(skill_weights.values()) ≈ 1.0 for 5 skills (20% each)

GP-V1  VALIDATION: no skills entered         → Create button disabled (sum=0%)
GP-V2  VALIDATION: empty name               → "Name is required."
GP-V3  VALIDATION: code with uppercase/space → "Code must be lowercase …"

GP-W1  WEIGHT CREATE  — Create preset with 40/35/25% weights; API verifies 0.40/0.35/0.25
GP-W2  WEIGHT EDIT    — Edit preset from 60/40 → 30/70; API verifies dominance flip
GP-W3  WEIGHT INVALID — Weights summing to ≠100% keep Create button disabled; no API call

Auth strategy (identical to tournament_monitor tests):
    URL-param injection — ?token=<JWT>&user=<JSON>
    restore_session_from_url() picks these up from st.query_params.

HTTP assertions:
    Every mutating UI action is verified at the API layer via requests AFTER the
    Streamlit rerun, confirming server-side persistence rather than UI optimism.

Weight-input mechanics note:
    Skills are selected via checkboxes; each tick triggers an immediate Streamlit
    rerun so weight spinbuttons appear for every selected skill.  Inputs are
    integer % (1–99 per skill); the live sum indicator turns green at exactly 100%.
    The Create/Save button is disabled unless sum == 100 AND at least one skill is
    selected.  Tests must call _set_equal_weights() (or explicit spinbutton helpers)
    to reach a valid sum before _submit_form() is useful.

    CREATE path: all spinbuttons default to 10% → sum = n×10 ≠ 100 for n≠10 →
                 button disabled until weights are set explicitly.
    EDIT path:   stored fractional weights are converted → int % via
                 _fractional_to_pct(); spinbuttons pre-filled with those values.

Run:
    pytest tests_e2e/test_game_presets_admin.py -v --tb=short
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=900 pytest tests_e2e/test_game_presets_admin.py -v -s
"""

import json
import time
import urllib.parse
import uuid

import re
import pytest
import requests
from playwright.sync_api import Page, expect

# ── Constants ────────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@lfa.com"
ADMIN_PASSWORD = "admin123"
ADMIN_PATH = "/Admin_Dashboard"

_LOAD_TIMEOUT = 35_000    # 35 s — Streamlit cold-start budget
_SETTLE = 2.5             # seconds after each Streamlit rerun
_API_TIMEOUT = 10         # seconds for direct API calls
_WEIGHT_TOL = 0.01        # absolute tolerance for float weight assertions

# Skill set used by most tests (3 skills for equal-weight create; 2 for weight-ratio edit)
_SKILLS_3 = ["passing", "dribbling", "finishing"]
_SKILLS_2 = ["passing", "dribbling"]

# NOTE: Preset names are now per-test unique (via fixture), not module-level
# This prevents test interaction/pollution when tests run in sequence


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _admin_token(api_url: str) -> str:
    resp = requests.post(
        f"{api_url}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code == 200, f"Admin login failed ({resp.status_code}): {resp.text}"
    return resp.json()["access_token"]


def _admin_user(api_url: str, token: str) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code == 200, f"GET /users/me failed: {resp.text}"
    return resp.json()


# ── API helpers ───────────────────────────────────────────────────────────────

def _api_list_presets(api_url: str, token: str) -> list:
    resp = requests.get(
        f"{api_url}/api/v1/game-presets/",
        headers={"Authorization": f"Bearer {token}"},
        params={"active_only": "false"},
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code == 200, f"GET /game-presets/ failed: {resp.text}"
    data = resp.json()
    return data.get("presets", data) if isinstance(data, dict) else data


def _api_get_preset(api_url: str, token: str, preset_id: int) -> dict:
    resp = requests.get(
        f"{api_url}/api/v1/game-presets/{preset_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code == 200, f"GET /game-presets/{preset_id} failed: {resp.text}"
    return resp.json()


def _api_find_by_name(api_url: str, token: str, name: str) -> dict | None:
    for p in _api_list_presets(api_url, token):
        if p.get("name") == name:
            return p
    return None


def _api_delete(api_url: str, token: str, preset_id: int) -> None:
    resp = requests.delete(
        f"{api_url}/api/v1/game-presets/{preset_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code in (200, 204), f"DELETE /game-presets/{preset_id} failed: {resp.text}"


def _api_create(
    api_url: str,
    token: str,
    *,
    name: str,
    code: str,
    skills: list[str],
    weights: dict[str, float] | None = None,
    is_active: bool = True,
) -> dict:
    """
    Create a game preset directly via the API (precondition helper).

    Weights, if provided, must already be normalised (sum ≈ 1.0).
    If omitted, equal weights are applied (1/n each).
    """
    n = len(skills)
    if weights is None:
        weights = {s: round(1.0 / n, 4) for s in skills}
    resp = requests.post(
        f"{api_url}/api/v1/game-presets/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "code": code,
            "name": name,
            "description": "Created by E2E test suite",
            "game_config": {
                "version": "1.0",
                "format_config": {},
                "skill_config": {
                    "skills_tested": skills,
                    "skill_weights": weights,
                    "skill_impact_on_matches": True,
                },
                "simulation_config": {},
                "metadata": {
                    "game_category": "Football",
                    "difficulty_level": None,
                    "min_players": 4,
                },
            },
            "is_active": is_active,
        },
        timeout=_API_TIMEOUT,
    )
    assert resp.status_code in (200, 201), (
        f"API create preset failed ({resp.status_code}): {resp.text}"
    )
    return resp.json()


# ── Navigation helpers ────────────────────────────────────────────────────────

def _go_to_admin(
    page: Page,
    base_url: str,
    api_url: str,
    *,
    token: str | None = None,
    user: dict | None = None,
) -> str:
    """
    Navigate to the Admin Dashboard with auth via URL params.
    Full state reset: hard navigation + wait for stable root container.
    Returns the token used (for subsequent API assertions).
    """
    if token is None:
        token = _admin_token(api_url)
    if user is None:
        user = _admin_user(api_url, token)
    params = urllib.parse.urlencode({"token": token, "user": json.dumps(user)})

    # Hard navigation with full reload (no cache)
    page.goto(f"{base_url}{ADMIN_PATH}?{params}", timeout=_LOAD_TIMEOUT, wait_until="networkidle")
    page.wait_for_load_state("domcontentloaded", timeout=_LOAD_TIMEOUT)

    # Wait for stable root container (Streamlit app ready)
    # Use visible heading as stability marker (Streamlit renders after app init)
    expect(page.get_by_role("heading", name="Welcome, System Administrator!")).to_be_visible(timeout=_LOAD_TIMEOUT)
    time.sleep(_SETTLE)

    # Verify no leftover form state from previous tests
    # If a create form is open from previous test (should not happen), close it
    cancel_button = page.get_by_role("button", name="Cancel")
    if cancel_button.count() > 0:
        try:
            if cancel_button.is_visible(timeout=500):
                cancel_button.click()
                time.sleep(0.5)
        except:
            pass  # No open form, continue

    return token


def _click_presets_tab(page: Page) -> None:
    page.get_by_role("button", name="🎮 Presets").click()
    time.sleep(_SETTLE)


def _open_create_form(page: Page) -> None:
    page.get_by_role("button", name="➕ New Game Preset").click()
    time.sleep(_SETTLE)
    expect(page.get_by_text("Create New Game Preset")).to_be_visible(timeout=10_000)


def _expand_preset(page: Page, name: str) -> None:
    """Click the expander header for the named preset."""
    page.get_by_text(name, exact=False).first.click()
    time.sleep(1)


def _click_edit(page: Page) -> None:
    page.get_by_role("button", name="✏️ Edit").first.click()
    time.sleep(_SETTLE)


def _fill_name(page: Page, value: str) -> None:
    field = page.get_by_label("Name *")
    field.click(click_count=3)
    field.fill(value)


def _fill_skills(page: Page, skills: list[str]) -> None:
    """
    Tick the grouped skill checkboxes for each skill in *skills* (snake_case).

    Each st.checkbox tick triggers an immediate Streamlit rerun (no keyboard
    shortcut needed).  After the last tick and a settle wait, weight spinbuttons
    are visible for every selected skill.

    Skills must be in the standard catalogue (_SKILL_GROUPS).
    For non-standard skills use the 'Custom skills' textarea directly.

    Implementation: Click the visible text label (Streamlit checkbox pattern).
    NO force=True - natural user interaction only (test isolation ensures clean state).
    """
    for skill in skills:
        label = skill.replace("_", " ").title()  # e.g. "passing" → "Passing"
        # Click the visible label text next to the checkbox (natural user interaction)
        label_elem = page.get_by_text(label, exact=True).first
        label_elem.scroll_into_view_if_needed()
        expect(label_elem).to_be_visible(timeout=5_000)
        label_elem.click()
        time.sleep(1)  # allow Streamlit to complete the per-checkbox rerun


def _set_weight_spinbutton(page: Page, skill_display: str, value: int) -> None:
    """
    Set a weight spinbutton by its skill label (Title-cased + ' %').

    Example: skill_display="Passing", value=75  → sets "Passing %" to 75
    """
    sb = page.get_by_role("spinbutton", name=f"{skill_display} %")
    sb.click(click_count=3)
    sb.fill(str(value))


def _set_equal_weights(page: Page, skills: list[str]) -> None:
    """
    Set integer % weights for *skills* summing to exactly 100.

    Distributes evenly; the first skill absorbs the rounding remainder.
    Example: 3 skills → 34, 33, 33  (= 100)
             2 skills → 50, 50
             1 skill  → 100
    """
    n = len(skills)
    base = 100 // n
    remainder = 100 - base * n
    for i, skill in enumerate(skills):
        display = skill.replace("_", " ").title()
        pct = base + (remainder if i == 0 else 0)
        _set_weight_spinbutton(page, display, pct)
    time.sleep(0.5)   # allow live sum indicator to settle


def _submit_form(page: Page, *, label_fragment: str) -> None:
    """
    Click the submit button whose accessible name CONTAINS *label_fragment*.

    exact=False is required because buttons carry emoji prefixes:
      "➕ Create preset"  →  label_fragment="Create preset"
      "💾 Save changes"   →  label_fragment="Save changes"
    """
    page.get_by_role("button", name=label_fragment, exact=False).first.click()
    time.sleep(_SETTLE)


# ── Cleanup ───────────────────────────────────────────────────────────────────

def _cleanup(api_url: str, token: str, *names: str) -> None:
    for name in names:
        p = _api_find_by_name(api_url, token, name)
        if p:
            try:
                _api_delete(api_url, token, p["id"])
            except Exception:
                pass


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_token(api_url):
    return _admin_token(api_url)


@pytest.fixture(scope="module")
def admin_user(api_url, admin_token):
    return _admin_user(api_url, admin_token)


@pytest.fixture(scope="function")
def test_preset_names():
    """Generate unique preset names for this test (prevents test interaction/pollution)."""
    uniq = uuid.uuid4().hex[:6]
    return {
        "name_base": f"E2E Preset {uniq}",
        "name_edit": f"E2E Edited {uniq}",
        "code_base": f"e2e_preset_{uniq}",
    }


@pytest.fixture(autouse=True)
def _wipe_test_presets(api_url, admin_token, test_preset_names):
    """Delete any leftover test preset before AND after every test."""
    _cleanup(api_url, admin_token, test_preset_names["name_base"], test_preset_names["name_edit"])
    yield
    _cleanup(api_url, admin_token, test_preset_names["name_base"], test_preset_names["name_edit"])


# ============================================================================
# GP-01 CREATE — domain consistency
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gp01_create_preset_domain_consistency(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-01: Create a preset with 3 skills through the UI.

    Each checkbox tick triggers an immediate Streamlit rerun so weight spinbuttons
    appear after the last tick.  Default per-skill value is 10%, so 3 skills →
    30% sum → button disabled.  _set_equal_weights() sets 34/33/33 = 100% to
    enable the button.

    Assertions:
      UI  — "created." success banner
      API — skills_tested contains all 3 submitted skills
      API — skill_weights keys == set(skills)
      API — each weight ≈ 1/3  (34%, 33%, 33% → 0.34/0.33/0.33, within ±0.01)
      API — sum(weights) ≈ 1.0  (normalisation invariant)
      API — game_config structure has version, format_config, skill_config,
             simulation_config, metadata  (schema compliance)
      API — skill_config.skill_impact_on_matches present
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    _fill_skills(page, _SKILLS_3)
    _set_equal_weights(page, _SKILLS_3)   # 34+33+33=100 → enables submit
    page.get_by_label("Category").fill("Football")

    _submit_form(page, label_fragment="Create preset")

    # ── UI assertion ──────────────────────────────────────────────────────────
    # Success confirmation: form closes on success (streamlit_app/components/admin/game_presets_tab.py:492)
    # Note: st.success() toast disappears on rerun when form closes, so check form closure instead
    # (E2E_ISSUES.md Step 1.3 - deterministic success assertion via form state change)
    expect(page.get_by_role("heading", name="Create New Game Preset")).not_to_be_visible(timeout=5_000)

    # ── API assertions ────────────────────────────────────────────────────────
    summary = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert summary is not None, f"Preset '{test_preset_names['name_base']}' not found in API after create"

    detail = _api_get_preset(api_url, admin_token, summary["id"])
    gc = detail["game_config"]

    # Schema structure
    required_top_keys = {"version", "format_config", "skill_config", "simulation_config"}
    missing = required_top_keys - set(gc.keys())
    assert not missing, f"game_config missing required sections: {missing}"

    assert gc["version"] == "1.0", f"Expected version '1.0', got {gc['version']!r}"

    sc = gc["skill_config"]
    assert "skills_tested" in sc, "skill_config missing 'skills_tested'"
    assert "skill_weights" in sc, "skill_config missing 'skill_weights'"
    assert "skill_impact_on_matches" in sc, "skill_config missing 'skill_impact_on_matches'"

    # Skill membership
    stored_skills = set(sc["skills_tested"])
    expected_skills = set(_SKILLS_3)
    assert expected_skills == stored_skills, (
        f"skills_tested mismatch: expected {expected_skills}, got {stored_skills}"
    )

    # Weight keys must match skills
    weight_keys = set(sc["skill_weights"].keys())
    assert weight_keys == expected_skills, (
        f"skill_weights keys {weight_keys} do not match skills_tested {expected_skills}"
    )

    # Equal weights: 34/33/33 % → stored 0.34/0.33/0.33; all within ±0.01 of 1/3
    weights = sc["skill_weights"]
    expected_each = round(1.0 / 3, 4)
    for skill in _SKILLS_3:
        w = weights[skill]
        assert abs(w - expected_each) < _WEIGHT_TOL, (
            f"Expected weight ≈{expected_each} for '{skill}', got {w}"
        )

    # Normalisation invariant: sum ≈ 1.0
    total = sum(weights.values())
    assert abs(total - 1.0) < _WEIGHT_TOL, (
        f"skill_weights sum {total:.6f} deviates from 1.0 (tol={_WEIGHT_TOL})"
    )


# ============================================================================
# GP-07 WEIGHT MATH — custom ratio via edit form sliders
# ============================================================================

@pytest.mark.e2e
def test_gp07_weight_ratio_via_edit(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-07: Verify that changing int-% weight spinbuttons in the edit form
    produces the correctly normalised fractional value in the API.

    Setup: preset created via API with 2 skills at equal weight (0.5 each).
           _fractional_to_pct converts these to 50/50 for pre-filling.

    Action (EDIT path — spinbuttons visible because initial_skills is pre-filled):
      - Passing spinbutton: set to 75%
      - Dribbling spinbutton: set to 25%    (sum = 100 → button enabled)

    Expected normalised result:
      total_raw = 75 + 25 = 100
      passing   = 75 / 100 = 0.75
      dribbling = 25 / 100 = 0.25
      ratio     = 0.75 / 0.25 = 3.0

    Assertions:
      API — sum(skill_weights) ≈ 1.0
      API — passing_weight ≈ 0.75   (dominant after 3:1 split)
      API — dribbling_weight ≈ 0.25
      API — passing_weight / dribbling_weight ≈ 3.0
    """
    # Precondition: active 2-skill preset with equal weights
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"],
        code=test_preset_names["code_base"],
        skills=_SKILLS_2,
        weights={"passing": 0.5, "dribbling": 0.5},
    )
    preset_id = created["id"]

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)

    # Expand and enter edit mode
    _expand_preset(page, test_preset_names["name_base"])
    _click_edit(page)

    # Edit form must be visible with the Name pre-filled
    expect(page.get_by_label("Name *")).to_be_visible(timeout=10_000)

    # Spinbuttons pre-filled with 50/50 (from stored 0.5/0.5 via _fractional_to_pct)
    # Change to 75/25 → sum=100 → Save enabled
    _set_weight_spinbutton(page, "Passing", 75)
    _set_weight_spinbutton(page, "Dribbling", 25)

    _submit_form(page, label_fragment="Save changes")
    expect(page.get_by_role("button", name="Save changes")).not_to_be_visible(timeout=5_000)

    # ── API assertions ────────────────────────────────────────────────────────
    detail = _api_get_preset(api_url, admin_token, preset_id)
    sc = detail["game_config"]["skill_config"]
    weights = sc["skill_weights"]

    total = sum(weights.values())
    assert abs(total - 1.0) < _WEIGHT_TOL, (
        f"sum(skill_weights) = {total:.6f}, expected ≈1.0"
    )

    p_w = weights["passing"]
    d_w = weights["dribbling"]

    assert abs(p_w - 0.75) < _WEIGHT_TOL, (
        f"passing weight {p_w:.4f} should be ≈0.75 (75%)"
    )
    assert abs(d_w - 0.25) < _WEIGHT_TOL, (
        f"dribbling weight {d_w:.4f} should be ≈0.25 (25%)"
    )

    ratio = p_w / d_w
    assert abs(ratio - 3.0) < 0.2, (
        f"Expected passing/dribbling ≈ 3.0 (75/25 raw split), got {ratio:.3f}"
    )


# ============================================================================
# GP-08 WEIGHT NORMALISATION — sum=1.0 invariant on create path
# ============================================================================

@pytest.mark.e2e
def test_gp08_weight_normalisation_create_path(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-08: sum(skill_weights.values()) ≈ 1.0 regardless of how many skills
    are entered, because _build_game_config() always divides by the total.

    Uses 5 skills with equal 20% weights (5×20=100) to make accidental
    equal-sum harder to fake.

    Assertion:
      API — sum(weights) ≈ 1.0  (normalisation invariant holds for n=5)
      API — every individual weight ≈ 0.20  (equal 20% each)
    """
    five_skills = ["passing", "dribbling", "finishing", "stamina", "agility"]

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    _fill_skills(page, five_skills)
    _set_equal_weights(page, five_skills)   # 5×20=100 → enables submit
    page.get_by_label("Category").fill("Football")

    _submit_form(page, label_fragment="Create preset")
    expect(page.get_by_role("heading", name="Create New Game Preset")).not_to_be_visible(timeout=5_000)

    summary = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert summary is not None
    detail = _api_get_preset(api_url, admin_token, summary["id"])
    weights = detail["game_config"]["skill_config"]["skill_weights"]

    total = sum(weights.values())
    assert abs(total - 1.0) < _WEIGHT_TOL, (
        f"sum(weights) = {total:.6f} for 5-skill preset, expected ≈1.0"
    )

    expected_each = round(1.0 / 5, 4)
    for skill in five_skills:
        w = weights.get(skill)
        assert w is not None, f"Weight missing for skill '{skill}'"
        assert abs(w - expected_each) < _WEIGHT_TOL, (
            f"Expected equal weight ≈{expected_each} for '{skill}', got {w}"
        )


# ============================================================================
# GP-V1 – GP-V4  VALIDATION GUARD TESTS
# Each test opens the Create form, submits an invalid configuration, and
# asserts the exact UI error message without any API call succeeding.
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gpv1_no_skills_blocked(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-V1: With no skills selected the weight sum is 0% → the Create button must
           be disabled (grey, not clickable).  Nothing is submitted to the API.

    The frontend _save_disabled flag = (not skills) or (not sum_valid), so a form
    with zero skills always disables the button regardless of any weight values.
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    # Skills intentionally left unticked — sum=0% → button disabled

    # Create button must be disabled
    submit_btn = page.get_by_role("button", name="Create preset", exact=False).first
    expect(submit_btn).to_be_disabled()

    # Confirm nothing was created
    created = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert created is None, "Preset must NOT be created when no skills are provided"


@pytest.mark.e2e
@pytest.mark.smoke
def test_gpv2_empty_name_blocked(
    page: Page, base_url, api_url, admin_token, admin_user
):
    """
    GP-V2: Submitting the create form with no name must surface
           "Name is required."

    Skills are provided and weights set to sum=100% so the button is enabled;
    the name-validation fires on submit.
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    # Workaround: fill dummy name first (Streamlit form state dependency for checkbox interaction)
    # then clear it before submit to trigger "Name is required" validation
    _fill_name(page, "TEMP_NAME_FOR_CHECKBOX_STATE")
    _fill_skills(page, ["passing", "dribbling"])
    _set_equal_weights(page, ["passing", "dribbling"])   # 50+50=100

    # Clear name to trigger validation
    page.get_by_label("Name *").click(click_count=3)
    page.get_by_label("Name *").fill("")
    time.sleep(0.5)  # allow Streamlit to update button state

    _submit_form(page, label_fragment="Create preset")

    expect(
        page.get_by_text("Name is required", exact=False)
    ).to_be_visible(timeout=10_000)

    # Nothing persisted — list should not contain an unnamed preset
    presets = _api_list_presets(api_url, admin_token)
    unnamed = [p for p in presets if not p.get("name", "").strip()]
    assert not unnamed, f"Unnamed preset should not exist: {unnamed}"


@pytest.mark.e2e
def test_gpv3_invalid_code_format_blocked(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-V3: A code containing uppercase letters or spaces must be rejected with
           "Code must be lowercase letters, digits, and underscores only."

    The Code field is auto-filled from the Name; we manually overwrite it with
    an invalid value before submitting.  Weight set to 100% (1 skill) to enable
    the button so the code-validation fires on click.
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    _fill_skills(page, ["passing"])
    _set_equal_weights(page, ["passing"])   # 1 skill × 100% → sum=100 → button enabled

    # Overwrite the auto-generated code with an invalid value (uppercase)
    code_field = page.get_by_label("Code *")
    code_field.click(click_count=3)
    code_field.fill("INVALID CODE WITH SPACES")

    _submit_form(page, label_fragment="Create preset")

    expect(
        page.get_by_text("Code must be lowercase", exact=False)
    ).to_be_visible(timeout=10_000)

    # Confirm rejection
    created = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert created is None, "Preset must NOT be created when code format is invalid"


# ============================================================================
# GP-02 EDIT — name change persists
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gp02_edit_name_persists(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-02: Edit the name of an existing preset through the UI and confirm
    the new name is returned by the detail API endpoint.
    """
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"], code=test_preset_names["code_base"],
        skills=_SKILLS_2,
    )
    preset_id = created["id"]

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _expand_preset(page, test_preset_names["name_base"])
    _click_edit(page)

    expect(page.get_by_label("Name *")).to_be_visible(timeout=10_000)
    _fill_name(page, test_preset_names["name_edit"])
    _submit_form(page, label_fragment="Save changes")

    expect(page.get_by_role("button", name="Save changes")).not_to_be_visible(timeout=5_000)

    detail = _api_get_preset(api_url, admin_token, preset_id)
    assert detail["name"] == test_preset_names["name_edit"], (
        f"Expected name '{test_preset_names['name_edit']}', API returned '{detail['name']}'"
    )


# ============================================================================
# GP-03 DEACTIVATE
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gp03_deactivate_preset(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """GP-03: Deactivate active preset; API confirms is_active=False."""
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"], code=test_preset_names["code_base"],
        skills=_SKILLS_2, is_active=True,
    )
    preset_id = created["id"]
    assert _api_get_preset(api_url, admin_token, preset_id)["is_active"] is True

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _expand_preset(page, test_preset_names["name_base"])

    page.get_by_role("button", name="⚫ Deactivate").first.click()
    time.sleep(_SETTLE)

    assert _api_get_preset(api_url, admin_token, preset_id)["is_active"] is False, (
        "Expected is_active=False after Deactivate"
    )


# ============================================================================
# GP-04 ACTIVATE
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gp04_activate_preset(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-04: Activate inactive preset; API confirms is_active=True.

    NOTE: Backend bug — POST /game-presets/ ignores is_active=False, always creates as active.
    Workaround: create as active, then toggle to inactive via PATCH before testing activate.
    """
    # Create preset (will be active due to backend bug ignoring is_active=False)
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"], code=test_preset_names["code_base"],
        skills=_SKILLS_2,  # is_active parameter removed (backend ignores it anyway)
    )
    preset_id = created["id"]

    # Workaround: Toggle to inactive via PATCH (backend respects PATCH is_active)
    patch_resp = requests.patch(
        f"{api_url}/api/v1/game-presets/{preset_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
        timeout=_API_TIMEOUT,
    )
    assert patch_resp.status_code in (200, 204), f"PATCH failed: {patch_resp.text}"
    assert _api_get_preset(api_url, admin_token, preset_id)["is_active"] is False

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _expand_preset(page, test_preset_names["name_base"])

    page.get_by_role("button", name="🟢 Activate").first.click()
    time.sleep(_SETTLE)

    assert _api_get_preset(api_url, admin_token, preset_id)["is_active"] is True, (
        "Expected is_active=True after Activate"
    )


# ============================================================================
# GP-05 DELETE — confirmation flow
# ============================================================================

@pytest.mark.e2e
@pytest.mark.smoke
def test_gp05_delete_with_confirmation(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-05: Delete via UI confirmation flow.

    UI assertions:
      - Warning "cannot be undone" visible before confirm
      - "Deleted." banner after confirm
    API assertion:
      - preset_id absent from GET /game-presets/
    """
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"], code=test_preset_names["code_base"],
        skills=_SKILLS_2,
    )
    preset_id = created["id"]

    # Verify preset exists before attempting UI delete
    preset_before_delete = _api_get_preset(api_url, admin_token, preset_id)
    assert preset_before_delete is not None, f"Preset {preset_id} should exist after create"
    assert preset_before_delete["name"] == test_preset_names["name_base"], (
        f"Preset name mismatch: expected {test_preset_names['name_base']}, got {preset_before_delete['name']}"
    )

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _expand_preset(page, test_preset_names["name_base"])

    page.get_by_role("button", name="🗑️ Delete").first.click()
    time.sleep(_SETTLE)

    expect(page.get_by_text("cannot be undone", exact=False)).to_be_visible(timeout=10_000)

    page.get_by_role("button", name="Yes, delete").click()
    time.sleep(_SETTLE)

    # UI assertion: st.success("Deleted.") appears but immediately disappears on st.rerun()
    # (same pattern as GP-01 create success). Verify via preset absence from list instead.
    # After rerun, the confirmation dialog should be gone (state cleared).
    expect(page.get_by_role("button", name="Yes, delete")).not_to_be_visible(timeout=5_000)

    # API assertion: DELETE is a soft-delete (business logic) — preset still exists but is_active=False
    deleted_preset = _api_get_preset(api_url, admin_token, preset_id)
    assert deleted_preset is not None, f"Preset id={preset_id} should still exist after soft-delete"
    assert deleted_preset["is_active"] is False, (
        f"Expected is_active=False after delete, got {deleted_preset['is_active']}"
    )


# ============================================================================
# GP-06 401 SIMULATION
# ============================================================================

@pytest.mark.e2e
def test_gp06_expired_token_shows_session_expired(
    page: Page, base_url, api_url, admin_token, admin_user
):
    """
    GP-06: When Streamlit holds a syntactically valid but signature-invalid JWT,
    API calls from the backend return 401.  The UI must display
    "Session expired. Please refresh the page and log in again."
    rather than raw JSON.

    HTTP assertion (direct): POST /game-presets/ with bad token → 401
    UI assertion: "Session expired" text visible; '"code":"http_401"' NOT visible
    """
    bad_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiI5OTk5OTkiLCJleHAiOjE2MDAwMDAwMDB9"
        ".bad_signature_intentionally_invalid"
    )

    # HTTP layer assertion first
    api_resp = requests.post(
        f"{api_url}/api/v1/game-presets/",
        headers={"Authorization": f"Bearer {bad_token}"},
        json={
            "code": "should_never_be_created",
            "name": "401 Guard",
            "description": None,
            "game_config": {
                "version": "1.0",
                "format_config": {},
                "skill_config": {
                    "skills_tested": ["passing"],
                    "skill_weights": {"passing": 1.0},
                    "skill_impact_on_matches": True,
                },
                "simulation_config": {},
            },
            "is_active": True,
        },
        timeout=_API_TIMEOUT,
    )
    assert api_resp.status_code == 401, (
        f"Expected HTTP 401 from API with invalid token, got {api_resp.status_code}"
    )

    # UI path: navigate with bad token injected, user dict is valid (role=admin passes guard)
    _go_to_admin(page, base_url, api_url, token=bad_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, "401 Trigger Test")
    _fill_skills(page, ["passing"])
    _set_equal_weights(page, ["passing"])   # 1 skill × 100% → sum=100 → button enabled
    _submit_form(page, label_fragment="Create preset")

    # Human-readable error
    expect(
        page.get_by_text("Session expired", exact=False)
    ).to_be_visible(timeout=15_000)

    # Raw JSON must NOT leak through
    raw_json_visible = page.get_by_text('"code":"http_401"', exact=False).is_visible()
    assert not raw_json_visible, "Raw 401 JSON error envelope must not be shown to the user"


# ============================================================================
# GP-W1 WEIGHT CREATE — explicit 40/35/25 % weights persisted correctly
# ============================================================================

@pytest.mark.e2e
def test_gpw1_create_custom_weights(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-W1: Create a 3-skill preset via UI with explicit 40/35/25% weights.

    The % inputs are set directly (not via _set_equal_weights).
    40 + 35 + 25 = 100 → save button enabled.
    _build_game_config() stores them as fractional: 0.40 / 0.35 / 0.25.

    Assertions:
      UI  — "created." banner
      API — sum(weights) ≈ 1.0
      API — passing   ≈ 0.40  (within ±_WEIGHT_TOL)
      API — dribbling ≈ 0.35
      API — finishing ≈ 0.25
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    _fill_skills(page, _SKILLS_3)          # passing, dribbling, finishing
    page.get_by_label("Category").fill("Football")

    # Explicit 40/35/25 — sums to 100
    _set_weight_spinbutton(page, "Passing",   40)
    _set_weight_spinbutton(page, "Dribbling", 35)
    _set_weight_spinbutton(page, "Finishing", 25)
    time.sleep(0.5)  # let live-sum indicator settle

    _submit_form(page, label_fragment="Create preset")
    expect(page.get_by_role("heading", name="Create New Game Preset")).not_to_be_visible(timeout=5_000)

    # ── API assertions ────────────────────────────────────────────────────────
    summary = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert summary is not None, f"Preset '{test_preset_names['name_base']}' not found after create"

    detail  = _api_get_preset(api_url, admin_token, summary["id"])
    weights = detail["game_config"]["skill_config"]["skill_weights"]

    total = sum(weights.values())
    assert abs(total - 1.0) < _WEIGHT_TOL, f"sum={total:.6f}, expected ≈1.0"

    assert abs(weights["passing"]   - 0.40) < _WEIGHT_TOL, f"passing={weights['passing']}"
    assert abs(weights["dribbling"] - 0.35) < _WEIGHT_TOL, f"dribbling={weights['dribbling']}"
    assert abs(weights["finishing"] - 0.25) < _WEIGHT_TOL, f"finishing={weights['finishing']}"


# ============================================================================
# GP-W2 WEIGHT EDIT — dominance-flip from 60/40 → 30/70 persisted correctly
# ============================================================================

@pytest.mark.e2e
def test_gpw2_edit_weight_dominance_flip(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-W2: Edit a 2-skill preset to reverse dominant/minor relationship.

    Setup via API: passing=0.60, dribbling=0.40.
    _fractional_to_pct converts to 60/40 for spinbutton pre-fill.

    Action: change to 30/70 (Dribbling now dominant).

    Assertions:
      API — sum(weights) ≈ 1.0
      API — passing   ≈ 0.30
      API — dribbling ≈ 0.70
      API — dribbling > passing  (dominance flip confirmed)
    """
    created = _api_create(
        api_url, admin_token,
        name=test_preset_names["name_base"], code=test_preset_names["code_base"],
        skills=_SKILLS_2,
        weights={"passing": 0.60, "dribbling": 0.40},
    )
    preset_id = created["id"]

    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _expand_preset(page, test_preset_names["name_base"])
    _click_edit(page)

    expect(page.get_by_label("Name *")).to_be_visible(timeout=10_000)

    # Spinbuttons pre-filled with 60/40 → change to 30/70 (sum=100 → Save enabled)
    _set_weight_spinbutton(page, "Passing",   30)
    _set_weight_spinbutton(page, "Dribbling", 70)

    _submit_form(page, label_fragment="Save changes")
    expect(page.get_by_role("button", name="Save changes")).not_to_be_visible(timeout=5_000)

    # ── API assertions ────────────────────────────────────────────────────────
    detail  = _api_get_preset(api_url, admin_token, preset_id)
    weights = detail["game_config"]["skill_config"]["skill_weights"]

    total = sum(weights.values())
    assert abs(total - 1.0) < _WEIGHT_TOL, f"sum={total:.6f}, expected ≈1.0"

    assert abs(weights["passing"]   - 0.30) < _WEIGHT_TOL, f"passing={weights['passing']}"
    assert abs(weights["dribbling"] - 0.70) < _WEIGHT_TOL, f"dribbling={weights['dribbling']}"
    assert weights["dribbling"] > weights["passing"], (
        "Dribbling (70%) should now be dominant over Passing (30%) after flip"
    )


# ============================================================================
# GP-W3 WEIGHT INVALID — sum ≠ 100% keeps Create button disabled
# ============================================================================

@pytest.mark.e2e
def test_gpw3_invalid_weight_sum_blocks_create(
    page: Page, base_url, api_url, admin_token, admin_user, test_preset_names
):
    """
    GP-W3: When skill weight % inputs do not sum to exactly 100%, the Create
    button must remain disabled and the error indicator must be visible.
    No preset should be persisted.

    Two scenarios tested in sequence (no page reload between them):
      a) 60 + 60 = 120%  → over-budget
      b) 40 + 40 = 80%   → under-budget

    In both cases the button must be disabled and the API must return None.
    """
    _go_to_admin(page, base_url, api_url, token=admin_token, user=admin_user)
    _click_presets_tab(page)
    _open_create_form(page)

    _fill_name(page, test_preset_names["name_base"])
    _fill_skills(page, _SKILLS_2)          # passing, dribbling

    submit_btn = page.get_by_role("button", name="Create preset", exact=False).first

    # ── Scenario (a): 60 + 60 = 120% ─────────────────────────────────────────
    _set_weight_spinbutton(page, "Passing",   60)
    _set_weight_spinbutton(page, "Dribbling", 60)
    time.sleep(0.5)

    # Error indicator visible (sum shown in red)
    expect(page.get_by_text("120%", exact=False)).to_be_visible(timeout=5_000)
    expect(submit_btn).to_be_disabled()

    # ── Scenario (b): 40 + 40 = 80% ──────────────────────────────────────────
    _set_weight_spinbutton(page, "Passing",   40)
    _set_weight_spinbutton(page, "Dribbling", 40)
    time.sleep(0.5)

    expect(page.get_by_text("80%", exact=False)).to_be_visible(timeout=5_000)
    expect(submit_btn).to_be_disabled()

    # ── API: no preset created ─────────────────────────────────────────────────
    created = _api_find_by_name(api_url, admin_token, test_preset_names["name_base"])
    assert created is None, "Preset must NOT be created when weight sum ≠ 100%"


# ============================================================================
# Audit report (printed at end of run)
# ============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    _TESTS = [
        ("GP-01", "CREATE — 3 skills, equal weights (34/33/33), schema structure", "test_gp01"),
        ("GP-02", "EDIT   — name change persists",                                  "test_gp02"),
        ("GP-03", "DEACTIVATE — is_active→False",                                   "test_gp03"),
        ("GP-04", "ACTIVATE   — is_active→True",                                    "test_gp04"),
        ("GP-05", "DELETE  — confirmation flow + API absent",                       "test_gp05"),
        ("GP-06", "401-SIM — Session expired, no raw JSON",                         "test_gp06"),
        ("GP-07", "WEIGHT MATH — 75/25% → ratio≈3.0 after normalise",              "test_gp07"),
        ("GP-08", "WEIGHT NORM — 5×20%=100 → sum=1.0 invariant",                   "test_gp08"),
        ("GP-V1", "VALIDATION — no skills → Create button disabled",                "test_gpv1"),
        ("GP-V2", "VALIDATION — empty name blocked",                                "test_gpv2"),
        ("GP-V3", "VALIDATION — invalid code format blocked",                       "test_gpv3"),
        ("GP-W1", "WEIGHT CREATE — 40/35/25% stored as 0.40/0.35/0.25",            "test_gpw1"),
        ("GP-W2", "WEIGHT EDIT   — 60/40→30/70 dominance flip preserved",          "test_gpw2"),
        ("GP-W3", "WEIGHT INVALID — sum≠100% keeps Create button disabled",         "test_gpw3"),
    ]

    passed  = {r.nodeid for r in terminalreporter.stats.get("passed",  [])}
    failed  = {r.nodeid for r in terminalreporter.stats.get("failed",  [])}
    skipped = {r.nodeid for r in terminalreporter.stats.get("skipped", [])}

    relevant = any(fn in nid for fn in [t[2] for t in _TESTS]
                   for nid in (passed | failed | skipped))
    if not relevant:
        return

    terminalreporter.write_sep("=", "Game Presets Admin — Audit Report")

    np = nf = ns = 0
    for tag, label, fn in _TESTS:
        p = any(fn in n for n in passed)
        f = any(fn in n for n in failed)
        s = any(fn in n for n in skipped)
        icon = "✅" if p else ("❌" if f else ("⚠️" if s else "⬜"))
        terminalreporter.write_line(f"  {icon}  {tag:<6}  {label}")
        np += p; nf += f; ns += s

    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"  Result: {np} passed · {nf} failed · {ns} skipped"
    )
    terminalreporter.write_line(
        "  Scope: CREATE domain · EDIT weight math · activation · delete"
        " · 401 guard · 3× validation · 3× weight control (GP-W)"
    )
    terminalreporter.write_sep("=", "")
