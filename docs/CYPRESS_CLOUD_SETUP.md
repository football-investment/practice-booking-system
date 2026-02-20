# Cypress Cloud Setup Guide — Aktiválás és Konfiguráció

> **Utolsó frissítés:** 2026-02-20
> **Státusz:** Aktiválásra kész

---

## 📋 Tartalomjegyzék

- [Áttekintés](#áttekintés)
- [Előnyök](#előnyök)
- [Step-by-Step Setup](#step-by-step-setup)
- [GitHub Secrets Konfiguráció](#github-secrets-konfiguráció)
- [Verifikáció](#verifikáció)
- [Dashboard Használata](#dashboard-használata)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Áttekintés

A **Cypress Cloud** (korábban Cypress Dashboard) egy cloud-based test reporting és analytics platform, amely átfogó betekintést nyújt az E2E tesztek futásába.

**Egyszer beállítva:**
- ✅ Automatikus recording minden PR és nightly futásban
- ✅ Flaky test detection és trend analysis
- ✅ Video replay minden teszt futáshoz
- ✅ Screenshot gallery minden failurehez
- ✅ Test analytics és performance metrics
- ✅ Parallel execution optimalizáció

---

## 🚀 Előnyök

### **1. Flaky Test Detection**

**Probléma:** Egyes tesztek néha failelnek, néha passzolnak (flaky tests).

**Cypress Cloud megoldás:**
- Automatikusan detektálja a flaky testeket
- Mutatja a failure rate-et (pl. "85% pass rate over last 50 runs")
- Trendeket azonosít (pl. "Started failing 3 days ago")

**Dashboard view:**
```
🟡 admin/user_management.cy.js
   └─ "admin can add credits to user balance"
      Pass rate: 92% (46/50 runs)
      Status: FLAKY ⚠️
      Trend: Stable flaky (last 7 days)
```

### **2. Video Replay & Screenshots**

**Probléma:** CI-ban failelt teszt, de lokálisan passzol — mi történt?

**Cypress Cloud megoldás:**
- Minden test run videója automatikusan feltöltve
- Click-to-play video replay közvetlenül a dashboardról
- Screenshot gallery minden assertion failurenél
- Timeline view: pontosan melyik lépésnél failelt

**Dashboard view:**
```
❌ Test: "instructor can submit results"
   Duration: 12.3s
   Failed at: Step 7 (Result submission)

   [▶ Watch Video Replay]  [📸 View Screenshots (3)]
```

### **3. Test Analytics**

**Probléma:** Melyik tesztek a leglassabbak? Melyik specc failel leggyakrabban?

**Cypress Cloud megoldás:**
- Test duration trends (lassulás detektálás)
- Failure rate by spec
- Most flaky tests leaderboard
- Execution time breakdown

**Dashboard view:**
```
📊 Test Performance (Last 30 days)

   Slowest Tests:
   1. admin/tournament_lifecycle_complete.cy.js  (~45s avg)
   2. instructor/tournament_workflow.cy.js       (~32s avg)
   3. admin/session_management.cy.js            (~28s avg)

   Most Flaky Tests:
   1. admin/financial_management.cy.js → "refund processing" (82% pass)
   2. student/enrollment_flow.cy.js → "payment success" (88% pass)
```

### **4. Parallel Execution Optimization**

**Probléma:** 525 teszt ~60 perc CI időben — lehet gyorsítani?

**Cypress Cloud megoldás:**
- Automatikus load balancing több machine között
- Intelligens test splitting (slowest tests először)
- Real-time progress tracking

**Eredmény:**
- 525 teszt 5 parallel machine-en → ~12-15 perc (4x gyorsabb)

---

## 🔧 Step-by-Step Setup

### **Lépés 1: Cypress Cloud Fiók Létrehozása**

1. **Navigálj a Cypress Cloud-hoz:**
   ```
   https://cloud.cypress.io/signup
   ```

2. **Sign up GitHub account-tal:**
   - Click "Sign up with GitHub"
   - Authorize Cypress Cloud
   - (Ingyenes tier: 500 test recordings/month)

3. **Organization létrehozása:**
   - Org name: `footballinvestment` (vagy custom)
   - Click "Create Organization"

---

### **Lépés 2: Project Létrehozása**

1. **New Project:**
   - Click "+ New Project"
   - Project name: `practice-booking-system-e2e`
   - Click "Create Project"

2. **Project ID megszerzése:**
   - Project Settings → General
   - **Copy Project ID** (pl. `abc123`)
   - Példa:
     ```
     Project ID: k5j9m2
     ```

3. **Record Key generálása:**
   - Project Settings → Record Keys
   - Click "+ Create Record Key"
   - Key name: `ci-github-actions`
   - Click "Create Key"
   - **Copy Record Key** (pl. `a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6`)
   - ⚠️ **FONTOS:** Ez a key csak egyszer látható! Másold le most!

---

### **Lépés 3: GitHub Secrets Beállítása**

1. **Navigálj a GitHub repository Settings-hez:**
   ```
   https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions
   ```

2. **Add meg a CYPRESS_PROJECT_ID secret-et:**
   - Click **"New repository secret"**
   - Name: `CYPRESS_PROJECT_ID`
   - Secret: `k5j9m2` (vagy a te Project ID-d)
   - Click **"Add secret"**

3. **Add meg a CYPRESS_RECORD_KEY secret-et:**
   - Click **"New repository secret"**
   - Name: `CYPRESS_RECORD_KEY`
   - Secret: `a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6` (vagy a te Record Key-ed)
   - Click **"Add secret"**

**Ellenőrzés:**
```
Repository Settings → Secrets and variables → Actions

✅ CYPRESS_PROJECT_ID        (set)
✅ CYPRESS_RECORD_KEY         (set)
```

---

### **Lépés 4: Lokális `cypress.config.js` Frissítése**

**Jelenleg:** Nincs projectId a config-ban

**Frissítés:** Add hozzá a projectId-t

```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system/tests_cypress
```

Szerkeszd a `cypress.config.js` fájlt:

```javascript
// Add this to the top-level config object:
module.exports = defineConfig({
  projectId: 'k5j9m2',  // ← Add this line (use your actual Project ID)
  e2e: {
    // ... existing config ...
  },
});
```

---

### **Lépés 5: Első Test Recording (Lokális Teszt)**

**Teszt futtatás recording-gal:**

```bash
cd tests_cypress

# Set environment variables
export CYPRESS_RECORD_KEY='a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6'

# Run smoke tests with recording
npx cypress run --env grepTags=@smoke --record
```

**Várt output:**
```
  Recording at https://cloud.cypress.io/projects/k5j9m2/runs/123

  ┌────────────────────────────────────────────────────────────────┐
  │ Cypress:        13.17.0                                         │
  │ Browser:        Chrome 123                                      │
  │ Node Version:   v20.11.0                                        │
  │ Specs:          15 found (smoke tests)                          │
  │ Searched:       cypress/e2e/**/*.cy.{js,jsx}                    │
  │ Params:         Tag @smoke                                      │
  │ Run URL:        https://cloud.cypress.io/projects/k5j9m2/runs/123│
  └────────────────────────────────────────────────────────────────┘

  Running:  admin/dashboard_navigation.cy.js                     (1 of 15)
  ✓ admin dashboard loads without error                      (1234ms)
  ...

  Uploading Results to Cypress Cloud...
  ✅ Recorded Run: https://cloud.cypress.io/projects/k5j9m2/runs/123
```

**Ellenőrzés:**
1. Kattints a run URL-re: `https://cloud.cypress.io/projects/k5j9m2/runs/123`
2. Láthatod a teljes test run eredményét
3. Video replay minden teszthez
4. Screenshot gallery (ha volt failure)

---

### **Lépés 6: CI/CD Workflow Automatic Recording Engedélyezése**

**Jelenleg:** A workflow csak manual dispatch esetén recordol (ha `record: true`)

**Frissítés:** Automatic recording minden futásban (ha secrets beállítva)

**Módosítás a `.github/workflows/e2e-comprehensive.yml`-ben:**

A **Full Suite** jobnál (line ~400):

**ELŐTTE:**
```yaml
RECORD_FLAG=""
if [ -n "${{ secrets.CYPRESS_RECORD_KEY }}" ] && [ "${{ github.event.inputs.record }}" = "true" ]; then
  RECORD_FLAG="--record --parallel --group ${{ matrix.role }} --ci-build-id ${{ github.run_id }}"
fi
```

**UTÁNA:**
```yaml
RECORD_FLAG=""
if [ -n "${{ secrets.CYPRESS_RECORD_KEY }}" ]; then
  RECORD_FLAG="--record --parallel --group ${{ matrix.role }} --ci-build-id ${{ github.run_id }}"
fi
```

**Változás:** Eltávolítottuk a `&& [ "${{ github.event.inputs.record }}" = "true" ]` feltételt

**Eredmény:** Ha `CYPRESS_RECORD_KEY` secret létezik → automatikus recording minden nightly futásban

---

## ✅ Verifikáció

### **1. GitHub Secrets Ellenőrzése**

```bash
# Navigálj a repository settings-hez:
open https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions
```

**Elvárt:**
```
✅ CYPRESS_PROJECT_ID     (set, last updated X days ago)
✅ CYPRESS_RECORD_KEY     (set, last updated X days ago)
```

### **2. Lokális Recording Teszt**

```bash
cd tests_cypress

# Test with your actual record key
CYPRESS_RECORD_KEY='your-record-key-here' \
  npx cypress run --env grepTags=@smoke --record
```

**Siker jele:**
```
Uploading Results to Cypress Cloud...
✅ Recorded Run: https://cloud.cypress.io/projects/k5j9m2/runs/XXX
```

### **3. CI/CD Recording Teszt**

**Trigger manual workflow:**

1. GitHub Actions → E2E Comprehensive workflow
2. Click "Run workflow"
3. Select:
   - `suite: smoke`
   - `record: true` (ha még nem automatic)
4. Click "Run workflow"

**Workflow futás után:**
1. Check workflow logs → "Run full suite" step
2. Look for: `Recording at https://cloud.cypress.io/projects/k5j9m2/runs/XXX`
3. Open the Cypress Cloud URL
4. Verify test results visible

### **4. Cypress Cloud Dashboard Ellenőrzése**

```bash
# Open your Cypress Cloud project
open https://cloud.cypress.io/projects/k5j9m2
```

**Elvárt:**
- ✅ Latest Runs tab shows recent test runs
- ✅ Specs tab shows all test files
- ✅ Analytics tab shows performance metrics
- ✅ Flaky Tests tab (még üres ha nincs flaky)

---

## 📊 Dashboard Használata

### **1. Runs Tab — Test Run Története**

**Navigálás:**
```
Cypress Cloud → Projects → practice-booking-system-e2e → Runs
```

**Mit látsz:**
```
┌──────────────────────────────────────────────────────────────┐
│ Recent Runs                                                   │
├──────────────────────────────────────────────────────────────┤
│ Run #123  ✅ Passed   main   2 min ago   Duration: 5m 23s    │
│   - 30 tests passed                                           │
│   - Triggered by: GitHub Actions (PR #456)                    │
│   [View Run Details]                                          │
│                                                                │
│ Run #122  ❌ Failed   main   1 hour ago  Duration: 18m 45s   │
│   - 148 passed, 2 failed                                      │
│   - admin/financial_management.cy.js → "refund processing"    │
│   [View Run Details] [Watch Video] [View Screenshots]         │
└──────────────────────────────────────────────────────────────┘
```

**Kattints egy run-ra:**
- **Overview:** Pass/fail summary, duration, commit info
- **Specs:** Minden spec fájl részletes eredményei
- **Timeline:** Vizuális timeline minden test execution-ről
- **Video:** Full test run video replay

---

### **2. Flaky Tests Tab — Instabil Tesztek Azonosítása**

**Navigálás:**
```
Cypress Cloud → Projects → practice-booking-system-e2e → Flaky Tests
```

**Mit látsz:**
```
┌──────────────────────────────────────────────────────────────┐
│ Flaky Tests (Last 50 runs)                                   │
├──────────────────────────────────────────────────────────────┤
│ admin/financial_management.cy.js                              │
│   └─ "admin can process refund for tournament cancellation"   │
│      Pass rate: 88% (44/50 runs)                              │
│      Status: FLAKY ⚠️                                         │
│      Trend: Getting worse (was 92% last week)                 │
│      [View Test] [See Failure Patterns]                       │
│                                                                │
│ instructor/tournament_workflow.cy.js                          │
│   └─ "instructor can submit results to finalize session"      │
│      Pass rate: 94% (47/50 runs)                              │
│      Status: FLAKY ⚠️                                         │
│      Trend: Stable (no change in 30 days)                     │
│      [View Test] [See Failure Patterns]                       │
└──────────────────────────────────────────────────────────────┘
```

**Használat:**
1. Kattints egy flaky test-re
2. **Failure Patterns:** Lásd hogy mikor failel (időpont, branch, CI machine)
3. **Video Comparison:** Nézd meg passing vs failing run video replay-eket
4. **Fix the flaky test:** Add explicit waits, improve selectors, stb.

---

### **3. Analytics Tab — Performance Metrics**

**Navigálás:**
```
Cypress Cloud → Projects → practice-booking-system-e2e → Analytics
```

**Mit látsz:**
```
┌──────────────────────────────────────────────────────────────┐
│ Test Performance (Last 30 days)                               │
├──────────────────────────────────────────────────────────────┤
│ Average Duration Trend:                                       │
│   [📈 Graph showing duration over time]                       │
│   Current avg: 18m 30s                                        │
│   30 days ago: 15m 45s                                        │
│   Trend: ⚠️ Getting slower (+17% in 30 days)                 │
│                                                                │
│ Slowest Specs:                                                │
│   1. admin/tournament_lifecycle_complete.cy.js   (avg 45s)    │
│   2. instructor/tournament_workflow.cy.js        (avg 32s)    │
│   3. admin/session_management.cy.js             (avg 28s)    │
│                                                                │
│ Most Failed Specs:                                            │
│   1. admin/financial_management.cy.js   (12 failures/50 runs) │
│   2. student/enrollment_flow.cy.js      (8 failures/50 runs)  │
└──────────────────────────────────────────────────────────────┘
```

**Használat:**
- **Duration trends:** Lassulás észlelése → optimalizálás szükséges
- **Slowest specs:** Targetált optimalizálás (cache, test data, stb.)
- **Most failed specs:** Reliability javítás prioritás

---

### **4. Parallel Execution Dashboard**

**Navigálás:**
```
Cypress Cloud → Run Details → Timeline View
```

**Mit látsz (parallel execution esetén):**
```
┌──────────────────────────────────────────────────────────────┐
│ Run #125 — Full Suite (Parallel 5x)                          │
├──────────────────────────────────────────────────────────────┤
│ Machine 1 (admin):                                            │
│   [████████████████████████████] 100% (35m 20s)              │
│   420 tests, 418 passed, 2 failed                             │
│                                                                │
│ Machine 2 (instructor):                                       │
│   [████████████████████] 100% (15m 10s)                      │
│   67 tests, 67 passed                                         │
│                                                                │
│ Machine 3 (player):                                           │
│   [█████████████] 100% (10m 05s)                             │
│   38 tests, 38 passed                                         │
│                                                                │
│ Machine 4 (auth):                                             │
│   [████████] 100% (8m 30s)                                   │
│   15 tests, 15 passed                                         │
│                                                                │
│ Machine 5 (system):                                           │
│   [█████████] 100% (9m 15s)                                  │
│   20 tests, 20 passed                                         │
│                                                                │
│ Total Duration: 35m 20s (bottleneck: admin machine)          │
│ Parallelization Efficiency: 4.2x speedup vs sequential       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### **Probléma 1: "Recording is not allowed"**

**Hibaüzenet:**
```
Error: Recording is not allowed in this project.
```

**Megoldás:**
1. Verify Project ID helyes:
   ```bash
   # Check cypress.config.js
   grep projectId tests_cypress/cypress.config.js
   # Should show: projectId: 'k5j9m2',
   ```

2. Verify Record Key aktív:
   - Cypress Cloud → Project Settings → Record Keys
   - Check key status: Active ✅ (not Revoked ❌)

3. Verify GitHub Secret helyes:
   - Repository Settings → Secrets
   - `CYPRESS_RECORD_KEY` value matches Cypress Cloud Record Key

### **Probléma 2: "Project not found"**

**Hibaüzenet:**
```
Error: We could not find a project with the ID: k5j9m2
```

**Megoldás:**
1. Verify Project ID Cypress Cloud-ban:
   - Cypress Cloud → Project Settings → General
   - Copy exact Project ID (case-sensitive!)

2. Update `cypress.config.js`:
   ```javascript
   projectId: 'k5j9m2',  // Must match exactly
   ```

3. Update GitHub Secret `CYPRESS_PROJECT_ID`

### **Probléma 3: Recording sikeres, de nincs video**

**Probléma:** Test run uploadolva, de nincs video replay

**Megoldás:**
1. Check `cypress.config.js` video setting:
   ```javascript
   video: true,  // Must be true for recording
   ```

2. Check CI workflow env var:
   ```yaml
   CYPRESS_video: true  # Ensure this is set in workflow
   ```

3. Verify video uploadolva:
   - Cypress Cloud → Run Details → Check "Videos" tab
   - Ha nincs → check Cypress Cloud storage quota (free tier: 500 recordings)

### **Probléma 4: Parallel execution nem működik**

**Probléma:** Recording működik, de parallel execution nem

**Megoldás:**
1. Verify `--parallel` flag használata:
   ```bash
   npx cypress run --record --parallel --ci-build-id ${CI_BUILD_ID}
   ```

2. Verify `--ci-build-id` egyedi:
   - GitHub Actions: `${{ github.run_id }}`
   - Ha duplicate build ID → parallel nem fog működni

3. Verify több machine fut egyidőben:
   - GitHub Actions matrix strategy kell
   - Min. 2 parallel job a parallel execution működéséhez

---

## 📈 Best Practices

### **1. Recording Stratégia**

**Ajánlott:**
- ✅ **PR gate:** NE recordolj (gyorsabb, nincs quota limit)
- ✅ **Nightly full suite:** Recordolj (analytics, flaky detection)
- ✅ **Manual workflow dispatch:** Opcionális (debug purposes)

**Indoklás:**
- Free tier: 500 recordings/month
- 30 nightly run = ~150 recordings/month (5 parallel jobs)
- Elég kapacitás analytics-hez, de ne pazarold PR-okra

### **2. Flaky Test Management**

**Workflow:**
1. **Detection:** Cypress Cloud flaky test tab
2. **Analysis:** Video replay comparing passing vs failing runs
3. **Fix:** Add explicit waits, improve selectors, retry logic
4. **Verify:** Monitor flaky test pass rate improvement

**Példa fix:**
```javascript
// BEFORE (flaky)
cy.get('[data-testid="stButton"]').click();

// AFTER (stable)
cy.get('[data-testid="stButton"]').should('be.visible');
cy.wait(500);  // Give Streamlit time to settle after rerender
cy.get('[data-testid="stButton"]').click();
```

### **3. Performance Optimization**

**Használd az Analytics tab-ot:**
1. **Identify slow tests:** Analytics → Slowest Specs
2. **Optimize:** Cache test data, reduce API calls, parallel-safe tests
3. **Measure:** Compare duration trends before/after optimization

**Példa:**
```
Before optimization: admin/session_management.cy.js → 45s avg
After optimization:  admin/session_management.cy.js → 28s avg
Improvement: 37% faster ✅
```

---

## ✅ Aktiválás Checklist

```
□ Cypress Cloud fiók létrehozva (https://cloud.cypress.io)
□ Organization létrehozva (footballinvestment)
□ Project létrehozva (practice-booking-system-e2e)
□ Project ID megszerzése (pl. k5j9m2)
□ Record Key generálása (pl. a1b2c3d4...)
□ GitHub Secret: CYPRESS_PROJECT_ID beállítva
□ GitHub Secret: CYPRESS_RECORD_KEY beállítva
□ cypress.config.js frissítve (projectId hozzáadva)
□ Lokális recording teszt sikeres (npx cypress run --record)
□ CI/CD workflow frissítve (automatic recording enabled)
□ Első CI recording sikeres (GitHub Actions run visible in Cypress Cloud)
□ Dashboard ellenőrizve (Runs/Flaky Tests/Analytics tabs)
```

---

**Cypress Cloud Státusz:** ✅ **Aktiválásra kész**

**Következő lépések:**
1. Követd a fenti setup guide-ot
2. Verify lokálisan (step 5)
3. Push changes (cypress.config.js + workflow update)
4. Trigger GitHub Actions workflow
5. Ellenőrizd a Cypress Cloud dashboard-ot

**Várható eredmény:**
- 🎥 Video replay minden teszt futáshoz
- 📊 Analytics és flaky test detection
- ⚡ Parallel execution optimization
- 🛡️ Long-term regression trend tracking
