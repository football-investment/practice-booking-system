# 🛡️ P2 Stabilization & Baseline Plan

**Phase**: Post-Deployment Stabilization
**Duration**: 24-72 hours
**Date**: 2025-10-25
**Status**: IN PROGRESS
**Author**: Claude Code

---

## 📋 Executive Summary

Following successful P2 implementation, this plan outlines the **stabilization phase** to ensure all automated processes function reliably in production before proceeding with new development.

### Objectives

1. ✅ Deploy P2 Health Dashboard to production
2. ⏳ Create baseline health snapshot
3. ⏳ Verify scheduler runs every 5 minutes
4. ⏳ Monitor system stability for 24-72 hours
5. ⏳ Document baseline and establish monitoring protocol

### Why Stabilization First?

> "Ne indíts új fejlesztést azonnal, hanem menjünk stratégiai lépésben tovább, és nézzük meg, hogyan viselkedik a rendszer élő környezetben."

**Benefits**:
- Catch deployment issues early
- Establish reliable baseline for future comparisons
- Verify scheduler stability before alerts
- Build confidence in automated monitoring
- Real data for P3 Alert System design

---

## 🎯 Deployment Execution

### Step 1: Backend Deployment

#### 1.1 Verify Current State

```bash
# Check current git status
git status

# Expected: P2 files committed or staged
# - app/services/health_monitor.py
# - app/api/api_v1/endpoints/health.py
# - app/background/scheduler.py (modified)
```

#### 1.2 Create Deployment Branch (Optional)

```bash
# Create deployment branch
git checkout -b deployment/p2-health-dashboard

# Commit all P2 changes
git add app/services/health_monitor.py
git add app/api/api_v1/endpoints/health.py
git add app/background/scheduler.py
git add app/api/api_v1/api.py
git add frontend/src/components/admin/HealthDashboard.js
git add frontend/src/components/admin/HealthDashboard.css
git add frontend/src/services/apiService.js
git add frontend/src/App.js
git add frontend/src/pages/admin/AdminDashboard.js

# Commit with descriptive message
git commit -m "feat(P2): Implement Health Dashboard with 5-min monitoring

- Add health monitoring service (health_monitor.py)
- Create 5 admin API endpoints (/api/v1/health/*)
- Integrate scheduler with 5-minute health checks
- Build React dashboard with auto-refresh (30s)
- Add color-coded status indicators (green/yellow/red)
- JSON violation logging to logs/integrity_checks/

Closes P2 Sprint - Observability & Monitoring

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Merge to main (or push to deployment branch)
git checkout main
git merge deployment/p2-health-dashboard
```

#### 1.3 Restart Backend Service

**Option A: Docker Compose**
```bash
# Restart backend container
docker-compose restart backend

# Verify restart
docker-compose logs -f backend | grep "scheduler"

# Expected output:
# INFO - 🚀 Starting background scheduler...
# INFO - ✅ Background scheduler started successfully
# INFO - Scheduled jobs:
#   - Progress-License Auto-Sync (ID: progress_license_sync): interval[6:00:00]
#   - Coupling Enforcer Health Check (ID: coupling_health_check): interval[0:05:00]
```

**Option B: Systemd Service**
```bash
# Restart service
sudo systemctl restart practice-booking-api

# Check status
sudo systemctl status practice-booking-api

# Tail logs
sudo journalctl -u practice-booking-api -f | grep "scheduler"
```

**Option C: Manual (Development)**
```bash
# Kill existing uvicorn process
pkill -f "uvicorn app.main:app"

# Start backend with scheduler
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Verify in logs:
# INFO:     Started server process [XXXX]
# INFO:     Waiting for application startup.
# INFO - 🚀 Starting background scheduler...
# INFO - ✅ Background scheduler started successfully
```

---

### Step 2: Frontend Deployment

#### 2.1 Verify Production Build

```bash
cd frontend

# Check build exists
ls -lh build/

# Verify build artifacts
ls -lh build/static/js/main*.js
ls -lh build/static/css/main*.css

# Expected:
# main.XXXXXXXX.js (~805 KB gzipped)
# main.XXXXXXXX.css (~95 KB gzipped)
```

#### 2.2 Deploy to Server

**Option A: Docker Compose**
```bash
# Copy build to container
docker cp build/. practice_booking_frontend:/usr/share/nginx/html/

# Restart frontend
docker-compose restart frontend

# Verify restart
docker-compose logs frontend
```

**Option B: Nginx Static Hosting**
```bash
# Backup existing deployment
sudo cp -r /var/www/practice_booking_frontend /var/www/practice_booking_frontend.backup_$(date +%Y%m%d)

# Deploy new build
sudo rsync -av --delete build/ /var/www/practice_booking_frontend/

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

**Option C: Netlify/Vercel**
```bash
# Netlify
netlify deploy --prod --dir=build

# OR Vercel
vercel --prod

# Note URL provided by hosting service
```

---

### Step 3: Verification

#### 3.1 Backend Health Endpoints

```bash
# Get admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}' \
  | jq -r '.access_token')

# Test health status endpoint
curl -s http://localhost:8000/api/v1/health/status \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected (first run, no checks yet):
# {
#   "status": "unknown",
#   "last_check": null,
#   "consistency_rate": null,
#   "total_violations": 0,
#   "requires_attention": false
# }
```

#### 3.2 Frontend Dashboard Access

1. Open browser: `https://yourdomain.com/login`
2. Log in as admin
3. Navigate to Admin Dashboard (`/admin/dashboard`)
4. Click "System Health" card
5. Verify health dashboard loads (`/admin/health`)
6. Check "No health reports available yet" message (first run)

#### 3.3 Trigger First Manual Check

```bash
# Trigger initial health check
curl -X POST http://localhost:8000/api/v1/health/check-now \
  -H "Authorization: Bearer $TOKEN" \
  | tee logs/baselines/manual_check_$(date +%Y%m%d_%H%M%S).json \
  | jq

# Expected output:
# {
#   "timestamp": "2025-10-25T14:30:00.123456",
#   "total_checked": 150,
#   "consistent": 148,
#   "inconsistent": 2,
#   "consistency_rate": 98.67,
#   "violations": [...]
# }
```

#### 3.4 Verify Dashboard Updates

1. Refresh dashboard in browser (`/admin/health`)
2. Status badge should now show color (green/yellow/red)
3. Gauge should show consistency rate
4. Metrics card should show user counts
5. If violations exist, table should appear

---

## 📊 Baseline Creation

### Step 1: Create Baselines Directory

```bash
# Create baselines directory
mkdir -p logs/baselines

# Verify
ls -la logs/baselines/
```

### Step 2: Capture Baseline Snapshot

```bash
# Trigger health check and save baseline
curl -X POST http://localhost:8000/api/v1/health/check-now \
  -H "Authorization: Bearer $TOKEN" \
  -o logs/baselines/baseline_$(date +%Y%m%d_%H%M%S).json

# Verify baseline saved
ls -lh logs/baselines/

# View baseline
cat logs/baselines/baseline_*.json | jq
```

### Step 3: Document Baseline Metadata

```bash
# Extract baseline metrics
BASELINE_FILE=$(ls -t logs/baselines/baseline_*.json | head -1)
TOTAL_CHECKED=$(cat $BASELINE_FILE | jq .total_checked)
CONSISTENCY_RATE=$(cat $BASELINE_FILE | jq .consistency_rate)
VIOLATIONS=$(cat $BASELINE_FILE | jq .inconsistent)

# Create baseline README
cat > logs/baselines/BASELINE_README.md <<EOF
# Health Dashboard Baseline

**Created**: $(date)
**Baseline File**: $(basename $BASELINE_FILE)

## Baseline Metrics

- **Total Users Checked**: $TOTAL_CHECKED
- **Consistency Rate**: $CONSISTENCY_RATE%
- **Violations**: $VIOLATIONS

## Status Thresholds

- **🟢 HEALTHY**: consistency_rate ≥ 99%
- **🟡 DEGRADED**: 95% ≤ consistency_rate < 99%
- **🔴 CRITICAL**: consistency_rate < 95%

## Baseline Interpretation

Current Status: $(if (( $(echo "$CONSISTENCY_RATE >= 99" | bc -l) )); then echo "🟢 HEALTHY"; elif (( $(echo "$CONSISTENCY_RATE >= 95" | bc -l) )); then echo "🟡 DEGRADED"; else echo "🔴 CRITICAL"; fi)

### Next Steps

1. Monitor health dashboard for 24-72 hours
2. Compare future checks to this baseline
3. Investigate any drops > 2% from baseline
4. Document violations if any (see KNOWN_VIOLATIONS.md)

## Monitoring Schedule

- **Automated Checks**: Every 5 minutes (scheduler)
- **Manual Review**: Daily (first week)
- **Weekly Report**: Every Monday
- **Baseline Update**: Monthly or after major changes

## Escalation Criteria

**DEGRADED** (95-99%):
- Review violations table
- Check sync logs
- Plan sync if needed

**CRITICAL** (<95%):
- Immediate investigation
- Run manual sync (auto_sync_all)
- Check for system issues
- Escalate to development team

EOF

echo "✅ Baseline documented: logs/baselines/BASELINE_README.md"
```

### Step 4: Document Violations (if any)

```bash
# If violations exist, extract and document
if [ $(cat $BASELINE_FILE | jq .inconsistent) -gt 0 ]; then
  # Extract violations
  cat $BASELINE_FILE | jq '.violations' > logs/baselines/baseline_violations.json

  # Create violations report
  cat > logs/baselines/KNOWN_VIOLATIONS.md <<EOF
# Known Baseline Violations

**Date**: $(date)
**Total Violations**: $(cat $BASELINE_FILE | jq .inconsistent)

## Violations List

$(cat $BASELINE_FILE | jq -r '.violations[] | "- **User \(.user_id)** | \(.specialization): Progress Level **\(.progress_level)** vs License Level **\(.license_level)** (Δ **\(.progress_level - .license_level)**)"')

## Analysis

### By Specialization

$(cat $BASELINE_FILE | jq -r '[.violations[] | .specialization] | group_by(.) | map({specialization: .[0], count: length}) | .[] | "- \(.specialization): \(.count) violations"')

### By Discrepancy

$(cat $BASELINE_FILE | jq -r '[.violations[] | .progress_level - .license_level] | group_by(.) | map({delta: .[0], count: length}) | .[] | "- Δ\(.delta): \(.count) users"')

## Recommended Actions

1. **Review each violation**: Determine if sync needed or expected state
2. **Run sync if needed**: Use \`POST /api/v1/health/check-now\` or wait for 6-hour sync
3. **Re-baseline**: After corrections, create new baseline
4. **Document exceptions**: If violations are expected, note in this file

## Sync Options

### Option 1: Manual Sync (Immediate)
\`\`\`bash
# Trigger sync for all users with violations
curl -X POST http://localhost:8000/api/v1/health/check-now \
  -H "Authorization: Bearer \$TOKEN"
\`\`\`

### Option 2: Wait for Scheduled Sync (6 hours)
The background scheduler will automatically sync desync issues every 6 hours.

### Option 3: Selective Sync (via admin panel)
Use the admin panel to sync individual users if needed (future feature).

EOF

  echo "⚠️  Violations documented: logs/baselines/KNOWN_VIOLATIONS.md"
else
  echo "✅ No violations in baseline. System healthy!"
fi
```

---

## 🔍 24-Hour Monitoring Protocol

### Hour 0-1: Initial Verification

**Checklist**:
- [ ] Backend scheduler running (check logs)
- [ ] First scheduled health check completed (wait 5 minutes)
- [ ] JSON log created (`logs/integrity_checks/`)
- [ ] Dashboard auto-refresh working (wait 30 seconds)
- [ ] No errors in backend logs
- [ ] No console errors in browser

**Commands**:
```bash
# Watch scheduler logs
tail -f logs/sync_jobs/scheduler_$(date +%Y%m%d).log

# Wait 5 minutes, then check integrity logs
ls -lt logs/integrity_checks/ | head -3

# Count checks in last hour
grep "Health check complete" logs/sync_jobs/scheduler_$(date +%Y%m%d).log | wc -l
# Expected: 12 checks (every 5 minutes)
```

---

### Hour 2-6: Stability Monitoring

**Checklist**:
- [ ] Consistency rate stable (±2% from baseline)
- [ ] No new unexpected violations
- [ ] Scheduler logs clean (no errors)
- [ ] JSON logs being created regularly

**Commands**:
```bash
# Check consistency rate trend
grep "Health check complete" logs/sync_jobs/scheduler_$(date +%Y%m%d).log | tail -20

# Count integrity check logs
ls logs/integrity_checks/*.json 2>/dev/null | wc -l

# Check for errors
grep ERROR logs/sync_jobs/scheduler_$(date +%Y%m%d).log
```

---

### Hour 12-24: Trend Analysis

**Checklist**:
- [ ] Extract consistency rates from last 24 hours
- [ ] Plot trend (manually or with script)
- [ ] Identify any anomalies
- [ ] Document observations

**Script**:
```bash
# Extract consistency rates from logs
grep "Health check complete" logs/sync_jobs/scheduler_$(date +%Y%m%d).log \
  | awk -F'[()]' '{print $2}' \
  | tee logs/reports/consistency_trend_24h_$(date +%Y%m%d).txt

# Calculate average
grep "Health check complete" logs/sync_jobs/scheduler_$(date +%Y%m%d).log \
  | awk -F'[()]' '{print $2}' \
  | awk -F'%' '{sum+=$1; count++} END {print "Average: " sum/count "%"}'

# Find min/max
grep "Health check complete" logs/sync_jobs/scheduler_$(date +%Y%m%d).log \
  | awk -F'[()]' '{print $2}' \
  | awk -F'%' '{
      if (NR==1) {min=$1; max=$1}
      if ($1<min) min=$1;
      if ($1>max) max=$1
    }
    END {print "Min: " min "%, Max: " max "%"}'
```

---

### Day 2-3: Extended Monitoring

**Checklist**:
- [ ] Review 48-hour trend
- [ ] Check for weekly patterns (if applicable)
- [ ] Verify 6-hour sync job ran successfully
- [ ] Compare violations to baseline

**Report Template**:
```bash
cat > logs/reports/stabilization_report_$(date +%Y%m%d).md <<EOF
# 72-Hour Stabilization Report

**Report Date**: $(date)
**Monitoring Period**: $(date -v-3d +%Y-%m-%d) to $(date +%Y-%m-%d)

## Executive Summary

**Status**: [STABLE / NEEDS ATTENTION / CRITICAL]

## Metrics

### Consistency Rate

- **Baseline**: $CONSISTENCY_RATE%
- **Current**: [CALCULATE FROM LATEST CHECK]
- **Average (72h)**: [CALCULATE]
- **Min/Max**: [CALCULATE]
- **Trend**: [STABLE / IMPROVING / DEGRADING]

### Violations

- **Baseline**: $VIOLATIONS violations
- **Current**: [COUNT FROM LATEST]
- **New Violations**: [CALCULATE DIFFERENCE]
- **Resolved**: [CALCULATE]

### System Health

- **Health Checks Run**: $(grep "Health check complete" logs/sync_jobs/scheduler_*.log | wc -l)
- **Expected Checks**: 864 (72h * 12 per hour)
- **Success Rate**: [CALCULATE]%
- **Errors**: $(grep ERROR logs/sync_jobs/scheduler_*.log | wc -l)

## Observations

### Positive

- [List stable behaviors]
- [List improvements]

### Issues

- [List anomalies]
- [List errors]

### Action Items

- [ ] [Item 1]
- [ ] [Item 2]

## Recommendation

**Proceed with P3 Sprint**: [YES / NO / CONDITIONAL]

**Reasoning**: [Explain based on data]

## Next Steps

1. [Step 1]
2. [Step 2]

---

**Compiled By**: [Your Name]
**Sign-Off**: [Manager Name]
**Date**: $(date)
EOF

echo "✅ Stabilization report created: logs/reports/stabilization_report_$(date +%Y%m%d).md"
```

---

## 📈 Success Criteria

### ✅ Ready for P3 (Alert System)

**Criteria**:
- ✅ Consistency rate **stable** (±2% variance from baseline)
- ✅ Scheduler **reliable** (>99% success rate)
- ✅ JSON logs **created regularly** (every 5 minutes)
- ✅ Dashboard **functional** (auto-refresh, manual check work)
- ✅ No critical errors in logs
- ✅ Violations documented and understood

### ⚠️ Needs Attention

**Indicators**:
- Consistency rate **degrading** (>5% drop from baseline)
- Scheduler **failing intermittently** (<95% success rate)
- **Errors** in logs
- Unexpected violations appearing

**Actions**:
1. Investigate logs for errors
2. Check database health
3. Review recent code changes
4. Consider rollback if critical

### 🔴 Critical Issues

**Indicators**:
- Scheduler **not running**
- Consistency rate **critical** (<95%)
- Dashboard **not accessible**
- Errors **blocking operations**

**Immediate Actions**:
1. **Stop P3 planning**
2. Debug and fix issues
3. Re-run stabilization after fix
4. Extend monitoring period

---

## 🎯 Decision Matrix

After 24-72 hours, use this matrix to decide next steps:

| Consistency Rate | Scheduler | Violations | Decision |
|------------------|-----------|------------|----------|
| ≥99% stable | ✅ Running | Documented | **✅ Proceed to P3** |
| 95-99% stable | ✅ Running | Documented | ⚠️ Investigate, then P3 |
| <95% | ✅ Running | Undocumented | 🔴 Fix issues first |
| Any | ❌ Failing | Any | 🔴 Fix scheduler first |

---

## 📚 Deliverables

### Required Deliverables

- [x] Deployment executed (backend + frontend)
- [ ] Baseline snapshot created (`logs/baselines/baseline_*.json`)
- [ ] Baseline documented (`BASELINE_README.md`)
- [ ] Violations documented (if any) (`KNOWN_VIOLATIONS.md`)
- [ ] 24-hour monitoring logs collected
- [ ] Stabilization report compiled
- [ ] Go/No-Go decision for P3

### Optional Deliverables

- [ ] Weekly monitoring protocol
- [ ] Alert thresholds defined
- [ ] Incident response playbook

---

## ✅ Sign-Off

**Stabilization Phase**: ⏳ IN PROGRESS

**Expected Completion**: 2025-10-28 (72 hours from now)

**Next Phase**: P3 Sprint – Alert System (conditional on stabilization success)

---

**Phase Owner**: Claude Code
**Stakeholder**: [Your Name]
**Start Date**: 2025-10-25
**Target End**: 2025-10-28
**Status**: Deployment executing...
