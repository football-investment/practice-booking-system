# Cypress Cloud — Quick Start Guide

> **5 perces setup** a Cypress Cloud aktiválásához

---

## 🚀 Gyors Setup (5 lépés)

### **1. Cypress Cloud Fiók és Projekt Létrehozása**

```bash
# Nyisd meg a Cypress Cloud-ot
open https://cloud.cypress.io/signup
```

**Actions:**
1. Sign up GitHub account-tal
2. Create Organization: `footballinvestment`
3. Create Project: `practice-booking-system-e2e`
4. **Copy Project ID** (pl. `k5j9m2`) → másold le most!
5. Create Record Key (Project Settings → Record Keys) → **másold le most!**

---

### **2. GitHub Secrets Beállítása**

```bash
# Nyisd meg a GitHub repository secrets page-et
open https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions
```

**Add hozzá a 2 secret-et:**

| Name | Value |
|------|-------|
| `CYPRESS_PROJECT_ID` | `k5j9m2` (a te Project ID-d) |
| `CYPRESS_RECORD_KEY` | `a1b2c3d4-e5f6-7g8h-...` (a te Record Key-ed) |

---

### **3. Frissítsd a `cypress.config.js` fájlt**

```bash
cd tests_cypress
```

**Szerkeszd a `cypress.config.js` fájlt:**

```javascript
// ELŐTTE (line 7):
// projectId: 'your-project-id-here',  // ← Replace with actual Project ID

// UTÁNA:
projectId: 'k5j9m2',  // ← A te Project ID-d
```

**Mentsd el a fájlt.**

---

### **4. Verifikáld Lokálisan**

```bash
cd tests_cypress

# Set your Record Key
export CYPRESS_RECORD_KEY='your-record-key-here'

# Run verification script
./verify-cypress-cloud.sh
```

**Várt output:**
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

...

✅ Verification complete!
```

---

### **5. Commit és Push**

```bash
git add tests_cypress/cypress.config.js
git commit -m "feat(cypress-cloud): enable Cypress Cloud recording with Project ID"
git push origin main
```

**Trigger GitHub Actions workflow:**

1. Go to: https://github.com/footballinvestment/practice-booking-system/actions
2. Select: "E2E Comprehensive" workflow
3. Click: "Run workflow"
4. Select: `suite: smoke`
5. Click: "Run workflow"

**Ellenőrizd a Cypress Cloud dashboard-ot:**
```bash
open https://cloud.cypress.io/projects/k5j9m2
```

**Várt eredmény:**
- ✅ Latest run visible a dashboard-on
- ✅ Video replay elérhető
- ✅ Test results feltöltve

---

## ✅ Setup Complete!

**Mostantól:**
- ✅ Minden nightly futás automatikusan recordolva van Cypress Cloud-ba
- ✅ Flaky test detection aktív
- ✅ Video replay minden test futáshoz
- ✅ Analytics és performance metrics

**Cypress Cloud Dashboard:**
```
https://cloud.cypress.io/projects/k5j9m2
```

---

## 📊 Mit Nézhetsz Most a Dashboard-on?

### **Runs Tab**
- Összes test futás története
- Pass/fail summary
- Video replay gombok

### **Flaky Tests Tab**
- Automatikusan detektált instabil tesztek
- Pass rate percentage
- Failure patterns

### **Analytics Tab**
- Test duration trends
- Slowest specs
- Most failed specs
- Performance metrics

---

## 🔧 Troubleshooting

### **Ha a verification script failel:**

**"Project ID not configured":**
```bash
# Edit cypress.config.js
nano tests_cypress/cypress.config.js

# Uncomment and set projectId:
projectId: 'k5j9m2',  # Your actual Project ID
```

**"CYPRESS_RECORD_KEY not set":**
```bash
# Set environment variable
export CYPRESS_RECORD_KEY='your-record-key-here'

# Run verification again
./verify-cypress-cloud.sh
```

**"Recording is not allowed":**
- Check Cypress Cloud: Project Settings → Record Keys
- Verify key is Active (not Revoked)
- Verify key matches `CYPRESS_RECORD_KEY` env var

---

## 📚 Részletes Dokumentáció

**Teljes setup guide:** [docs/CYPRESS_CLOUD_SETUP.md](CYPRESS_CLOUD_SETUP.md)

**Tartalmazza:**
- Részletes setup lépések
- Dashboard használati útmutató
- Troubleshooting guide
- Best practices
- Flaky test management workflow

---

**Setup Time:** ~5 perc
**Monthly Cost:** Ingyenes (500 recordings/month free tier)
**Értéke:** ⭐⭐⭐⭐⭐ (flaky test detection, video replay, analytics)
