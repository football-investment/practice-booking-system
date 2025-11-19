# ✅ Phase 1-2 Execution Checklist

**Sprint**: P2 Production Readiness
**Phases**: Staging Deployment + Load Testing
**Timeline**: 2-4 days
**Date**: 2025-10-25
**Status**: READY TO EXECUTE

---

## 📋 Overview

This checklist provides step-by-step instructions for executing **Phase 1 (Staging Deployment)** and **Phase 2 (Load Testing)**.

### Phases Covered

1. **Phase 1**: Staging Deployment with 10K anonymized users
2. **Phase 2**: Load & Performance Testing with 3 Locust scripts

### Success Criteria

**Phase 1**:
- ✅ Staging environment deployed
- ✅ 10K anonymized users imported
- ✅ Backend tests: 6/6 passing
- ✅ Frontend E2E tests: 12/12 passing

**Phase 2**:
- ✅ Progress update load test: <100ms median
- ✅ Coupling enforcer stress test: 0 desync issues
- ✅ Health dashboard load test: <50ms median
- ✅ All performance benchmarks met

---

## 🚀 Phase 1: Staging Deployment

### Day 1: Environment Setup

#### Step 1.1: Provision Staging Server

**Option A: Cloud (AWS/GCP/Azure)**
```bash
# Create EC2 instance (or equivalent)
# - Instance type: t3.medium (2 vCPU, 4GB RAM)
# - OS: Ubuntu 22.04 LTS
# - Storage: 50GB SSD
# - Security groups: HTTP(80), HTTPS(443), PostgreSQL(5432)

# SSH into server
ssh -i staging-key.pem ubuntu@staging-server-ip
```

**Option B: Docker Compose (Local/VM)**
```bash
# Use existing docker-compose.yml
docker-compose -f docker-compose.staging.yml up -d
```

#### Step 1.2: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install PostgreSQL 14
sudo apt install postgresql-14 postgresql-contrib -y

# Install Nginx
sudo apt install nginx -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Verify installations
python3 --version  # Expected: Python 3.11.x
psql --version     # Expected: PostgreSQL 14.x
nginx -v           # Expected: nginx 1.x
node -v            # Expected: v18.x
npm -v             # Expected: 9.x
```

#### Step 1.3: Setup Database

```bash
# Create staging database
sudo -u postgres psql <<EOF
CREATE DATABASE practice_booking_staging;
CREATE USER staging_user WITH ENCRYPTED PASSWORD 'staging_password';
GRANT ALL PRIVILEGES ON DATABASE practice_booking_staging TO staging_user;
EOF

# Verify database created
sudo -u postgres psql -l | grep staging
```

#### Step 1.4: Clone Repository

```bash
# Clone repo
cd /opt
sudo git clone https://github.com/your-org/practice-booking-system.git
cd practice-booking-system

# Checkout main branch
git checkout main
git pull origin main

# Verify latest commit
git log -1
```

---

### Day 1: Backend Deployment

#### Step 1.5: Configure Environment

```bash
# Create .env.staging
cat > .env.staging <<EOF
# Database
DATABASE_URL=postgresql://staging_user:staging_password@localhost:5432/practice_booking_staging

# Auth
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Environment
ENVIRONMENT=staging

# CORS (adjust domain)
ALLOWED_ORIGINS=https://staging.yourdomain.com,http://localhost:3000

# Logging
LOG_LEVEL=INFO
EOF

# Load environment variables
export $(cat .env.staging | xargs)
```

#### Step 1.6: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|sqlalchemy|alembic|uvicorn"
```

#### Step 1.7: Run Migrations

```bash
# Apply all migrations
alembic upgrade head

# Verify migrations applied
alembic current
# Expected: fc73d1aca3f3 (head) + P0/P1/P2 migrations
```

#### Step 1.8: Import Anonymized Data

**Option A: From Production Dump**
```bash
# On production server: Export anonymized data
pg_dump -h production-db -U user -d practice_booking \
  --table=users --table=specialization_progress --table=user_licenses \
  --data-only \
  | sed 's/@.*\.com/@staging.example.com/g' \
  > staging_data.sql

# Transfer to staging
scp staging_data.sql ubuntu@staging-server:/tmp/

# On staging server: Import data
psql -h localhost -U staging_user -d practice_booking_staging < /tmp/staging_data.sql

# Verify data imported
psql -h localhost -U staging_user -d practice_booking_staging -c "SELECT COUNT(*) FROM users;"
# Expected: 10,000+ users
```

**Option B: Generate Synthetic Data**
```bash
# Run data generation script
python3 scripts/generate_staging_data.py --users=10000

# Verify data
psql -h localhost -U staging_user -d practice_booking_staging -c "
SELECT
  (SELECT COUNT(*) FROM users) AS users,
  (SELECT COUNT(*) FROM specialization_progress) AS progress,
  (SELECT COUNT(*) FROM user_licenses) AS licenses;
"
```

#### Step 1.9: Start Backend Service

```bash
# Start uvicorn manually (for testing)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# OR create systemd service
sudo tee /etc/systemd/system/practice-booking-staging.service <<EOF
[Unit]
Description=Practice Booking API (Staging)
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/practice-booking-system
Environment="PATH=/opt/practice-booking-system/venv/bin"
ExecStart=/opt/practice-booking-system/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl start practice-booking-staging
sudo systemctl enable practice-booking-staging

# Check status
sudo systemctl status practice-booking-staging
```

#### Step 1.10: Verify Backend Endpoints

```bash
# Test health endpoint (should return 404 for now, no token)
curl -I http://localhost:8000/

# Expected: HTTP 200 OK or 404 (endpoint not found is ok)

# Test login endpoint
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@staging.example.com","password":"admin_password"}'

# Expected: {"access_token":"..."}

# Save token
export TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@staging.example.com","password":"admin_password"}' \
  | jq -r '.access_token')

# Test health endpoint with auth
curl http://localhost:8000/api/v1/health/status \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"status":"unknown",...} (no checks run yet)
```

---

### Day 2: Frontend Deployment

#### Step 1.11: Build Frontend

```bash
# On local machine (or build server)
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Verify build
ls -lh build/
# Expected: build/static/js/main.*.js, build/static/css/main.*.css
```

#### Step 1.12: Deploy to Staging Server

```bash
# Transfer build to staging server
rsync -av --delete build/ ubuntu@staging-server:/var/www/staging/

# OR if using Docker
docker cp build/. staging-frontend:/usr/share/nginx/html/
```

#### Step 1.13: Configure Nginx

```bash
# On staging server
sudo tee /etc/nginx/sites-available/staging <<EOF
server {
    listen 80;
    server_name staging.yourdomain.com;

    # Frontend
    location / {
        root /var/www/staging;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/staging /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### Step 1.14: Setup SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d staging.yourdomain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

#### Step 1.15: Verify Frontend Access

```bash
# Test frontend loads
curl -I https://staging.yourdomain.com/

# Expected: HTTP 200 OK

# Test admin dashboard route
curl -I https://staging.yourdomain.com/admin/health

# Expected: HTTP 200 OK (after login)
```

---

### Day 2: Run Backend Workflow Tests

#### Step 1.16: Execute Backend Tests

```bash
# SSH into staging server
ssh ubuntu@staging-server

# Navigate to project directory
cd /opt/practice-booking-system

# Activate venv
source venv/bin/activate

# Run backend workflow tests
export PYTHONPATH=venv/lib/python3.11/site-packages:.
python3 scripts/test_backend_workflow.py

# Expected output:
# ✅ PASS | User Creation + Specialization Assignment
# ✅ PASS | Progress Update → Auto-Sync Hook
# ✅ PASS | Multiple Level-Ups + XP Changes
# ✅ PASS | Desync Injection → Auto-Sync → Validation
# ✅ PASS | Health Monitoring Service
# ✅ PASS | Coupling Enforcer Atomic Update
#
# 📊 TEST SUMMARY
# Total Tests: 6
# ✅ Passed: 6
# ❌ Failed: 0
# Success Rate: 100.0%
```

**✅ Checklist Item**: Backend tests 6/6 passing

---

### Day 2: Run Frontend E2E Tests

#### Step 1.17: Install Cypress

```bash
# On local machine (or CI server)
cd frontend

# Install Cypress if not installed
npm install --save-dev cypress

# Verify Cypress installed
npx cypress --version
```

#### Step 1.18: Configure Cypress for Staging

```bash
# Create cypress.staging.json
cat > cypress.staging.json <<EOF
{
  "baseUrl": "https://staging.yourdomain.com",
  "env": {
    "apiUrl": "https://staging.yourdomain.com/api/v1",
    "adminEmail": "admin@staging.example.com",
    "adminPassword": "admin_password"
  }
}
EOF
```

#### Step 1.19: Execute Cypress Tests

```bash
# Run headless
npx cypress run \
  --config-file cypress.staging.json \
  --spec "cypress/e2e/health_dashboard.cy.js"

# Expected output:
#   ✓ should navigate to health dashboard from admin dashboard (2.1s)
#   ✓ should render all dashboard components correctly (1.5s)
#   ✓ should display color-coded status badge (1.2s)
#   ✓ should render consistency gauge with correct data (1.8s)
#   ✓ should display metrics card with current data (1.4s)
#   ✓ should trigger manual health check when button clicked (25.3s)
#   ✓ should display violations table or no violations banner (1.6s)
#   ✓ should auto-refresh data every 30 seconds (32.5s)
#   ✓ should handle API errors gracefully (1.3s)
#   ✓ should render correctly on mobile devices (1.9s)
#   ✓ should display accurate system info (1.2s)
#   ✓ should complete full workflow (35.8s)
#
# 12 passing (1m 47s)
```

**✅ Checklist Item**: Frontend E2E tests 12/12 passing

---

## 🔥 Phase 2: Load & Performance Testing

### Day 3: Setup Load Testing Tools

#### Step 2.1: Install Locust

```bash
# On local machine or dedicated load testing server
pip install locust

# Verify installation
locust --version

# Expected: locust 2.x.x
```

#### Step 2.2: Verify Locust Scripts

```bash
# Check scripts exist
ls -la scripts/load_test_*.py

# Expected:
# load_test_progress_update.py
# load_test_coupling_enforcer.py
# load_test_health_dashboard.py
```

---

### Day 3: Run Load Tests

#### Step 2.3: Test 1 - Progress Update Storm

```bash
# Run load test: 1,000 concurrent users, 10 minutes
locust -f scripts/load_test_progress_update.py \
  --host=https://staging.yourdomain.com \
  --users=1000 \
  --spawn-rate=50 \
  --run-time=10m \
  --headless \
  --html=logs/load_tests/progress_update_storm_$(date +%Y%m%d_%H%M%S).html

# Expected metrics:
# - Requests/sec: >500
# - Median Response Time: <100ms
# - 95th Percentile: <500ms
# - Failure Rate: <1%
```

**✅ Checklist Item**: Progress update load test completed

#### Step 2.4: Test 2 - Coupling Enforcer Stress

```bash
# Run stress test: 500 concurrent users, 5 minutes
locust -f scripts/load_test_coupling_enforcer.py \
  --host=https://staging.yourdomain.com \
  --users=500 \
  --spawn-rate=100 \
  --run-time=5m \
  --headless \
  --html=logs/load_tests/coupling_enforcer_stress_$(date +%Y%m%d_%H%M%S).html

# Expected results:
# - Latency < 200ms
# - No deadlocks
# - No race conditions
```

**After test, verify consistency**:
```bash
# SSH into staging
ssh ubuntu@staging-server

# Run health check
curl -X POST https://staging.yourdomain.com/api/v1/health/check-now \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected: "inconsistent": 0 (no desync issues from stress test)
```

**✅ Checklist Item**: Coupling enforcer stress test completed, 0 desync issues

#### Step 2.5: Test 3 - Health Dashboard Load

```bash
# Run dashboard load test: 100 concurrent admins, 10 minutes
locust -f scripts/load_test_health_dashboard.py \
  --host=https://staging.yourdomain.com \
  --users=100 \
  --spawn-rate=20 \
  --run-time=10m \
  --headless \
  --html=logs/load_tests/health_dashboard_load_$(date +%Y%m%d_%H%M%S).html

# Expected metrics:
# - Requests/sec: >200
# - Median Response Time: <50ms
# - Manual Check Time: <15s
# - Failure Rate: <0.1%
```

**✅ Checklist Item**: Health dashboard load test completed

---

### Day 4: Analyze Results & Create Report

#### Step 2.6: Review Load Test Reports

```bash
# Open HTML reports in browser
open logs/load_tests/progress_update_storm_*.html
open logs/load_tests/coupling_enforcer_stress_*.html
open logs/load_tests/health_dashboard_load_*.html

# Review metrics:
# - Requests/sec
# - Response times (median, 95th percentile)
# - Failure rates
# - Errors and exceptions
```

#### Step 2.7: Check System Metrics

```bash
# SSH into staging server
ssh ubuntu@staging-server

# Check CPU/Memory during load
htop

# Check database connections
sudo -u postgres psql -d practice_booking_staging -c "
SELECT count(*) AS connections FROM pg_stat_activity;
"
# Expected: <100 connections

# Check logs for errors
tail -100 logs/app.log | grep ERROR
# Expected: No critical errors
```

#### Step 2.8: Compile Load Test Report

```bash
# Create report from template
cat > logs/load_tests/LOAD_TEST_REPORT_$(date +%Y%m%d).md <<EOF
# Load Testing Report - P2 Health Dashboard

**Date**: $(date)
**Duration**: Day 3-4
**Environment**: Staging

## Test Configuration

- **Server**: staging.yourdomain.com
- **Users (Data)**: 10,000
- **Database**: PostgreSQL 14

## Results Summary

### Test 1: Progress Update Storm

- **Users**: 1,000
- **Duration**: 10 minutes
- **Total Requests**: [FROM REPORT]
- **Requests/sec**: [FROM REPORT]
- **Median Response Time**: [FROM REPORT]
- **95th Percentile**: [FROM REPORT]
- **Failure Rate**: [FROM REPORT]

**Status**: ✅ PASS (if all metrics met)

### Test 2: Coupling Enforcer Stress

- **Users**: 500
- **Duration**: 5 minutes
- **Total Requests**: [FROM REPORT]
- **Concurrent Updates**: Same 100 users
- **Desync Issues**: 0 (verified post-test)
- **Deadlocks**: 0
- **Median Latency**: [FROM REPORT]

**Status**: ✅ PASS (if 0 desync)

### Test 3: Health Dashboard Load

- **Users**: 100
- **Duration**: 10 minutes
- **Total Requests**: [FROM REPORT]
- **Endpoints Tested**: 4 (/status, /metrics, /violations, /check-now)
- **Manual Checks Triggered**: [FROM REPORT]
- **Avg Manual Check Duration**: [FROM REPORT]

**Status**: ✅ PASS (if all metrics met)

## Performance Benchmarks

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Progress Update Latency | <100ms | [FILL] | ✅/❌ |
| Health Check Latency | <50ms | [FILL] | ✅/❌ |
| Manual Check Duration | <20s | [FILL] | ✅/❌ |
| Coupling Enforcer Desync | 0 | 0 | ✅ |
| CPU Usage (max) | <60% | [FILL] | ✅/❌ |
| Memory Usage (max) | <4GB | [FILL] | ✅/❌ |

## Recommendation

**Proceed to Phase 3 (Security)**: YES / NO

**Reasoning**: [Based on results]
EOF
```

---

## ✅ Phase 1-2 Completion Checklist

### Phase 1: Staging Deployment

- [ ] Staging server provisioned
- [ ] Database created and configured
- [ ] Backend deployed and running
- [ ] Frontend built and deployed
- [ ] SSL certificate configured
- [ ] 10K anonymized users imported
- [ ] Backend tests: 6/6 passing
- [ ] Frontend E2E tests: 12/12 passing

### Phase 2: Load Testing

- [ ] Locust installed
- [ ] Progress update storm test completed
- [ ] Coupling enforcer stress test completed
- [ ] Health dashboard load test completed
- [ ] All performance benchmarks met
- [ ] 0 desync issues verified
- [ ] System metrics analyzed
- [ ] Load test report compiled

---

## 🎯 Success Criteria

**Phase 1 Complete** ✅:
- All backend tests passing (6/6)
- All frontend E2E tests passing (12/12)
- Staging environment fully operational

**Phase 2 Complete** ✅:
- Progress update latency < 100ms
- Health check latency < 50ms
- Manual check duration < 20s
- Coupling enforcer: 0 desync issues
- CPU usage < 60%
- Memory usage < 4GB
- All load test reports compiled

**Ready for Phase 3** ✅:
- All Phase 1 criteria met
- All Phase 2 criteria met
- Load test report shows PASS for all tests
- No critical issues discovered

---

## 📚 Related Documentation

- [P2_PRODUCTION_READINESS.md](P2_PRODUCTION_READINESS.md:1) – Full 5-phase plan
- [test_backend_workflow.py](scripts/test_backend_workflow.py:1) – Backend integration tests
- [health_dashboard.cy.js](frontend/cypress/e2e/health_dashboard.cy.js:1) – Frontend E2E tests
- [load_test_progress_update.py](scripts/load_test_progress_update.py:1) – Load test script 1
- [load_test_coupling_enforcer.py](scripts/load_test_coupling_enforcer.py:1) – Load test script 2
- [load_test_health_dashboard.py](scripts/load_test_health_dashboard.py:1) – Load test script 3

---

**Last Updated**: 2025-10-25
**Status**: READY TO EXECUTE
**Timeline**: 2-4 days
**Next Phase**: Phase 3 (Security & Edge Case Hardening)
