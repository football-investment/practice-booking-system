# 🔧 E2E Test Setup Instructions

**Status:** ⚠️ Tests need UI selector customization
**Estimated Time:** 30-60 minutes

---

## Current Situation

✅ **What's Ready:**
- Playwright installed and configured
- 17 E2E tests created with full test logic
- Test framework and fixtures implemented
- Streamlit app is running

⚠️ **What Needs Adjustment:**
- Login selectors need to match your actual Streamlit UI
- Navigation selectors need customization
- Button selectors may need fine-tuning

---

## Step-by-Step Setup Guide

### Step 1: Update Login Selectors

**File to edit:** `tests/e2e/conftest.py`
**Lines:** 90-111 (function `login_as_instructor`)

**Current code (generic):**
```python
def login_as_instructor(page: Page) -> None:
    page.goto(STREAMLIT_URL)
    page.wait_for_selector("text=Login", timeout=10000)

    # Try different selector strategies
    try:
        page.fill("[data-testid='stTextInput']", INSTRUCTOR_EMAIL)
        page.keyboard.press("Tab")
        page.fill("[data-testid='stTextInput']:nth-child(2)", INSTRUCTOR_PASSWORD)
    except:
        # ... alternative strategies
```

**How to fix:**

1. **Open Streamlit app in browser:**
   ```bash
   open http://localhost:8501
   ```

2. **Inspect login form elements:**
   - Right-click on email field → Inspect
   - Note the actual selector (id, class, data-testid, etc.)
   - Do the same for password field and login button

3. **Update selectors in conftest.py:**
   ```python
   # Example: If your email field has id="email_input"
   page.fill("#email_input", INSTRUCTOR_EMAIL)
   page.fill("#password_input", INSTRUCTOR_PASSWORD)
   page.click("#login_button")

   # Or if using Streamlit keys:
   page.fill("[key='email']", INSTRUCTOR_EMAIL)
   page.fill("[key='password']", INSTRUCTOR_PASSWORD)
   ```

4. **Update post-login verification:**
   ```python
   # Change this line to match what appears after login
   page.wait_for_selector("text=Dashboard, text=Instructor", timeout=15000)

   # To match your actual UI (examples):
   page.wait_for_selector("text=Welcome", timeout=15000)
   # OR
   page.wait_for_selector("h1:has-text('Dashboard')", timeout=15000)
   # OR
   page.wait_for_selector("[data-testid='main-dashboard']", timeout=15000)
   ```

---

### Step 2: Test Login Manually

**Create a simple test file:**

`tests/e2e/test_login_manual.py`:
```python
"""Manual login test to verify selectors."""

import pytest
from playwright.sync_api import Page

def test_login_works(page: Page):
    """Test if login selectors are correct."""
    page.goto("http://localhost:8501")

    # Wait for page to load
    page.wait_for_timeout(2000)

    # Take screenshot of login page
    page.screenshot(path="login_page.png")
    print("Screenshot saved: login_page.png")

    # Try to login (update selectors as needed)
    page.fill("YOUR_EMAIL_SELECTOR", "instructor@lfa.com")
    page.fill("YOUR_PASSWORD_SELECTOR", "instructor123")
    page.click("YOUR_LOGIN_BUTTON_SELECTOR")

    # Wait and take screenshot
    page.wait_for_timeout(3000)
    page.screenshot(path="after_login.png")
    print("Screenshot saved: after_login.png")

    # Check if login succeeded
    assert "Dashboard" in page.content() or "Welcome" in page.content()
```

**Run it:**
```bash
PYTHONPATH=. pytest tests/e2e/test_login_manual.py -v --headed --slowmo 1000
```

This will:
- Open browser in headed mode
- Run slowly (1s between actions)
- Save screenshots
- Show you exactly where it fails

**Fix selectors based on screenshots and error messages.**

---

### Step 3: Update Navigation Helpers

**File:** `tests/e2e/conftest.py`
**Functions:** `navigate_to_tournament_checkin()`, `navigate_to_session_checkin()`

**Current code (generic):**
```python
def navigate_to_tournament_checkin(page: Page) -> None:
    try:
        page.click("text=Tournament Check-in")
    except:
        # Try alternatives...
```

**How to fix:**

1. **After logging in, inspect sidebar/navigation:**
   - Where is "Tournament Check-in" link?
   - What selector will click it?

2. **Update selector:**
   ```python
   # Examples:
   page.click("a:has-text('Tournament Check-in')")
   # OR
   page.click("[data-testid='sidebar'] >> text=Tournament")
   # OR
   page.get_by_role("link", name="Tournament Check-in").click()
   ```

3. **Verify navigation worked:**
   ```python
   # Update this to match tournament page
   page.wait_for_selector("text=Tournament Check-in, text=🏆", timeout=10000)
   ```

---

### Step 4: Run Individual Tests

**Start with simplest test:**

```bash
# Tournament branding test (doesn't require session data)
PYTHONPATH=. pytest tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentUIBranding::test_tournament_wizard_shows_tournament_icon -v --headed --slowmo 1000
```

**Watch it run:**
- See where it fails
- Update selectors
- Re-run until it passes

**Then try critical test:**
```bash
# 2-button test (requires tournament session with students)
PYTHONPATH=. pytest tests/e2e/tournament/test_tournament_checkin_e2e.py::TestTournamentCheckinE2E::test_tournament_shows_only_2_attendance_buttons -v --headed --slowmo 1000
```

---

### Step 5: Create Test Data

**Before running attendance tests, ensure:**

1. **Tournament semester exists:**
   - Go to Admin panel
   - Create tournament semester
   - Set status to READY_FOR_ENROLLMENT

2. **Tournament session created:**
   - Add tournament session to semester
   - Set `is_tournament_game = True`
   - Set capacity (e.g., 20)

3. **Students enrolled:**
   - Enroll at least 2 test students
   - Bookings should be CONFIRMED

4. **Instructor assigned:**
   - Assign instructor to tournament
   - Login with instructor credentials

**Or use SQL:**
```sql
-- Create tournament
INSERT INTO semesters (code, name, start_date, end_date, is_active, status, specialization_type, master_instructor_id)
VALUES ('TOURN-TEST', 'E2E Test Tournament', CURRENT_DATE + 7, CURRENT_DATE + 7, true, 'READY_FOR_ENROLLMENT', 'LFA_PLAYER_YOUTH', 2);

-- Create session
INSERT INTO sessions (title, date_start, date_end, session_type, capacity, is_tournament_game, game_type, semester_id, instructor_id)
VALUES ('Test Final', CURRENT_TIMESTAMP + INTERVAL '7 days', CURRENT_TIMESTAMP + INTERVAL '7 days 90 minutes', 'on_site', 20, true, 'Final', <semester_id>, 2);

-- Enroll students
INSERT INTO bookings (user_id, session_id, status)
VALUES
  (3, <session_id>, 'CONFIRMED'),
  (4, <session_id>, 'CONFIRMED');
```

---

## Common Selector Patterns

### Streamlit-Specific Selectors

**Text inputs:**
```python
# By data-testid (Streamlit auto-generated)
page.fill("[data-testid='stTextInput']", "value")

# By label (if using st.text_input with label)
page.fill("input:near(:text('Email'))", "value")

# By key (if set st.text_input(key='email'))
page.fill("[key='email']", "value")
```

**Buttons:**
```python
# By text
page.click("button:has-text('Login')")

# By data-testid
page.click("[data-testid='stButton']")

# By emoji + text
page.click("button:has-text('✅ Present')")
```

**Navigation:**
```python
# Sidebar links
page.click("[data-testid='stSidebarNav'] >> text=Tournament")

# Radio buttons
page.click("text=Tournament Check-in")
```

---

## Debugging Tips

### 1. Use Headed Mode
```bash
pytest tests/e2e/ --headed --slowmo 1000
```
- See exactly what Playwright is doing
- Slow motion helps spot errors

### 2. Take Screenshots
```python
# Add to test
page.screenshot(path="debug_screenshot.png", full_page=True)
```

### 3. Print Page Content
```python
# Add to test
print(page.content())  # Full HTML
print(page.text_content("body"))  # Visible text
```

### 4. Use Playwright Inspector
```bash
PWDEBUG=1 pytest tests/e2e/test_login_manual.py
```
- Opens Playwright inspector
- Step through actions
- Try selectors interactively

### 5. Check Selector in Browser Console
```javascript
// In browser DevTools console:
document.querySelectorAll('button:has-text("Present")')
```

---

## Troubleshooting Checklist

- [ ] Streamlit app is running (`curl http://localhost:8501` returns 200)
- [ ] Test credentials exist in database
- [ ] Login selectors match actual UI
- [ ] Post-login verification selector is correct
- [ ] Navigation selectors are accurate
- [ ] Test data exists (tournament + session + students)
- [ ] Environment variables set (if using custom creds)

---

## Quick Fix Template

**If test fails with "TimeoutError: waiting for selector":**

1. **Run with headed + slowmo:**
   ```bash
   pytest tests/e2e/YOUR_TEST.py -v --headed --slowmo 1000
   ```

2. **When it fails, note:**
   - What page is it on?
   - What selector is it looking for?
   - Is that element visible?

3. **Inspect element in browser:**
   - Right-click element → Inspect
   - Copy selector

4. **Update test file:**
   ```python
   # Change from:
   page.click("text=Old Selector")

   # To:
   page.click("YOUR_ACTUAL_SELECTOR")
   ```

5. **Re-run test**

---

## Success Criteria

Once you've completed setup:

✅ Login test passes
✅ Navigation to tournament page works
✅ At least 1 critical test passes (2-button or 4-button)
✅ Screenshots are captured
✅ No timeout errors

---

## Next Steps After Setup

1. ✅ All 17 E2E tests pass
2. ✅ Screenshots captured in `docs/screenshots/`
3. ✅ Add to CI/CD (GitHub Actions)
4. ✅ Run on every PR

---

## Estimated Time

- **Login selector fix:** 10-15 min
- **Navigation fix:** 10-15 min
- **Test data creation:** 5-10 min
- **Run + verify tests:** 10-20 min

**Total:** 30-60 minutes

---

## Need Help?

If stuck:
1. Check Playwright docs: https://playwright.dev/python/
2. Use `PWDEBUG=1` for interactive debugging
3. Share screenshot + error message

---

**Status:** Ready to customize selectors and run tests! 🚀
