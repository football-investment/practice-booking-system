# Tournament Enrollment - Manuális Tesztelési Útmutató

## 📋 Áttekintés

Ez a dokumentum a teljes tournament enrollment flow manuális tesztelését írja le, a tournament létrehozásától a player enrollment-ig.

## 🎯 Tesztelési Cél

Ellenőrizzük hogy:
1. ✅ Admin létrehozhat tournament-et
2. ✅ Instructor jelentkezhet (APPLICATION_BASED workflow)
3. ✅ Admin jóváhagyja az instructor application-t
4. ✅ Tournament status automatikusan → INSTRUCTOR_CONFIRMED
5. ✅ Admin megnyitja az enrollment-et → READY_FOR_ENROLLMENT
6. ✅ Player-ek jelentkezhetnek a tournament-re
7. ✅ Enrollment validációk működnek (age, credits, conflicts)

---

## 🔐 Teszt User Credentials

### Admin User
```
Email: admin@lfa.com
Password: admin123
Role: ADMIN
```

### Instructor Users
```
Email: coach.instructor@lfa.com
Password: password123
Role: INSTRUCTOR
Coach Level: 1 (PRE-qualified)
Credits: 3000
```

```
Email: youth.instructor@lfa.com
Password: password123
Role: INSTRUCTOR
Coach Level: 3 (YOUTH-qualified)
Credits: 0
```

### Player/Student Users

**PRE Category (Age 10 - Born 2014):**
```
Email: pwt.k1sqx1@f1stteam.hu
Password: password123
Role: STUDENT
Date of Birth: 2014-05-15 (Age 10)
Age Category: PRE
Credits: 0 (❌ NEEDS CREDITS!)
```

**YOUTH Category (Age 15 - Born 2009):**
```
Email: pwt.p3t1k3@f1stteam.hu
Password: password123
Role: STUDENT
Date of Birth: 2009-08-20 (Age 15)
Age Category: YOUTH
Credits: 0 (❌ NEEDS CREDITS!)
```

**AMATEUR Category (Age 20 - Born 2004):**
```
Email: pwt.V4lv3rd3jr@f1stteam.hu
Password: password123
Role: STUDENT
Date of Birth: 2004-11-12 (Age 20)
Age Category: AMATEUR
Credits: 0 (❌ NEEDS CREDITS!)
```

---

## 🚀 Tournament Enrollment Flow - Lépések

### PHASE 1: Tournament Creation (Admin)

**Lépések:**

1. **Login as Admin**
   - Email: `admin@lfa.com`
   - Password: `admin123`

2. **Navigate to Tournaments Tab**
   - Admin Dashboard → "🏆 Tournament Management"
   - "➕ Create Tournament" tab

3. **Create PRE Tournament**
   ```
   Name: "Test PRE Tournament - [Date]"
   Age Group: PRE
   Assignment Type: APPLICATION_BASED
   Start Date: [Future date]
   End Date: [Future date]
   Max Players: 10
   Enrollment Cost: 500 credits
   Location: [Any available]
   Campus: [Any available]
   ```

4. **Verify Tournament Created**
   - Check "📋 View Tournaments" tab
   - Tournament should show:
     - Status: `SEEKING_INSTRUCTOR`
     - Assignment Type: `📝 APPLICATION_BASED`

   **✅ Expected:** Tournament létrehozva, várakozik instructor-ra

---

### PHASE 2: Instructor Application (Instructor)

**Lépések:**

1. **Logout from Admin**

2. **Login as Instructor**
   - Email: `coach.instructor@lfa.com`
   - Password: `password123`

3. **Navigate to Tournaments**
   - Instructor Dashboard → "🏆 Open Tournaments" tab

4. **Find and Apply to Tournament**
   - Locate "Test PRE Tournament"
   - Should show "📝 Apply" button (Level 1 is sufficient for PRE)
   - Click "Apply"

5. **Fill Application Form**
   ```
   Message: "I would like to lead this PRE tournament. I have experience with U6-U8 players."
   ```

6. **Submit Application**

7. **Verify Application Submitted**
   - Navigate to "📬 My Applications" tab
   - Should see application with status: `PENDING`

   **✅ Expected:** Application elküldve, várakozik admin approval-ra

---

### PHASE 3: Admin Approves Application (Admin)

**Lépések:**

1. **Logout from Instructor**

2. **Login as Admin**
   - Email: `admin@lfa.com`
   - Password: `admin123`

3. **Navigate to Tournaments**
   - Admin Dashboard → "🏆 Tournament Management"
   - "📋 View Tournaments" tab

4. **Find Tournament and Open Details**
   - Locate "Test PRE Tournament"
   - Click to expand tournament details

5. **View Instructor Applications Section**
   - Scroll to "Instructor Application Management"
   - Should see application from `coach.instructor@lfa.com`
   - Status: `PENDING`

6. **Approve Application**
   - Click "✅ Approve" button
   - **FIGYELD A CONSOLE-T:** Debug logok kellene megjelenjenek:
     ```
     🔍 DEBUG: Creating notification for application approval
     ✅ DEBUG: Notification object created successfully
     ✅ DEBUG: Notification committed successfully!
     ```

7. **Fill Approval Message**
   ```
   Response Message: "Congratulations! Your application has been approved. Looking forward to working with you!"
   ```

8. **Submit Approval**

9. **Verify Tournament Status Changed**
   - Tournament status should now be: `INSTRUCTOR_CONFIRMED`
   - Instructor should be assigned

   **✅ Expected:**
   - Application approved ✅
   - Tournament status → INSTRUCTOR_CONFIRMED ✅
   - Instructor notification created ✅
   - NO INTEGRITY ERROR! ✅

---

### PHASE 4: Open Enrollment (Admin)

**Lépések:**

1. **Still logged in as Admin**

2. **Find Tournament in List**
   - Should see "📝 Open Enrollment" button

3. **Click "Open Enrollment"**

4. **Confirm Enrollment Opening**
   - Verify tournament details
   - Click "Open Enrollment" button in dialog

5. **Verify Status Changed**
   - Tournament status should now be: `READY_FOR_ENROLLMENT`

   **✅ Expected:** Tournament nyitva player enrollment-nek

---

### PHASE 5: Add Credits to Student (Admin - Required!)

**KRITIKUS LÉPÉS:** A student user-eknek nincs credit-jük, adjunk nekik!

**Lépések:**

1. **Still logged in as Admin**

2. **Open Database or Use Admin Tool**

3. **Add Credits to Students**
   ```sql
   -- Run in psql
   PGDATABASE=lfa_intern_system psql -U postgres -h localhost

   UPDATE users SET credit_balance = 2000
   WHERE email IN (
     'pwt.k1sqx1@f1stteam.hu',
     'pwt.p3t1k3@f1stteam.hu',
     'pwt.V4lv3rd3jr@f1stteam.hu'
   );
   ```

4. **Verify Credits Added**
   ```sql
   SELECT email, credit_balance FROM users
   WHERE role = 'STUDENT';
   ```

   **✅ Expected:** Minden student-nek 2000 credit-je van

---

### PHASE 6: Player Enrollment (Student - PRE)

**Lépések:**

1. **Logout from Admin**

2. **Login as PRE Student**
   - Email: `pwt.k1sqx1@f1stteam.hu`
   - Password: `password123`

3. **Navigate to Tournaments** (ELLENŐRIZD HOGY VAN-E ILYEN TAB!)
   - Player Dashboard → Look for Tournaments/Enrollment section

4. **Find Open Tournament**
   - Should see "Test PRE Tournament"
   - Status should show: `READY_FOR_ENROLLMENT` or `Open for Enrollment`

5. **Enroll in Tournament**
   - Click "Enroll" or "Sign Up" button
   - **FIGYELD A CONSOLE-T:** Backend API hívás:
     ```
     POST /api/v1/tournaments/{tournament_id}/enroll
     🚀 ENROLLMENT START - Tournament: X, User: Y
     ```

6. **Verify Enrollment Success**
   - Should see success message
   - Credits should be deducted: 2000 - 500 = 1500
   - Should see tournament in "My Tournaments" section

7. **Check Backend Logs**
   - Backend terminal-ban kellene látni:
     ```
     ✅ Enrollment created
     ✅ Credits deducted
     ✅ Booking created (if applicable)
     ```

   **✅ Expected:**
   - Player successfully enrolled ✅
   - Credits deducted correctly ✅
   - NO errors ✅

---

### PHASE 7: Enrollment Validation Tests

**Test 1: Duplicate Enrollment (Same Student)**

1. **Still logged in as PRE Student**
2. **Try to enroll again in same tournament**
3. **Expected:** Error message: "Already enrolled in this tournament"

**Test 2: Wrong Age Category (YOUTH tries to enroll in PRE)**

1. **Logout and login as YOUTH Student**
   - Email: `pwt.p3t1k3@f1stteam.hu`
2. **Try to enroll in PRE Tournament**
3. **Expected:** Error message about age category mismatch

**Test 3: Insufficient Credits**

1. **Create another PRE tournament** (if needed)
2. **Enroll PRE student until credits run out**
3. **Try one more enrollment**
4. **Expected:** Error message: "Insufficient credits"

---

## 🔍 Debugging Checklist

Ha valami nem működik, ellenőrizd:

### Backend Logs
```bash
# Check if backend is running
curl http://localhost:8000/health

# Watch backend logs in real-time
# (Terminal where uvicorn is running)
```

### Database State
```sql
-- Check tournament status
SELECT id, name, tournament_status, master_instructor_id
FROM semesters
WHERE name LIKE '%Test PRE%'
ORDER BY created_at DESC;

-- Check instructor applications
SELECT id, semester_id, instructor_id, status
FROM instructor_assignment_requests
WHERE semester_id IN (SELECT id FROM semesters WHERE name LIKE '%Test PRE%');

-- Check enrollments
SELECT se.id, se.user_id, se.semester_id, se.request_status, s.name
FROM semester_enrollments se
JOIN semesters s ON se.semester_id = s.id
WHERE s.name LIKE '%Test PRE%';

-- Check student credits
SELECT email, credit_balance
FROM users
WHERE role = 'STUDENT';
```

### Frontend Logs
- Open Browser DevTools (F12)
- Console tab
- Network tab (check API responses)

---

## 📊 Expected Results Summary

| Phase | Action | Expected Status | Expected Result |
|-------|--------|----------------|-----------------|
| 1 | Tournament Created | `SEEKING_INSTRUCTOR` | Tournament visible, waiting for instructor |
| 2 | Instructor Applied | Still `SEEKING_INSTRUCTOR` | Application shows `PENDING` |
| 3 | Admin Approved | `INSTRUCTOR_CONFIRMED` | Application approved, instructor assigned |
| 4 | Enrollment Opened | `READY_FOR_ENROLLMENT` | Players can now enroll |
| 5 | Credits Added | N/A | Students have 2000 credits |
| 6 | Player Enrolled | Still `READY_FOR_ENROLLMENT` | Enrollment created, credits deducted |

---

## ❌ Common Issues & Solutions

### Issue 1: Integrity Error on Approval
**Symptom:** `{"error": "integrity_error", "message": "Data integrity constraint violated"}`
**Solution:** This was fixed in commit `5d9c663`. Make sure migration ran:
```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic upgrade head
```

### Issue 2: Students Can't Enroll (No Tab/Button)
**Symptom:** No tournament enrollment UI in player dashboard
**Solution:** Check if tournament browser component exists in player dashboard

### Issue 3: Enrollment Fails (Insufficient Credits)
**Symptom:** `"Insufficient credits"`
**Solution:** Add credits to student users (see Phase 5)

### Issue 4: Age Category Validation Fails
**Symptom:** Player can't enroll despite being correct age
**Solution:** Verify date_of_birth is set and age_category calculation is correct

---

## ✅ Success Criteria

A tesztelés sikeres ha:

- ✅ Admin létrehozhat tournament-et
- ✅ Instructor jelentkezhet
- ✅ Admin jóváhagyhatja (NO integrity error!)
- ✅ Tournament status transitions működnek
- ✅ Admin megnyithatja enrollment-et
- ✅ Player-ek jelentkezhetnek
- ✅ Credit deduction működik
- ✅ Enrollment validációk működnek (age, duplicate, credits)
- ✅ Backend logs megfelelőek
- ✅ Nincs error a console-ban

---

## 📝 Notes for Tester

- **FIGYELD A CONSOLE-T:** Backend és Frontend logok kritikusak a debugging-hoz
- **POSTGRES CHECK:** Ha bármi gyanús, ellenőrizd a DB state-et
- **BACKEND RESTART:** Ha változik a kód, újra kell indítani a backend-et
- **CLEAR CACHE:** Néha szükséges a browser cache törlése (Ctrl+Shift+R)

---

## 🎯 Next Steps After Testing

Ha minden működik:
1. ✅ Dokumentáld a talált bug-okat (ha vannak)
2. ✅ Készíts screenshot-okat a successful flow-ról
3. ✅ Jegyezd fel a console log-okat
4. ✅ Oszd meg az eredményeket

Ha vannak problémák:
1. ❌ Gyűjtsd össze a console log-okat
2. ❌ Készíts screenshot-ot az error-ról
3. ❌ Ellenőrizd a database state-et
4. ❌ Oszd meg a részleteket debug-oláshoz
