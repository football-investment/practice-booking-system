# Cypress E2E Tests — LFA Education Center

Isolated Cypress test suite for the LFA Education Center Streamlit frontend.

**Separation of concerns:**
| Folder | Tool | Language | Scope |
|---|---|---|---|
| `tests_e2e/` | Playwright (pytest) | Python | Backend-heavy lifecycle, DB-level |
| `tests_cypress/` | Cypress | JavaScript | Frontend UI, user flows, error states |

---

## Prerequisites

- Node.js ≥ 18
- Streamlit app running on `http://localhost:8501`
- FastAPI backend running on `http://localhost:8000`

```bash
# Install Cypress
cd tests_cypress
npm install
```

---

## Running Tests

```bash
# Interactive mode (Cypress app, headed)
npm run cy:open

# Headless CI run (all specs)
npm run cy:run:ci

# Run by category
npm run cy:run:auth         # Login, registration
npm run cy:run:admin        # Admin dashboard, tournament manager/monitor
npm run cy:run:instructor   # Instructor dashboard tabs
npm run cy:run:player       # Player dashboard, hub, credits
npm run cy:run:errors       # HTTP 409, 401, 403 error states

# Smoke tests only (@smoke tagged)
npm run cy:run:smoke
```

---

## Environment Variables

Override any default via `CYPRESS_<KEY>=value` or a `cypress.env.json` file
(gitignored):

```json
{
  "adminEmail":         "admin@lfa.com",
  "adminPassword":      "password123",
  "instructorEmail":    "instructor@lfa.com",
  "instructorPassword": "password123",
  "playerEmail":        "junior.intern@lfa.com",
  "playerPassword":     "password123",
  "apiUrl":             "http://localhost:8000"
}
```

```bash
# Custom base URL (e.g. staging)
CYPRESS_BASE_URL=https://staging.lfa.com npm run cy:run:ci
```

---

## Structure

```
tests_cypress/
├── cypress.config.js          # Timeouts, baseUrl, env defaults
├── package.json               # Cypress + @cypress/grep
├── .gitignore                 # node_modules, screenshots, videos
│
└── cypress/
    ├── e2e/
    │   ├── auth/
    │   │   ├── login.cy.js            # Login / logout flows, invalid creds
    │   │   └── registration.cy.js     # Registration form, 409 duplicate email
    │   ├── admin/
    │   │   ├── dashboard_navigation.cy.js   # 9 tabs, sidebar, access control
    │   │   ├── tournament_manager.cy.js     # OPS Wizard steps, form validation
    │   │   └── tournament_monitor.cy.js     # Monitor page, auto-refresh
    │   ├── instructor/
    │   │   └── dashboard.cy.js        # 7 tabs, sidebar, today/applications
    │   ├── player/
    │   │   ├── dashboard.cy.js        # Player dashboard, onboarding redirect
    │   │   ├── specialization_hub.cy.js  # Unlock/Enter/Learn More flows
    │   │   └── credits.cy.js          # Balance metric, transaction history
    │   └── error_states/
    │       ├── http_409_conflict.cy.js   # Double enroll, booking, result, finalize
    │       └── unauthorized.cy.js        # 401 login, 403 RBAC, 422 validation
    │
    ├── fixtures/
    │   ├── users.json             # Test credentials (admin, instructor, player)
    │   └── api_responses.json     # Canned API error/success responses
    │
    └── support/
        ├── commands.js            # Custom commands (login, waitForStreamlit, …)
        └── e2e.js                 # Global hooks, @cypress/grep, noise suppression
```

---

## Custom Commands

| Command | Description |
|---|---|
| `cy.waitForStreamlit()` | Wait for Streamlit to finish rendering (spinner gone) |
| `cy.login(email, password)` | Fill and submit the login form |
| `cy.loginAsAdmin()` | Login with admin credentials from env |
| `cy.loginAsInstructor()` | Login with instructor credentials from env |
| `cy.loginAsPlayer()` | Login with player credentials from env |
| `cy.logout()` | Click the sidebar Logout button |
| `cy.navigateTo(path)` | `cy.visit(path)` + `waitForStreamlit()` |
| `cy.clickSidebarButton(text)` | Click a button in `[data-testid="stSidebar"]` |
| `cy.clickAdminTab(label)` | Click an Admin Dashboard tab button |
| `cy.fillInput(label, value)` | Fill a Streamlit text input by its label |
| `cy.assertAuthenticated()` | Assert sidebar + Logout button visible |
| `cy.assertUnauthenticated()` | Assert Login button visible |
| `cy.assertAlert(text)` | Assert a Streamlit alert contains text |
| `cy.assertMetric(label, value)` | Assert a Streamlit metric value |
| `cy.stub409Enrollment(apiUrl)` | Intercept enrollment POST with 409 |
| `cy.stub401Login(apiUrl)` | Intercept login POST with 401 |

---

## Test Tags (@cypress/grep)

| Tag | Description |
|---|---|
| `@smoke` | Fast regression — must pass on every deploy |

```bash
# Run smoke tests only
CYPRESS_grepTags=@smoke npm run cy:run:ci
```

---

## Streamlit DOM Selectors Reference

Streamlit renders a React app with stable `data-testid` attributes:

| Element | Selector |
|---|---|
| App wrapper | `[data-testid="stApp"]` |
| Sidebar | `[data-testid="stSidebar"]` |
| Button wrapper | `[data-testid="stButton"]` |
| Text input wrapper | `[data-testid="stTextInput"]` |
| Password input | `[data-testid="stTextInput"] input[type="password"]` |
| Select/combobox | `[data-testid="stSelectbox"]` |
| Tabs container | `[data-testid="stTabs"]` |
| Individual tab | `[data-testid="stTab"]` |
| Alert/toast | `[data-testid="stAlert"]` |
| Metric card | `[data-testid="stMetric"]` |
| Metric value | `[data-testid="stMetricValue"]` |
| Spinner | `[data-testid="stSpinner"]` |
| Checkbox | `[data-testid="stCheckbox"]` |

---

## CI Integration Example

```yaml
# .github/workflows/cypress-e2e.yml
name: Cypress E2E

on: [push, pull_request]

jobs:
  cypress:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Start backend + Streamlit
        run: |
          # Start FastAPI
          uvicorn app.main:app --port 8000 &
          # Start Streamlit
          streamlit run streamlit_app/🏠_Home.py --server.port 8501 &
          sleep 10  # wait for startup

      - name: Install Cypress
        run: cd tests_cypress && npm ci

      - name: Run smoke tests
        run: cd tests_cypress && npm run cy:run:smoke
        env:
          CYPRESS_BASE_URL: http://localhost:8501
          CYPRESS_API_URL:  http://localhost:8000

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: cypress-screenshots
          path: tests_cypress/cypress/screenshots/
```

---

## Playwright Coexistence

The `tests_e2e/` folder uses **Playwright (Python + pytest)** for:
- Full lifecycle tests requiring DB state manipulation
- Backend concurrency race condition verification
- Large-scale (1024-player) simulation tests

The `tests_cypress/` folder uses **Cypress (JavaScript)** for:
- Frontend UI rendering and navigation
- Form interaction and validation
- Error state display (HTTP 4xx)
- Role-based access control visual verification

The two suites are entirely independent and can run in parallel in CI.
