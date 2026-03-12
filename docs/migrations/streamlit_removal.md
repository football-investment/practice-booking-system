# Streamlit Removal — Migration Record

**Sprint**: 59h
**Date**: 2026-03-12
**Status**: Complete ✅

---

## Why Streamlit Was Removed

Streamlit was the original frontend framework, chosen for rapid prototyping during early sprints.
Over sprints 55–59g it was fully superseded by a production-grade HTML/FastAPI frontend:

- **Maintainability**: Streamlit's session-state model made complex multi-role flows brittle.
  FastAPI + Jinja2 templates align with standard web development practices.
- **Performance**: Streamlit re-runs the entire script on every interaction; Jinja2 renders only
  what is requested, with no Python overhead per user action.
- **Single port**: Streamlit required a second process on :8501; the HTML frontend is served by
  the existing FastAPI process on :8000, simplifying deployment and proxy configuration.
- **Testability**: Streamlit UIs were tested via Playwright with fragile CSS-selector-based
  selectors. The HTML frontend uses standard Cypress DOM-driven specs with stable `data-testid`
  attributes.

---

## What Replaced It

The HTML frontend is a FastAPI + Jinja2 template application, fully colocated in the existing
`app/` package:

| Layer | Location | Notes |
|---|---|---|
| Routes | `app/api/web_routes/` | 14 route modules, cookie-based auth |
| Templates | `app/templates/` | Jinja2, extends `base.html` |
| Admin panel | `app/api/web_routes/admin.py` | 37+ routes, 12 admin pages |
| Cypress E2E | `cypress/cypress/e2e/web/` | 198 specs, 100% passing |
| Integration tests | `tests/integration/web_flows/` | 88 tests covering all key flows |

### Feature parity achieved (Sprints 55–59g)

| Streamlit page | HTML route |
|---|---|
| `🏠_Home.py` (registration) | `GET/POST /register` |
| `Admin_Dashboard.py` | `GET /admin/*` (12 pages) |
| `Tournament_Monitor.py` | `GET /tournaments` |
| `Tournament_Manager.py` | `GET/POST /admin/tournaments` |
| `Instructor_Dashboard.py` | `GET /instructor/*` |
| All student pages | `GET /sessions`, `/credits`, `/progress`, etc. |

---

## Where the Archive Lives

The Streamlit source code is preserved in git history and accessible at:

```
archive/
├── streamlit_app/           # 231 files — full Streamlit multi-page app
├── streamlit_components/    # 18 files — shared UI components
└── streamlit_requirements.txt
```

These files are excluded from pytest (`norecursedirs = archive`) and from the production
`_PROD_PATTERN` in the pre-push hook. They will not be imported or executed by any active code.

To browse the archive locally:
```bash
ls archive/streamlit_app/pages/
```

To recover a specific file from git history (if the archive is later removed):
```bash
git log --all --oneline -- streamlit_app/<path>
git show <commit>:streamlit_app/<path>
```

---

## What Was Deleted

| Category | Files removed |
|---|---|
| Source | `streamlit_app/` (231), `streamlit_components/` (18), `streamlit_requirements.txt` → moved to `archive/` |
| Tests | `tests/e2e_frontend/` (35), `tests/e2e_legacy/` (35), 5 individual Streamlit test files |
| Scripts | `scripts/deployment/run_streamlit.sh`, `scripts/startup/start_streamlit_*.sh`, 6 `scripts/admin_tools/streamlit_*.py`, 7 `scripts/dashboards/`, `scripts/helpers/sandbox_helpers.py` |
| Cypress specs | `cypress/cypress/e2e/admin|auth|error_states|instructor|player|student|system/` (Streamlit-targeting specs) |

---

## CI Changes

| Workflow | Action | Reason |
|---|---|---|
| `cypress-e2e.yml` | All jobs disabled (`if: false`) | Ran Streamlit Cypress specs |
| `cypress-tests.yml` | All jobs disabled | Ran deleted Streamlit specs |
| `e2e-fast-suite.yml` | All jobs disabled | Ran `test_champion_badge_regression.py` (Playwright + Streamlit) |
| `e2e-live-suite.yml` | All jobs disabled | Streamlit live suite |
| `e2e-scale-suite.yml` | All jobs disabled | Streamlit scale suite |
| `e2e-comprehensive.yml` | All jobs disabled | Ran Streamlit Cypress specs |
| `e2e-wizard-coverage.yml` | 4/6 jobs disabled; `api-boundary` kept | 127 pure API tests preserved |
| `e2e-integration-critical.yml` | Streamlit startup step removed | Tests are pure API, no Streamlit needed |

The 3 **required CI checks** (`api-smoke-tests.yml`, `skill-weight-regression.yml`,
`test-baseline-check.yml`) had zero Streamlit references and were not modified.

---

## Verification

```bash
# No active Streamlit imports in app or tests
grep -r "import streamlit\|from streamlit\|streamlit_app\." \
  tests/unit/ tests/integration/ tests/e2e/ app/ --include="*.py"
# → no output (clean)

# FastAPI starts without Streamlit
uvicorn app.main:app --port 8000
curl http://localhost:8000/health
# → {"status":"healthy"}

# Full test suite
pytest tests/unit/ tests/integration/ -q
# → 8884 passed, 1 xfailed
```
