# 🧪 Integration Testing Guide

Quick guide to test Hook 1, Hook 2, and Hook 3 integration.

## ⚡ Quick Start

### Option 1: Automated E2E Tests (Recommended)

**Prerequisites:**
- Application must be running on `http://localhost:8000`

**Steps:**
```bash
# Terminal 1: Start the application
cd practice_booking_system
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Run automated tests
source venv/bin/activate
python test_integration_hooks.py
```

**What it tests:**
- ✅ Student registration & login
- ✅ Hook 1: Quiz completion → Competency assessment + Recommendations
- ✅ Hook 3: Performance snapshot creation

**Expected duration:** 30-45 seconds

---

### Option 2: Database Verification (No application needed)

**Steps:**
```bash
cd practice_booking_system
source venv/bin/activate
python verify_hooks_db.py
```

**What it checks:**
- ✅ Recent quiz attempts and their competency assessments
- ✅ Recent graded exercises and their competency assessments
- ✅ Performance snapshots
- ✅ User competency scores

**Expected duration:** 5-10 seconds

---

## 📊 Test Coverage

| Hook | Description | Test Script | Database Verification |
|------|-------------|-------------|----------------------|
| Hook 1 | Quiz → Competency | ✅ `test_integration_hooks.py` | ✅ `verify_hooks_db.py` |
| Hook 2 | Exercise → Competency | ⏳ Manual (requires instructor) | ✅ `verify_hooks_db.py` |
| Hook 3 | Daily Snapshot | ✅ `test_integration_hooks.py` | ✅ `verify_hooks_db.py` |

---

## 🔍 What Each Hook Does

### Hook 1: Quiz Completion → Competency Assessment
**File:** `app/api/api_v1/endpoints/quiz.py` (lines 142-168)

**Trigger:** Student completes a quiz

**Actions:**
1. ✅ Create competency assessments for quiz skills
2. ✅ Update user learning profile (pace, quiz average)
3. ✅ Generate recommendations if score < 70% (REVIEW_LESSON type)

**Database Effects:**
```sql
-- New records created:
INSERT INTO competency_assessments (user_id, skill_id, score, source_type, source_id)
UPDATE user_learning_profiles SET quiz_average_score = X, learning_pace = Y
INSERT INTO adaptive_recommendations (recommendation_type = 'REVIEW_LESSON')
```

---

### Hook 2: Exercise Grading → Competency Assessment
**File:** `app/api/api_v1/endpoints/curriculum.py` (lines 122-162)

**Trigger:** Instructor grades an exercise submission

**Actions:**
1. ✅ Award XP to student
2. ✅ Create competency assessments for exercise skills
3. ✅ Update user learning profile

**Database Effects:**
```sql
-- New records created:
UPDATE user_exercise_submissions SET score = X, xp_awarded = Y, reviewed_at = NOW()
UPDATE users SET total_xp = total_xp + Y
INSERT INTO competency_assessments (user_id, skill_id, score, source_type = 'exercise')
UPDATE user_learning_profiles SET ...
```

**Manual Test:**
```bash
# 1. Student submits exercise
curl -X POST "http://localhost:8000/api/v1/curriculum/exercise/{exercise_id}/submit" \
  -H "Authorization: Bearer {student_token}" \
  -d '{"submission_text": "My solution..."}'

# 2. Instructor grades exercise
curl -X POST "http://localhost:8000/api/v1/curriculum/exercise/submission/{submission_id}/grade" \
  -H "Authorization: Bearer {instructor_token}" \
  -d '{"score": 85, "feedback": "Good work!"}'

# 3. Verify with database script
python verify_hooks_db.py
```

---

### Hook 3: Daily Snapshot Scheduler
**File:** `app/tasks/scheduler.py`

**Trigger:** Automated at 00:00 daily (+ manual via API)

**Actions:**
1. ✅ Create performance snapshots for all active students
2. ✅ Capture daily metrics (quiz avg, lessons completed, XP, etc.)
3. ✅ Weekly recommendation refresh (Mondays at 06:00)

**Database Effects:**
```sql
-- New records created:
INSERT INTO performance_snapshots (
  user_id, snapshot_date, quiz_average, lessons_completed,
  total_xp, current_level, total_minutes_studied
)
```

**Manual Trigger:**
```bash
# Trigger snapshot for current user
curl -X POST "http://localhost:8000/api/v1/curriculum-adaptive/snapshot" \
  -H "Authorization: Bearer {token}"
```

---

## 🎯 Expected Results

### After Running `test_integration_hooks.py`:

**Database State:**
- ✅ 1 new student account created
- ✅ 1 quiz attempt completed (score < 70%)
- ✅ 3-5 competency assessments created
- ✅ 1 user learning profile created/updated
- ✅ 1-2 adaptive recommendations created (REVIEW_LESSON type)
- ✅ 1 performance snapshot created

**Console Output:**
```
🎉 ALL INTEGRATION TESTS PASSED!
Total: 4/4 tests passed
```

---

### After Running `verify_hooks_db.py`:

**Console Output:**
```
✅ Found 1 recent quiz attempts
  ✅ Hook 1 triggered: 3 competency assessments created
  ✅ Learning profile updated
  ✅ Recommendations generated

✅ Found 1 performance snapshots
  ✅ Hook 3 working: Daily metrics captured
```

---

## 🐛 Troubleshooting

### Issue: "Cannot connect to application"
**Solution:**
```bash
# Start the application first
uvicorn app.main:app --reload
```

### Issue: "Database connection failed"
**Solution:**
```bash
# Check PostgreSQL is running
psql -h localhost -U lfa_user practice_booking_system -c "SELECT 1"

# If fails, start PostgreSQL:
brew services start postgresql@14
```

### Issue: "No quizzes available"
**Solution:**
```bash
# Check if quiz seed data exists
psql -h localhost -U lfa_user practice_booking_system -c "SELECT COUNT(*) FROM quizzes;"

# If 0, run seed script
python scripts/create_comprehensive_quizzes.py
```

### Issue: "Hook not working"
**Check application logs:**
```bash
# Look for error messages in Hook 1/2/3 execution
grep "Error in post-quiz hooks" logs/app.log
grep "Error in exercise grading hooks" logs/app.log
grep "Failed for user" logs/app.log
```

---

## 📝 Test Data Cleanup

After testing, you may want to clean up test data:

```sql
-- Remove test students
DELETE FROM users WHERE email LIKE 'test_student_%@lfa.test';
DELETE FROM users WHERE email LIKE 'test_instructor_%@lfa.test';

-- Remove test quiz attempts
DELETE FROM quiz_attempts WHERE user_id IN (
  SELECT id FROM users WHERE email LIKE 'test_%@lfa.test'
);

-- Remove test competency data
DELETE FROM competency_assessments WHERE user_id IN (
  SELECT id FROM users WHERE email LIKE 'test_%@lfa.test'
);

-- Remove test snapshots
DELETE FROM performance_snapshots WHERE user_id IN (
  SELECT id FROM users WHERE email LIKE 'test_%@lfa.test'
);
```

Or run the cleanup script:
```bash
psql -h localhost -U lfa_user practice_booking_system -f scripts/cleanup_test_data.sql
```

---

## 📚 Additional Resources

- **Full Testing Report:** See `TESTING_REPORT.md`
- **Hook Implementation Details:** See integration letters in project root
- **API Documentation:** http://localhost:8000/docs (when app is running)
- **Database Schema:** See `alembic/versions/` for migrations

---

## ✅ Success Criteria

All hooks are working correctly if:

1. **Hook 1 (Quiz):**
   - ✅ Competency assessments created after quiz completion
   - ✅ Learning profile updated with new quiz average
   - ✅ Recommendations generated for low scores (<70%)

2. **Hook 2 (Exercise):**
   - ✅ Competency assessments created after grading
   - ✅ XP awarded to student
   - ✅ Learning profile updated

3. **Hook 3 (Snapshot):**
   - ✅ Daily snapshots created at 00:00
   - ✅ Manual snapshot API works
   - ✅ Snapshot contains all metrics (quiz avg, lessons, XP, etc.)

4. **Scheduler:**
   - ✅ APScheduler running on application startup
   - ✅ Two jobs scheduled (daily snapshots, weekly recommendations)
   - ✅ Logs show successful job execution

---

**Last Updated:** October 10, 2025
**Test Scripts Version:** 1.0
