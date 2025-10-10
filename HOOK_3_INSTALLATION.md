# Hook 3: Daily Snapshot Scheduler Installation

## ✅ Implementation Complete

All code for Hook 3 (Daily Snapshot Cron Job) has been successfully implemented:

- ✅ `app/tasks/scheduler.py` - Background scheduler with APScheduler
- ✅ `app/main.py` - Integrated scheduler into app lifespan
- ✅ Two scheduled jobs configured:
  1. **Daily Snapshots:** Every day at 00:00 (midnight)
  2. **Weekly Recommendations:** Every Monday at 06:00

## 📦 Required Installation

To activate the scheduler, install APScheduler:

```bash
pip install apscheduler
```

Or add to `requirements.txt`:
```
apscheduler==3.10.4
```

Then run:
```bash
pip install -r requirements.txt
```

## 🔧 How It Works

### Startup Sequence
1. FastAPI app starts
2. `lifespan()` context manager runs
3. `start_scheduler()` initializes BackgroundScheduler
4. Two jobs are scheduled:
   - Daily snapshots (00:00)
   - Weekly recommendations (Monday 06:00)
5. Scheduler runs in background thread

### Job 1: Daily Snapshots (00:00)
```python
def create_daily_snapshots_for_all_users():
    # Gets all active students with lesson progress
    # Creates daily performance snapshot for each
    # Logs success/error counts
```

**What it captures:**
- Pace score
- Quiz average
- Lessons completed today
- Time spent today

### Job 2: Weekly Recommendations (Monday 06:00)
```python
def refresh_all_recommendations():
    # Gets all active students
    # Regenerates recommendations for each
    # Force refresh = true
```

**Why weekly:**
- Keeps recommendations fresh
- Catches students who became inactive
- Adapts to changing learning patterns

## 🧪 Testing

### Manual Trigger (for testing):
```python
from app.tasks.scheduler import create_daily_snapshots_for_all_users, refresh_all_recommendations

# Test snapshot creation
create_daily_snapshots_for_all_users()

# Test recommendation refresh
refresh_all_recommendations()
```

### Check Scheduler Status:
```python
# In app startup logs, you should see:
# ✅ Background scheduler started successfully
# 📅 Jobs scheduled:
#    - Daily snapshots: Every day at 00:00
#    - Weekly recommendations: Every Monday at 06:00
```

### Verify Jobs Are Running:
```bash
# Check application logs at:
# - 00:00 daily (snapshots)
# - 06:00 Mondays (recommendations)

# Expected log output:
# 🕐 Starting daily snapshot creation at 2025-10-10 00:00:00
# ✅ Daily snapshots completed: 150 success, 0 errors
```

## 🔍 Database Verification

After midnight, check that snapshots were created:

```sql
-- Check latest snapshots
SELECT user_id, snapshot_date, pace_score, quiz_average, lessons_completed_count
FROM performance_snapshots
WHERE snapshot_date = CURRENT_DATE
ORDER BY user_id
LIMIT 10;
```

After Monday 06:00, check recommendations were refreshed:

```sql
-- Check latest recommendations
SELECT user_id, recommendation_type, title, created_at
FROM adaptive_recommendations
WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
    AND is_active = true
ORDER BY created_at DESC
LIMIT 20;
```

## 📊 Production Considerations

### Monitoring
- Add application monitoring (Sentry, Datadog, etc.)
- Alert if snapshot success rate < 90%
- Alert if job execution time > 5 minutes

### Scaling
- For 10,000+ users, consider:
  - Batch processing (100 users at a time)
  - Distributed task queue (Celery + Redis)
  - Database query optimization (batch inserts)

### Error Handling
- Current implementation: Logs errors, continues with next user
- Non-critical errors don't stop the job
- Critical errors are logged and reported

### Time Zone
- Current: UTC (00:00 UTC)
- To change: Modify CronTrigger in `scheduler.py`
- Example (CET): `CronTrigger(hour=0, minute=0, timezone='Europe/Budapest')`

## 🎯 Integration Status

### ✅ Completed
- [x] Scheduler code implemented
- [x] Integrated with FastAPI lifespan
- [x] Error handling added
- [x] Logging configured
- [x] Two jobs scheduled

### ⏳ Pending
- [ ] Install APScheduler (`pip install apscheduler`)
- [ ] Test first run (wait for midnight or trigger manually)
- [ ] Verify snapshots in database
- [ ] Monitor logs for any errors

## 🚀 Next Steps

1. **Install APScheduler:**
   ```bash
   pip install apscheduler
   ```

2. **Restart application:**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Check logs:**
   ```
   ✅ Background scheduler started successfully
   📅 Jobs scheduled:
      - Daily snapshots: Every day at 00:00
      - Weekly recommendations: Every Monday at 06:00
   ```

4. **Manual test (optional):**
   ```python
   from app.tasks.scheduler import create_daily_snapshots_for_all_users
   create_daily_snapshots_for_all_users()
   ```

5. **Wait for midnight** and verify snapshots were created!

---

**Implementation Date:** October 10, 2025
**Status:** ✅ Code Complete - Pending APScheduler Installation
**Estimated Installation Time:** 1 minute
