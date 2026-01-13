# Production Deployment Guide

**Application:** LFA Internship Practice Booking System
**Security Status:** ✅ Production Ready (307/307 security tests passing)
**Date:** 2026-01-11

---

## Prerequisites

- [x] All security audits complete (SQL Injection, XSS, CSRF)
- [x] All 307 security tests passing (100%)
- [x] Bearer token authentication unified (74 API calls)
- [x] CSRF protection implemented and tested
- [x] Functional tests passed (Bearer auth verified)

---

## Production Configuration

### 1. Environment Variables

Create `.env.production` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@production-db-host:5432/lfa_intern_system

# Security - CRITICAL SETTINGS
COOKIE_SECURE=True  # ⚠️ REQUIRED for production (HTTPS only)
COOKIE_SAMESITE=strict
COOKIE_HTTPONLY=True
COOKIE_MAX_AGE=3600

# CORS - Update with production domains
CORS_ALLOWED_ORIGINS=["https://lfa-education.com", "https://app.lfa-education.com"]

# JWT
SECRET_KEY=<generate-strong-random-key-here>  # Use: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# API Configuration
API_BASE_URL=https://api.lfa-education.com
```

### 2. Generate Production Secret Key

```bash
# Generate strong SECRET_KEY
openssl rand -hex 32

# Example output:
# a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0
```

### 3. SSL/TLS Certificate

**Required for COOKIE_SECURE=True**

```bash
# Option 1: Let's Encrypt (Free)
sudo certbot --nginx -d lfa-education.com -d app.lfa-education.com

# Option 2: Commercial certificate
# - Purchase from CA (DigiCert, Comodo, etc.)
# - Install certificate files
# - Configure nginx/apache
```

### 4. CORS Configuration

Update `app/config.py` or use environment variable:

```python
# Development (localhost)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://localhost:8000"
]

# Production (replace with actual domains)
CORS_ALLOWED_ORIGINS = [
    "https://lfa-education.com",
    "https://app.lfa-education.com",
    "https://admin.lfa-education.com"
]
```

---

## Deployment Steps

### Step 1: Build and Test

```bash
# 1. Clone repository
git clone <repository-url>
cd practice_booking_system

# 2. Checkout production branch
git checkout main  # or production branch

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run security tests
pytest tests/security/ -v

# Expected: 307/307 tests passing
```

### Step 2: Database Setup

```bash
# 1. Create production database
psql -U postgres -c "CREATE DATABASE lfa_intern_system;"

# 2. Run migrations
export DATABASE_URL="postgresql://user:pass@host:5432/lfa_intern_system"
alembic upgrade head

# 3. Verify database schema
psql $DATABASE_URL -c "\dt"
```

### Step 3: Configure Web Server (nginx)

Create `/etc/nginx/sites-available/lfa-education`:

```nginx
# FastAPI Backend
server {
    listen 443 ssl http2;
    server_name api.lfa-education.com;

    ssl_certificate /etc/letsencrypt/live/api.lfa-education.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.lfa-education.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Streamlit Frontend
server {
    listen 443 ssl http2;
    server_name app.lfa-education.com;

    ssl_certificate /etc/letsencrypt/live/app.lfa-education.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.lfa-education.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.lfa-education.com app.lfa-education.com;
    return 301 https://$server_name$request_uri;
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/lfa-education /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: Start Services

#### FastAPI (systemd service)

Create `/etc/systemd/system/lfa-api.service`:

```ini
[Unit]
Description=LFA Education API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/lfa-education
Environment="DATABASE_URL=postgresql://user:pass@localhost:5432/lfa_intern_system"
Environment="COOKIE_SECURE=True"
Environment="CORS_ALLOWED_ORIGINS=[\"https://app.lfa-education.com\"]"
ExecStart=/var/www/lfa-education/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lfa-api
sudo systemctl start lfa-api
sudo systemctl status lfa-api
```

#### Streamlit (systemd service)

Create `/etc/systemd/system/lfa-streamlit.service`:

```ini
[Unit]
Description=LFA Education Streamlit App
After=network.target lfa-api.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/lfa-education/streamlit_app
ExecStart=/var/www/lfa-education/venv/bin/streamlit run 🏠_Home.py --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lfa-streamlit
sudo systemctl start lfa-streamlit
sudo systemctl status lfa-streamlit
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# API health
curl https://api.lfa-education.com/health

# Expected: {"status": "healthy"}

# API docs (verify accessible)
curl -I https://api.lfa-education.com/docs

# Expected: 200 OK
```

### 2. Security Verification

```bash
# 1. Verify HTTPS redirect
curl -I http://api.lfa-education.com
# Expected: 301 redirect to https://

# 2. Check SSL certificate
openssl s_client -connect api.lfa-education.com:443 -servername api.lfa-education.com

# 3. Verify CORS headers
curl -I -X OPTIONS https://api.lfa-education.com/api/v1/users \
  -H "Origin: https://app.lfa-education.com" \
  -H "Access-Control-Request-Method: GET"

# Expected: Access-Control-Allow-Origin: https://app.lfa-education.com

# 4. Verify Secure cookies (check browser DevTools)
# - Navigate to https://app.lfa-education.com
# - Login
# - Open DevTools → Application → Cookies
# - Verify: Secure=✓, SameSite=Strict
```

### 3. Functional Tests

```bash
# Run production tests against live API
export API_BASE_URL=https://api.lfa-education.com
python test_bearer_auth.py

# Expected: All tests pass ✅
```

### 4. Monitor Logs

```bash
# FastAPI logs
sudo journalctl -u lfa-api -f

# Streamlit logs
sudo journalctl -u lfa-streamlit -f

# Nginx access/error logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Security Monitoring

### 1. Set Up Alerts

Monitor for:
- **403 CSRF errors** (potential attack attempts)
- **CORS preflight failures** (unauthorized origins)
- **Token validation failures** (potential brute force)
- **Failed login attempts** (credential stuffing)

### 2. Log Analysis

```bash
# Count CSRF errors (should be low in production)
sudo journalctl -u lfa-api | grep "CSRF" | wc -l

# Check for suspicious CORS attempts
sudo journalctl -u lfa-api | grep "CORS" | grep -v "localhost:8501"

# Monitor authentication failures
sudo journalctl -u lfa-api | grep "401" | tail -20
```

### 3. Automated Security Scans

```bash
# OWASP ZAP automated scan
zap-cli quick-scan https://api.lfa-education.com

# Nikto web server scanner
nikto -h https://api.lfa-education.com
```

---

## Rollback Procedure

If critical issues arise:

```bash
# 1. Stop services
sudo systemctl stop lfa-api lfa-streamlit

# 2. Rollback to previous version
cd /var/www/lfa-education
git checkout <previous-stable-tag>

# 3. Restore database (if needed)
psql $DATABASE_URL < backup_YYYYMMDD.sql

# 4. Restart services
sudo systemctl start lfa-api lfa-streamlit

# 5. Verify rollback
curl https://api.lfa-education.com/health
```

---

## Performance Tuning

### Database Connection Pooling

Update `app/database.py`:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Production pool size
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600  # Recycle connections after 1 hour
)
```

### Gunicorn (Production WSGI)

Replace `uvicorn` with `gunicorn + uvicorn workers`:

```bash
# Install gunicorn
pip install gunicorn

# Update systemd service
ExecStart=/var/www/lfa-education/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/lfa-api/access.log \
    --error-logfile /var/log/lfa-api/error.log
```

---

## Backup Strategy

### Database Backups

```bash
# Daily automated backup (cron job)
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/lfa_$(date +\%Y\%m\%d).sql.gz

# Keep last 30 days
find /backups/ -name "lfa_*.sql.gz" -mtime +30 -delete
```

### Application Backups

```bash
# Backup application files
tar -czf /backups/app_$(date +%Y%m%d).tar.gz /var/www/lfa-education

# Backup environment config
cp .env.production /backups/env_$(date +%Y%m%d).backup
```

---

## Support and Maintenance

### Regular Tasks

**Daily:**
- Monitor error logs
- Check service status
- Review authentication failures

**Weekly:**
- Review security logs for anomalies
- Check disk space and performance
- Update dependencies (security patches)

**Monthly:**
- Full security audit review
- Database optimization (VACUUM, REINDEX)
- SSL certificate expiry check

### Emergency Contacts

- **DevOps Team:** devops@lfa-education.com
- **Security Team:** security@lfa-education.com
- **On-Call:** +1-XXX-XXX-XXXX

---

## Checklist

Use this checklist for production deployment:

### Pre-Deployment
- [ ] All 307 security tests passing
- [ ] Functional tests passed (test_bearer_auth.py)
- [ ] `.env.production` configured
- [ ] SSL certificates obtained and installed
- [ ] CORS origins updated for production domains
- [ ] Database backup created
- [ ] Rollback procedure documented

### Deployment
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Services started and healthy
- [ ] nginx configured and running
- [ ] HTTPS redirect working
- [ ] Health endpoints responding

### Post-Deployment
- [ ] HTTPS verification (no mixed content)
- [ ] Secure cookies verified (DevTools)
- [ ] CORS headers correct
- [ ] Bearer token authentication working
- [ ] Login/logout flow tested
- [ ] Admin functions tested (invitation codes, coupons, etc.)
- [ ] Monitoring and alerts configured
- [ ] Backup jobs scheduled

### Security Verification
- [ ] 403 CSRF errors monitored (should be zero)
- [ ] CORS preflight working for allowed origins
- [ ] CORS blocking unauthorized origins
- [ ] Cookie security attributes verified
- [ ] SSL/TLS configuration verified (A+ rating on SSL Labs)

---

## Summary

**Production Deployment Status:** ✅ Ready

- **Security:** 307/307 tests passing (SQL Injection, XSS, CSRF)
- **Authentication:** Bearer token (CSRF-safe)
- **Configuration:** Environment-based (.env.production)
- **Infrastructure:** nginx + systemd + PostgreSQL
- **Monitoring:** Logs + alerts configured
- **Backup:** Automated daily backups

**Estimated Deployment Time:** 2-3 hours (including verification)

**Next Steps:**
1. Schedule deployment window
2. Notify users of maintenance
3. Execute deployment steps
4. Verify all checklist items
5. Monitor for 24 hours post-deployment

---

**Document Version:** 1.0
**Last Updated:** 2026-01-11
**Status:** Production Ready ✅
