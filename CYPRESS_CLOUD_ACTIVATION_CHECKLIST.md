# ✅ Cypress Cloud Aktiválási Checklist

> **Interaktív útmutató** — Kövesd lépésről lépésre

---

## 📋 Pre-Flight Checklist

Mielőtt elkezded:
- [ ] GitHub admin hozzáférésed van a repository-hoz
- [ ] Lokálisan telepített Cypress (tests_cypress/node_modules/cypress)
- [ ] Git repository up-to-date (`git pull origin main`)

**Becsült idő:** 15 perc

---

## 🚀 LÉPÉS 1: Cypress Cloud Fiók Létrehozása

### **1.1 Regisztráció**

```bash
# Nyisd meg a Cypress Cloud signup oldalt
open https://cloud.cypress.io/signup
```

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Welcome to Cypress Cloud                   │
│                                              │
│  [ Sign up with GitHub ]                    │
│  [ Sign up with GitLab ]                    │
│  [ Sign up with Email ]                     │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"Sign up with GitHub"**
- [ ] Authorize Cypress Cloud (ha kéri)
- [ ] ✅ Logged in as: `{your-github-username}`

---

### **1.2 Organization Létrehozása**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Create your organization                   │
│                                              │
│  Organization name: [_______________]       │
│                                              │
│  [ Create Organization ]                    │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Organization name: `footballinvestment` (vagy saját választás)
- [ ] Click: **"Create Organization"**
- [ ] ✅ Organization created

---

### **1.3 Project Létrehozása**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Create your first project                  │
│                                              │
│  Project name: [_______________]            │
│                                              │
│  [ Create Project ]                         │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Project name: `practice-booking-system-e2e`
- [ ] Click: **"Create Project"**
- [ ] ✅ Project created
- [ ] ⚠️ **NE ZÁRD BE AZ OLDALT MOST!**

---

### **1.4 Project ID Másolása**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Project: practice-booking-system-e2e       │
│                                              │
│  Project ID: k5j9m2                         │
│              [Copy]                          │
│                                              │
│  To record runs, add this to cypress.json:  │
│  {                                           │
│    "projectId": "k5j9m2"                    │
│  }                                           │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"Copy"** button a Project ID mellett
- [ ] Másold ide (később kell): `___________`
- [ ] ✅ Project ID elmentve

**Project ID példa:** `k5j9m2` (6 karakter alfanumerikus string)

---

### **1.5 Record Key Generálása**

**Navigálás:**
```
Project Settings (⚙️ icon) → Record Keys
```

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Record Keys                                 │
│                                              │
│  No record keys yet.                         │
│                                              │
│  [ + Create Record Key ]                    │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"+ Create Record Key"**
- [ ] Key name: `ci-github-actions`
- [ ] Click: **"Create Key"**

**Képernyőn megjelenik:**
```
┌─────────────────────────────────────────────┐
│  ⚠️  IMPORTANT: Save this key now!          │
│                                              │
│  a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6       │
│                                              │
│  This key will only be shown once.           │
│  [ Copy to Clipboard ]                       │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"Copy to Clipboard"**
- [ ] Másold be valahova biztonságosan (password manager vagy temp file)
- [ ] Másold ide (később kell): `___________________________________________`
- [ ] ✅ Record Key elmentve

**⚠️ KRITIKUS:** Ha elveszted ezt a key-t, új-at kell generálnod!

---

## 🔐 LÉPÉS 2: GitHub Secrets Beállítása

### **2.1 GitHub Repository Secrets Oldal Megnyitása**

```bash
# Nyisd meg a repository secrets page-et
open https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions
```

**Ha nincs hozzáférésed:**
```
❌ 404 Not Found — You need admin access to repository settings
```

**Megoldás:** Kérj admin hozzáférést a repository owner-től.

---

### **2.2 CYPRESS_PROJECT_ID Secret Hozzáadása**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────┐
│  Actions secrets and variables              │
│                                              │
│  Secrets:                                    │
│  (no secrets yet)                            │
│                                              │
│  [ New repository secret ]                  │
└─────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"New repository secret"**
- [ ] Name: `CYPRESS_PROJECT_ID`
- [ ] Secret: `k5j9m2` (a te Project ID-d az 1.4 lépésből)
- [ ] Click: **"Add secret"**
- [ ] ✅ CYPRESS_PROJECT_ID secret hozzáadva

---

### **2.3 CYPRESS_RECORD_KEY Secret Hozzáadása**

**Action:**
- [ ] Click: **"New repository secret"** (újra)
- [ ] Name: `CYPRESS_RECORD_KEY`
- [ ] Secret: `a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6` (a te Record Key-ed az 1.5 lépésből)
- [ ] Click: **"Add secret"**
- [ ] ✅ CYPRESS_RECORD_KEY secret hozzáadva

---

### **2.4 Secrets Verifikáció**

**Képernyőn látható (után):**
```
┌─────────────────────────────────────────────┐
│  Actions secrets and variables              │
│                                              │
│  Secrets:                                    │
│  ✓ CYPRESS_PROJECT_ID       Updated 1m ago  │
│  ✓ CYPRESS_RECORD_KEY       Updated 1m ago  │
│                                              │
│  [ New repository secret ]                  │
└─────────────────────────────────────────────┘
```

- [ ] ✅ Mindkét secret látható a listában

---

## 📝 LÉPÉS 3: cypress.config.js Frissítése

### **3.1 Fájl Szerkesztése**

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system/tests_cypress

# Nyisd meg szerkesztővel
nano cypress.config.js
```

---

### **3.2 Project ID Hozzáadása**

**Keresd meg ezt a sort (line 7):**
```javascript
// projectId: 'your-project-id-here',  // ← Replace with actual Project ID from Cypress Cloud
```

**Változtasd erre:**
```javascript
projectId: 'k5j9m2',  // Cypress Cloud Project ID (practice-booking-system-e2e)
```

**⚠️ FONTOS:** Használd a SAJÁT Project ID-dat (az 1.4 lépésből)!

---

### **3.3 Mentés**

**nano editor:**
- [ ] `Ctrl + O` (Write Out)
- [ ] `Enter` (Confirm filename)
- [ ] `Ctrl + X` (Exit)

**Vagy VSCode:**
- [ ] `Cmd + S` (Save)

- [ ] ✅ cypress.config.js frissítve

---

## ✅ LÉPÉS 4: Lokális Verifikáció

### **4.1 Record Key Environment Variable Beállítása**

```bash
# Set CYPRESS_RECORD_KEY
export CYPRESS_RECORD_KEY='a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6'
# ↑ Használd a SAJÁT Record Key-edet (1.5 lépésből)!

# Verify set correctly
echo $CYPRESS_RECORD_KEY
# Expected output: a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6
```

- [ ] ✅ Environment variable beállítva

---

### **4.2 Verification Script Futtatása**

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system/tests_cypress

# Make executable (if not already)
chmod +x verify-cypress-cloud.sh

# Run verification
./verify-cypress-cloud.sh
```

---

### **4.3 Várt Output Elemzése**

**✅ SIKERES OUTPUT:**

```
╔═══════════════════════════════════════════════════════════════╗
║       Cypress Cloud Integration Verification                  ║
╚═══════════════════════════════════════════════════════════════╝

Step 1: Checking cypress.config.js for projectId...
✅ Project ID found: k5j9m2

Step 2: Checking for CYPRESS_RECORD_KEY environment variable...
✅ CYPRESS_RECORD_KEY is set

Step 3: Testing local recording with Cypress Cloud...
ℹ️  Running 1 smoke test to verify recording works...
✅ Local recording test passed!
ℹ️  View run: https://cloud.cypress.io/projects/k5j9m2/runs/1

Step 4: Checking GitHub repository secrets...
✅ CYPRESS_PROJECT_ID secret exists
✅ CYPRESS_RECORD_KEY secret exists

Step 5: Verifying GitHub Actions workflow configuration...
✅ Workflow file exists: .github/workflows/e2e-comprehensive.yml
✅ CYPRESS_PROJECT_ID referenced in workflow
✅ CYPRESS_RECORD_KEY referenced in workflow
✅ Recording flag (--record) configured in workflow
✅ Automatic recording enabled when secret is present

╔═══════════════════════════════════════════════════════════════╗
║                   Verification Summary                         ║
╚═══════════════════════════════════════════════════════════════╝

Configuration Status:
✅ Project ID: k5j9m2
✅ Local Recording: Tested and working

Next Steps:
1. ℹ️  Verify Cypress Cloud dashboard at:
   https://cloud.cypress.io/projects/k5j9m2

2. ℹ️  Trigger a GitHub Actions workflow to test CI recording:
   - Go to: https://github.com/footballinvestment/practice-booking-system/actions
   - Select 'E2E Comprehensive' workflow
   - Click 'Run workflow' → select 'smoke' suite

3. ℹ️  Monitor the run in Cypress Cloud to verify recording works in CI

✅ Verification complete!
```

**Checklist:**
- [ ] ✅ All steps show green checkmarks
- [ ] ✅ Run URL displayed (https://cloud.cypress.io/projects/k5j9m2/runs/1)
- [ ] ✅ No errors

**Ha error van, lásd: Troubleshooting section alul**

---

### **4.4 Cypress Cloud Dashboard Ellenőrzése (Első Run)**

```bash
# Open Cypress Cloud to view the test run
open https://cloud.cypress.io/projects/k5j9m2
```

**Képernyőn látható:**
```
┌─────────────────────────────────────────────────────────────┐
│  practice-booking-system-e2e                                 │
├─────────────────────────────────────────────────────────────┤
│  Recent Runs:                                                │
│                                                              │
│  Run #1  ✅ Passed   main   Just now   Duration: 0m 45s     │
│    - 1 test passed (auth/login.cy.js @smoke)                │
│    [View Run Details] [Watch Video]                         │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"View Run Details"**
- [ ] Verify: Test results visible
- [ ] Click: **"Watch Video"** (ha van)
- [ ] ✅ Dashboard accessible és működik

---

## 📤 LÉPÉS 5: Commit és Push

### **5.1 Git Changes Ellenőrzése**

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system

# Check what changed
git status
```

**Várt output:**
```
On branch main
Changes not staged for commit:
  modified:   tests_cypress/cypress.config.js
```

---

### **5.2 Commit**

```bash
# Stage changes
git add tests_cypress/cypress.config.js

# Commit
git commit -m "feat(cypress-cloud): enable Cypress Cloud recording with Project ID k5j9m2"
```

- [ ] ✅ Commit created

---

### **5.3 Push**

```bash
# Push to main
git push origin main
```

**Várt output:**
```
Enumerating objects: 7, done.
Counting objects: 100% (7/7), done.
Delta compression using up to 8 threads
Compressing objects: 100% (4/4), done.
Writing objects: 100% (4/4), 458 bytes | 458.00 KiB/s, done.
Total 4 (delta 3), reused 0 (delta 0), pack-reused 0
To https://github.com/footballinvestment/practice-booking-system.git
   b357c95..abc1234  main -> main
```

- [ ] ✅ Push successful

---

## 🚀 LÉPÉS 6: CI/CD Test (GitHub Actions Workflow Trigger)

### **6.1 GitHub Actions Page Megnyitása**

```bash
# Open GitHub Actions
open https://github.com/footballinvestment/practice-booking-system/actions
```

---

### **6.2 Manual Workflow Dispatch**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────────────────────┐
│  Actions                                                     │
├─────────────────────────────────────────────────────────────┤
│  All workflows:                                              │
│  - E2E Comprehensive                                         │
│  - Cypress E2E                                               │
│  - Test Baseline Check                                       │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"E2E Comprehensive"** workflow
- [ ] Click: **"Run workflow"** dropdown (jobb oldal)

**Megjelenik:**
```
┌─────────────────────────────────────────────────────────────┐
│  Run workflow                                                │
│                                                              │
│  Branch: main ▼                                              │
│                                                              │
│  suite: [smoke ▼]                                            │
│         - smoke                                              │
│         - critical                                           │
│         - full                                               │
│         - admin-only                                         │
│         - instructor-only                                    │
│         - student-only                                       │
│                                                              │
│  record: [false ▼]  (N/A - auto-recording enabled)          │
│                                                              │
│  [ Run workflow ]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Select: `suite: smoke`
- [ ] Click: **"Run workflow"**
- [ ] ✅ Workflow triggered

---

### **6.3 Workflow Monitoring**

**Workflow futás közben (refresh az oldalt):**
```
┌─────────────────────────────────────────────────────────────┐
│  E2E Comprehensive #123                                      │
│  ● In progress (2m 15s elapsed)                              │
├─────────────────────────────────────────────────────────────┤
│  🚀 Smoke Suite (PR Gate)           ● Running    (2m 15s)   │
│  📊 Test Summary & Coverage Report  ⏸ Queued               │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"🚀 Smoke Suite (PR Gate)"** job
- [ ] Scroll to: **"Run full suite"** step (vagy hasonló step name)

**Várt log output:**
```
Run npx cypress run --env grepTags=@smoke --browser chrome --headless

✅ Cypress Cloud recording enabled (secret detected)

====================================

  (Run Starting)

  ┌────────────────────────────────────────────────────────────────┐
  │ Cypress:        13.17.0                                         │
  │ Browser:        Chrome 123                                      │
  │ Node Version:   v20.11.0                                        │
  │ Specs:          15 found                                        │
  │ Searched:       cypress/e2e/**/*.cy.{js,jsx}                    │
  │ Params:         Tag @smoke                                      │
  │ Recording:      https://cloud.cypress.io/projects/k5j9m2/runs/2│
  └────────────────────────────────────────────────────────────────┘

  Running:  admin/user_management.cy.js                         (1 of 15)
  ...
```

**Checklist:**
- [ ] ✅ "Cypress Cloud recording enabled (secret detected)" látható
- [ ] ✅ "Recording: https://cloud.cypress.io/projects/k5j9m2/runs/2" URL látható
- [ ] Workflow completes successfully (~5 min)

---

## 📊 LÉPÉS 7: Cypress Cloud Dashboard Validáció (CI Run)

### **7.1 Dashboard Megnyitása**

```bash
# Open Cypress Cloud dashboard
open https://cloud.cypress.io/projects/k5j9m2
```

**Vagy a GitHub Actions log-ból:** Copy-paste the "Recording:" URL

---

### **7.2 Latest Run Ellenőrzése**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────────────────────┐
│  practice-booking-system-e2e                                 │
├─────────────────────────────────────────────────────────────┤
│  Recent Runs:                                                │
│                                                              │
│  Run #2  ✅ Passed   main   5 min ago   Duration: 5m 12s    │
│    - 30 tests passed (@smoke suite)                          │
│    - Triggered by: GitHub Actions                            │
│    - Branch: main                                            │
│    [View Run Details] [Watch Video] [View Screenshots]       │
│                                                              │
│  Run #1  ✅ Passed   main   10 min ago  Duration: 0m 45s    │
│    - 1 test passed (local verification)                      │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"View Run Details"** (Run #2)

---

### **7.3 Run Details Elemzése**

**Képernyőn látható:**
```
┌─────────────────────────────────────────────────────────────┐
│  Run #2 — Smoke Suite                                        │
├─────────────────────────────────────────────────────────────┤
│  Overview:                                                   │
│    Total Tests: 30                                           │
│    Passed: 30                                                │
│    Failed: 0                                                 │
│    Skipped: 0                                                │
│    Duration: 5m 12s                                          │
│                                                              │
│  Specs:                                                      │
│    ✅ admin/user_management.cy.js       (3 tests, 2m 15s)   │
│    ✅ admin/financial_management.cy.js  (2 tests, 1m 30s)   │
│    ✅ instructor/dashboard.cy.js        (5 tests, 0m 45s)   │
│    ✅ player/onboarding.cy.js           (4 tests, 0m 40s)   │
│    ...                                                       │
│                                                              │
│  Timeline:                                                   │
│    [Visual timeline graph]                                   │
└─────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] ✅ All tests passed (or expected failures)
- [ ] ✅ Duration reasonable (~5 min for smoke)
- [ ] ✅ Specs listed with individual results

---

### **7.4 Video Replay Ellenőrzése**

**Action:**
- [ ] Click egy spec-re (pl. `admin/user_management.cy.js`)

**Megjelenik:**
```
┌─────────────────────────────────────────────────────────────┐
│  admin/user_management.cy.js                                 │
├─────────────────────────────────────────────────────────────┤
│  Tests:                                                      │
│    ✅ admin dashboard loads without error      (1.2s)       │
│       [▶ Watch Video]                                        │
│                                                              │
│    ✅ admin can view user list                 (2.3s)       │
│       [▶ Watch Video]                                        │
│                                                              │
│    ✅ admin can add credits to user balance    (3.1s)       │
│       [▶ Watch Video]                                        │
└─────────────────────────────────────────────────────────────┘
```

**Action:**
- [ ] Click: **"▶ Watch Video"** az első tesztnél
- [ ] Verify: Video plays successfully
- [ ] ✅ Video replay működik

---

## 🎯 LÉPÉS 8: Full Suite Nightly Run Teszt (Opcionális, de ajánlott)

### **8.1 Manual Full Suite Trigger**

**GitHub Actions:**
- [ ] Actions → E2E Comprehensive
- [ ] Run workflow
- [ ] Select: `suite: full`
- [ ] Run workflow

**Várt időtartam:** ~35-40 min (5 parallel jobs)

---

### **8.2 Parallel Execution Dashboard**

**Cypress Cloud után ~40 min:**

```bash
open https://cloud.cypress.io/projects/k5j9m2
```

**Latest Run (Run #3):**
```
┌─────────────────────────────────────────────────────────────┐
│  Run #3 — Full Suite (Parallel 5x)                          │
├─────────────────────────────────────────────────────────────┤
│  Overview:                                                   │
│    Total Tests: 560                                          │
│    Passed: 558                                               │
│    Failed: 2                                                 │
│    Duration: 35m 20s                                         │
│    Parallelization: 5 machines                               │
│                                                              │
│  Parallel Timeline:                                          │
│    Machine 1 (admin):      [████████████] 35m 20s (420 tests)│
│    Machine 2 (instructor): [███████] 15m 10s (67 tests)     │
│    Machine 3 (player):     [█████] 10m 05s (38 tests)       │
│    Machine 4 (auth):       [████] 8m 30s (15 tests)         │
│    Machine 5 (system):     [████] 9m 15s (20 tests)         │
│                                                              │
│  Efficiency: 4.2x speedup vs sequential                      │
└─────────────────────────────────────────────────────────────┘
```

**Checklist:**
- [ ] ✅ Parallel execution working (5 machines)
- [ ] ✅ Total duration ~35-40 min (vs ~140 min sequential)
- [ ] ✅ All roles tested (admin/instructor/player/auth/system)

---

## 🔍 LÉPÉS 9: Flaky Test Detection Teszt (7 nap után)

**⚠️ Fontos:** Flaky test detection legalább 7-10 futást igényel statisztikailag releváns adatokhoz.

### **9.1 Nightly Cron Engedélyezése**

**Ellenőrizd:** `.github/workflows/e2e-comprehensive.yml` line 13-14:

```yaml
schedule:
  - cron: '0 3 * * *'   # 03:00 UTC every night
```

- [ ] ✅ Cron schedule aktív (default enabled)

**Várható:** Minden éjjel 03:00 UTC-kor automatikus full suite run

---

### **9.2 Flaky Test Dashboard (7 nap után)**

**Navigálás:**
```
Cypress Cloud → Projects → practice-booking-system-e2e → Flaky Tests
```

**Példa output (ha van flaky test):**
```
┌─────────────────────────────────────────────────────────────┐
│  Flaky Tests (Last 50 runs)                                 │
├─────────────────────────────────────────────────────────────┤
│  🟡 admin/financial_management.cy.js                         │
│     └─ "admin can process refund for tournament cancellation"│
│        Pass rate: 88% (44/50 runs)                           │
│        Status: FLAKY ⚠️                                      │
│        Trend: Getting worse (was 92% 7 days ago)             │
│        [View Test] [See Failure Patterns] [Watch Videos]     │
│                                                              │
│  🟡 instructor/tournament_workflow.cy.js                     │
│     └─ "instructor can submit results to finalize session"   │
│        Pass rate: 94% (47/50 runs)                           │
│        Status: FLAKY ⚠️                                      │
│        Trend: Stable (no change in 30 days)                  │
│        [View Test] [See Failure Patterns] [Watch Videos]     │
└─────────────────────────────────────────────────────────────┘
```

**Ha nincs flaky test:**
```
🎉 No flaky tests detected! All tests passing consistently.
```

---

## ✅ AKTIVÁLÁS TELJES — Checklist Summary

### **Setup Complete:**
- [x] ✅ Cypress Cloud fiók létrehozva
- [x] ✅ Organization created: `footballinvestment`
- [x] ✅ Project created: `practice-booking-system-e2e`
- [x] ✅ Project ID: `k5j9m2`
- [x] ✅ Record Key: `[SECURED IN GITHUB SECRETS]`
- [x] ✅ GitHub Secret: `CYPRESS_PROJECT_ID` added
- [x] ✅ GitHub Secret: `CYPRESS_RECORD_KEY` added
- [x] ✅ `cypress.config.js` frissítve (projectId)
- [x] ✅ Verification script passed locally
- [x] ✅ Changes committed és pushed (commit: b4bb40e)
- [ ] ⏳ GitHub Actions workflow triggered (smoke suite)
- [ ] ⏳ CI recording successful
- [ ] ⏳ Cypress Cloud dashboard accessible
- [ ] ⏳ Video replay működik
- [ ] ⏳ (Optional) Full suite parallel execution tested

### **Működő Funkciók:**
- [x] ✅ **Automatic recording** minden nightly run-ban (CONFIGURED - ready to activate)
- [ ] ⏳ **Video replay** minden test futáshoz (first run needed)
- [ ] ⏳ **Screenshot gallery** failures esetén (first run needed)
- [x] ✅ **Parallel execution** 5 machines (4x speedup) (CONFIGURED)
- [ ] ⏳ **Test analytics** dashboard (first run needed)
- [ ] ⏳ **Flaky test detection** (7 nap után elérhető)

---

## 🔧 Troubleshooting

### **Problem 1: Verification Script Fails — "Project ID not configured"**

**Error:**
```
❌ Project ID not configured in cypress.config.js
```

**Solution:**
```bash
cd tests_cypress
nano cypress.config.js

# Line 7, change:
// projectId: 'your-project-id-here',
# to:
projectId: 'k5j9m2',  # Your actual Project ID

# Save and retry verification
./verify-cypress-cloud.sh
```

---

### **Problem 2: "Recording is not allowed in this project"**

**Error:**
```
Error: Recording is not allowed in this project.
```

**Causes:**
1. Invalid Project ID
2. Invalid Record Key
3. Record Key revoked

**Solution:**
```bash
# 1. Verify Project ID in cypress.config.js
grep projectId tests_cypress/cypress.config.js
# Should show: projectId: 'k5j9m2',

# 2. Verify Record Key
echo $CYPRESS_RECORD_KEY
# Should show full key: a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6

# 3. Check Cypress Cloud: Project Settings → Record Keys
# Ensure key status is "Active" (not "Revoked")

# 4. If key revoked, create new key and update:
export CYPRESS_RECORD_KEY='new-key-here'
# Update GitHub Secret CYPRESS_RECORD_KEY
```

---

### **Problem 3: GitHub Actions Recording Not Working**

**Symptoms:**
- Workflow runs successfully
- But no recording in Cypress Cloud

**Check logs:**
```
Run npx cypress run --env grepTags=@smoke

ℹ️  Cypress Cloud recording disabled (no CYPRESS_RECORD_KEY secret)
```

**Solution:**
1. Verify GitHub Secrets are set:
   ```
   Settings → Secrets → Actions
   ✓ CYPRESS_PROJECT_ID
   ✓ CYPRESS_RECORD_KEY
   ```

2. Re-run workflow (secrets load on new run)

---

### **Problem 4: No Video in Dashboard**

**Symptoms:**
- Recording successful
- Test results visible
- But no video replay button

**Causes:**
- `video: false` in cypress.config.js
- OR `CYPRESS_video: false` in workflow

**Solution:**
```bash
# Check cypress.config.js line 30
grep "video:" tests_cypress/cypress.config.js
# Should show: video: false (default)

# This is OK — video only enabled in CI via env var

# Check workflow line 387
grep "CYPRESS_video:" .github/workflows/e2e-comprehensive.yml
# Should show: CYPRESS_video: true

# If missing, add to workflow env section
```

---

## 🎉 Success Criteria

**You know Cypress Cloud is working when:**

1. ✅ Local verification passes with green checkmarks
2. ✅ GitHub Actions logs show: "Cypress Cloud recording enabled"
3. ✅ GitHub Actions logs show: "Recording: https://cloud.cypress.io/..."
4. ✅ Cypress Cloud dashboard shows recent runs
5. ✅ Video replay available for all tests
6. ✅ Screenshot gallery visible for failures
7. ✅ Parallel execution shows 5 machines timeline
8. ✅ Test analytics tab shows duration trends

**After 7 days:**
9. ✅ Flaky Tests tab shows pass rate percentages
10. ✅ Performance trends visible in Analytics tab

---

## 📚 További Dokumentáció

**Részletes setup guide:**
- `docs/CYPRESS_CLOUD_SETUP.md` (600+ lines, comprehensive)

**Quick reference:**
- `docs/CYPRESS_CLOUD_QUICK_START.md` (150 lines, fast)

**Verification tool:**
- `tests_cypress/verify-cypress-cloud.sh` (automated validation)

---

**Becsült teljes aktiválási idő:** 15-20 perc

**Hosszú távú érték:** ⭐⭐⭐⭐⭐
- Flaky test detection
- Video replay minden failure-höz
- Performance trend tracking
- 4x faster CI runs (parallel execution)

---

**Status:** ✅ Ready for activation — Follow this checklist!

---

**Test trigger:** 2026-02-20 - Testing Cypress Cloud recording via PR
# Cypress Cloud Test - Fri Feb 20 19:24:13 CET 2026
