# 📈 SLOW QUERY MONITORING GUIDE

**Dátum**: 2025-12-17
**Típus**: Performance Monitoring Setup Guide
**Státusz**: ✅ **READY TO USE**

---

## 🎯 ÁTTEKINTÉS

Ez a guide bemutatja, hogyan kell használni a slow query monitoring rendszert a Practice Booking System-ben.

**Amit nyújt**:
- ✅ Automatikus slow query logging
- ✅ N+1 query pattern detection
- ✅ Per-request query statistics
- ✅ Performance headers HTTP response-okban
- ✅ Részletes log fájlok

---

## 📁 LÉTREHOZOTT FÁJLOK

### 1. Query Logger (`app/middleware/query_logger.py`)
**Funkció**: SQLAlchemy event listener-ek, query monitoring logika

**Key Features**:
- Query execution time tracking
- Slow query threshold (default: 100ms)
- N+1 pattern detection
- Query statistics aggregation

### 2. Performance Middleware (`app/middleware/performance_middleware.py`)
**Funkció**: FastAPI middleware integráció

**Key Features**:
- Request duration tracking
- Automatic query monitoring per request
- Performance headers in HTTP response
- Slow request logging (default: 1000ms threshold)

### 3. Log Directory (`logs/`)
**Fájlok**:
- `logs/slow_queries.log` - Slow query log

---

## 🚀 HASZNÁLAT

### Opció 1: FastAPI Middleware (AJÁNLOTT - Automatikus)

**app/main.py** módosítása:

```python
from fastapi import FastAPI
from app.middleware.performance_middleware import PerformanceMonitoringMiddleware

app = FastAPI()

# Add performance monitoring middleware
app.add_middleware(
    PerformanceMonitoringMiddleware,
    slow_request_threshold_ms=1000,  # 1 second threshold
    enable_headers=True  # Add X-Query-Count, X-Query-Time-Ms headers
)

# ... rest of your app setup
```

**Mit csinál**:
- ✅ Minden API request automatikusan monitorozva
- ✅ Query count és execution time logolva
- ✅ Slow requests automatikusan logolva
- ✅ N+1 patterns automatikusan detektálva
- ✅ Performance headers hozzáadva minden response-hoz

**HTTP Response Headers** (automatikusan):
```
X-Request-Duration-Ms: 245.67
X-Query-Count: 12
X-Query-Time-Ms: 189.34
```

---

### Opció 2: Manual Context Manager (Specifikus használat)

Ha csak bizonyos endpoint-okat akarsz monitorozni:

```python
from app.middleware.query_logger import monitor_queries

@app.get("/sessions/")
def list_sessions(db: Session = Depends(get_db)):
    with monitor_queries("GET /sessions/"):
        # Your database operations
        sessions = db.query(SessionModel).all()

        # Any additional queries
        stats = get_session_stats(db, sessions)

        return sessions

    # Context manager automatically logs:
    # - Total queries executed
    # - Total query time
    # - N+1 pattern detection
```

---

## 📊 LOG OUTPUT PÉLDÁK

### Normal Request (Fast)

```
2025-12-17 14:30:15 - performance_middleware - INFO - GET /sessions/ | Duration: 45.23ms | Queries: 2 | DB Time: 23.45ms
```

### Slow Request (Warning)

```
2025-12-17 14:30:20 - performance_middleware - WARNING - SLOW REQUEST (1234.56ms): GET /sessions/ | Queries: 15 | DB Time: 987.12ms
```

### Slow Query (Warning)

```
2025-12-17 14:30:22 - slow_query_monitor - WARNING - SLOW QUERY (156.78ms): SELECT * FROM sessions WHERE ...
```

### N+1 Pattern Detected (Error)

```
2025-12-17 14:30:25 - slow_query_monitor - ERROR - N+1 QUERY PATTERN DETECTED: 50 similar queries in single request

2025-12-17 14:30:25 - slow_query_monitor - ERROR - N+1 PATTERN in GET /reports/export-csv: 501 queries executed
```

### High Query Count (Warning)

```
2025-12-17 14:30:30 - slow_query_monitor - WARNING - HIGH QUERY COUNT in GET /users/123/details: 45 queries |
Queries: [
  {"query_number": 1, "duration_ms": 12.34, "statement": "SELECT * FROM users WHERE id = 123"},
  {"query_number": 2, "duration_ms": 8.91, "statement": "SELECT * FROM bookings WHERE user_id = 123"},
  ...
]
```

---

## 🔧 KONFIGURÁCIÓ

### Query Logger Settings

```python
from app.middleware.query_logger import QueryMonitor

# Custom threshold for slow queries
monitor = QueryMonitor(slow_query_threshold_ms=150)  # 150ms instead of default 100ms
```

### Middleware Settings

```python
app.add_middleware(
    PerformanceMonitoringMiddleware,
    slow_request_threshold_ms=2000,  # 2 second threshold for slow requests
    enable_headers=False  # Disable performance headers (production)
)
```

---

## 🎯 THRESHOLD RECOMMENDATIONS

| Environment | Slow Query | Slow Request | Headers |
|-------------|------------|--------------|---------|
| **Development** | 50ms | 500ms | ✅ ON |
| **Staging** | 100ms | 1000ms | ✅ ON |
| **Production** | 200ms | 2000ms | ❌ OFF |

**Miért OFF a headers production-ban?**
- Csökkenti response size-t
- Nem expozálja internal metrics-eket

---

## 📈 HOGYAN HASZNÁLD AZ ADATOKAT

### 1. Identify Slow Endpoints

**Log-ból**:
```bash
# List top 10 slowest requests
grep "SLOW REQUEST" logs/slow_queries.log | head -10
```

**Mit csinálj**:
- Nézd meg a query count-ot
- Ha >20 queries, N+1 pattern gyanú
- Check API Endpoint Audit dokumentációt ([docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md](docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md))

---

### 2. Detect N+1 Patterns

**Log-ból**:
```bash
# Find all N+1 patterns
grep "N+1 PATTERN" logs/slow_queries.log
```

**Mit csinálj**:
1. Check az endpoint kódját
2. Add eager loading: `query.options(joinedload(...))`
3. Vagy használj batch fetching (GROUP BY)
4. Lásd: [API Endpoint Audit - Best Practice Template](docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md#best-practice-template)

---

### 3. Find Slow Queries

**Log-ból**:
```bash
# List all slow queries
grep "SLOW QUERY" logs/slow_queries.log
```

**Mit csinálj**:
1. Check az SQL statement-et
2. Add index ha hiányzik
3. Optimalizáld a query-t (SELECT specific fields, not *)
4. Lásd: [Database Audit - Missing Indexes](docs/CURRENT/DATABASE_STRUCTURE_AUDIT_COMPLETE.md#missing-indexes)

---

### 4. Monitor Query Count per Endpoint

**Log-ból**:
```bash
# Get query count distribution
grep "Queries:" logs/slow_queries.log | awk '{print $NF}' | sort -n | uniq -c
```

**Eredmény**:
```
   100   Queries: 1
    45   Queries: 2
    20   Queries: 5
    10   Queries: 12
     5   Queries: 50    # ⚠️ RED FLAG!
     2   Queries: 501   # 🔥 N+1 PATTERN!
```

---

## 🚨 ALERT SZABÁLYOK

### Critical Alerts (Immediate Action)

| Metric | Threshold | Action |
|--------|-----------|--------|
| **N+1 Pattern** | Detected | Fix immediately (see API Audit) |
| **Query Count** | >50 | Investigate + optimize |
| **Request Time** | >5000ms | Critical performance issue |

### Warning Alerts (Fix Soon)

| Metric | Threshold | Action |
|--------|-----------|--------|
| **Query Count** | >20 | Review endpoint logic |
| **Slow Query** | >200ms | Add index or optimize |
| **Request Time** | >2000ms | Performance degradation |

---

## 📝 INTEGRATION CHECKLIST

### Backend Integration

- [ ] Add `PerformanceMonitoringMiddleware` to `app/main.py`
- [ ] Configure thresholds (dev: 100ms, prod: 200ms)
- [ ] Verify `logs/` directory exists
- [ ] Test with `/sessions/` endpoint
- [ ] Check `logs/slow_queries.log` for output

### Production Setup

- [ ] Set `enable_headers=False` in production
- [ ] Set `slow_request_threshold_ms=2000` (2 seconds)
- [ ] Configure log rotation (logrotate)
- [ ] Set up monitoring/alerting (Datadog, Sentry, etc.)
- [ ] Add log aggregation (ELK, Splunk, etc.)

---

## 🔍 TESTING

### Manual Test

1. Start backend:
```bash
./start_backend.sh
```

2. Make API request:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/sessions/
```

3. Check response headers:
```bash
curl -I -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/sessions/
# Look for:
# X-Request-Duration-Ms: 245.67
# X-Query-Count: 2
# X-Query-Time-Ms: 123.45
```

4. Check logs:
```bash
tail -f logs/slow_queries.log
```

---

### Automated Test

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_performance_headers():
    """Test that performance headers are added"""
    response = client.get("/api/v1/sessions/")

    assert "X-Request-Duration-Ms" in response.headers
    assert "X-Query-Count" in response.headers
    assert "X-Query-Time-Ms" in response.headers

    # Check values are reasonable
    duration_ms = float(response.headers["X-Request-Duration-Ms"])
    assert duration_ms < 1000  # Request should be < 1 second

    query_count = int(response.headers["X-Query-Count"])
    assert query_count < 10  # Should not have N+1 pattern
```

---

## 📊 EXAMPLE USAGE SCENARIOS

### Scenario 1: Debug Slow Endpoint

**Problem**: `/api/v1/reports/export-csv` takes 5 seconds

**Steps**:
1. Check logs:
```bash
grep "GET /reports/export-csv" logs/slow_queries.log
```

2. Output shows:
```
SLOW REQUEST (5234.56ms): GET /reports/export-csv | Queries: 501 | DB Time: 4987.12ms
N+1 PATTERN DETECTED: 500 similar queries in single request
```

3. **Root Cause**: N+1 pattern (5N+1 queries!)

4. **Fix**: Apply batch fetching from [API Endpoint Audit](docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md#1-reportspy---csv-export-endpoint)

5. **Verify**: After fix, re-run and check logs:
```
GET /reports/export-csv | Duration: 127.89ms | Queries: 4 | DB Time: 89.23ms
```

6. **Result**: **5234ms → 128ms** (97.5% improvement!) ✅

---

### Scenario 2: Find Missing Indexes

**Problem**: Specific queries consistently slow

**Steps**:
1. Check slow query logs:
```bash
grep "SLOW QUERY" logs/slow_queries.log | sort | uniq -c | sort -rn | head -5
```

2. Output shows:
```
45  SLOW QUERY (234.56ms): SELECT * FROM attendance WHERE check_in_time > '2025-01-01'
```

3. **Root Cause**: Missing index on `attendance.check_in_time`

4. **Fix**: Add index (already done in migration `2025_12_17_1430-add_performance_indexes.py`)

5. **Verify**: After migration:
```
INFO: Query (12.34ms): SELECT * FROM attendance WHERE check_in_time > '2025-01-01'
```

6. **Result**: **234ms → 12ms** (95% improvement!) ✅

---

## 🔗 RELATED DOCUMENTATION

- **API Endpoint Audit**: [docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md](docs/CURRENT/API_ENDPOINT_AUDIT_COMPLETE.md) - N+1 fixes
- **Database Audit**: [docs/CURRENT/DATABASE_STRUCTURE_AUDIT_COMPLETE.md](docs/CURRENT/DATABASE_STRUCTURE_AUDIT_COMPLETE.md) - Missing indexes
- **Testing Coverage Audit**: [docs/CURRENT/TESTING_COVERAGE_AUDIT_COMPLETE.md](docs/CURRENT/TESTING_COVERAGE_AUDIT_COMPLETE.md) - Test gaps

---

## 📞 SUPPORT

**Created Files**:
- [app/middleware/query_logger.py](app/middleware/query_logger.py) - Query monitoring logic
- [app/middleware/performance_middleware.py](app/middleware/performance_middleware.py) - FastAPI integration
- [docs/CURRENT/SLOW_QUERY_MONITORING_GUIDE.md](docs/CURRENT/SLOW_QUERY_MONITORING_GUIDE.md) - This guide

**Log Files**:
- `logs/slow_queries.log` - Slow query log (auto-created)

---

**Guide Készítő**: Claude Sonnet 4.5
**Dátum**: 2025-12-17
**Verzió**: 1.0

---

**END OF SLOW QUERY MONITORING GUIDE**
