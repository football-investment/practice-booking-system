# 📋 TODO - SPECIALIZATION SYSTEM CONTINUATION

## 🔥 SESSION 2 TASKS (Tomorrow)

### 1️⃣ Achievement System Update (1.5 hours)

**Goal:** Make achievements aware of specializations and create specialization-specific achievements

#### **Files to Modify:**
- `app/services/gamification.py` - Update achievement triggers
- `app/models/__init__.py` - Check achievement models
- Database - Add specialization field to achievements (migration needed)

#### **Tasks:**

**1.1 Database Schema Update (30 min)**
- [ ] Create migration to add `specialization_id` field to achievements table
- [ ] Make field nullable (for general achievements that apply to all)
- [ ] Add specialization filter to achievement queries

**1.2 Achievement Definitions (30 min)**
- [ ] Define PLAYER-specific achievements:
  - "First Belt Promotion" - Reach level 2
  - "Bambusz Master" - Complete level 1 with 80%+ attendance
  - "Yellow Belt Warrior" - Reach level 3
  - "GanCuju Dedication" - 20+ sessions as PLAYER
  - "Belt Collector" - Reach level 5

- [ ] Define COACH-specific achievements:
  - "First Training Session" - Lead first session as coach
  - "Pre Football Certified" - Reach level 2
  - "Youth Coach" - Reach level 4
  - "Coaching Mastery" - Complete 50h theory + practice
  - "PRO Certification" - Reach level 8

- [ ] Define INTERNSHIP-specific achievements:
  - "First Sprint" - Complete first internship project
  - "Explorer Badge" - Reach level 1
  - "Growth Mindset" - Reach level 2
  - "Startup Leader" - Reach level 3
  - "Innovation Champion" - Complete 3+ projects

**1.3 Update Achievement Service (30 min)**
- [ ] Update `calculate_achievements()` to filter by specialization
- [ ] Update achievement triggers in session completion
- [ ] Update achievement triggers in project enrollment
- [ ] Test achievement unlock flow

#### **Expected Outcome:**
- Achievements are filtered by user's current specialization
- Users only see relevant achievements
- Specialization-specific achievements unlock correctly

---

### 2️⃣ Frontend Progress Display (2 hours)

**Goal:** Show level progress in student dashboard with beautiful visualizations

#### **Files to Create:**

**2.1 Components (1 hour)**

**File:** `frontend/src/components/student/SpecializationProgress.jsx`
```jsx
// Main progress card showing:
// - Current level with badge
// - XP progress bar
// - Next level requirements
// - Level up notification (if eligible)
```

**File:** `frontend/src/components/student/LevelProgressBar.jsx`
```jsx
// Visual XP progress bar:
// - Animated fill based on progress percentage
// - Show current XP / required XP
// - Color-coded by specialization (blue/purple/green)
```

**File:** `frontend/src/components/student/LevelBadge.jsx`
```jsx
// Level badge display:
// - Icon/emoji based on specialization
// - Level number
// - Level name (e.g., "Bambusz Tanítvány")
// - Color based on belt/certification level
```

**2.2 CSS Styling (30 min)**

**File:** `frontend/src/components/student/SpecializationProgress.css`
```css
/* Responsive design for:
 * - Progress cards
 * - Level badges
 * - XP bars
 * - Level up animations
 */
```

**2.3 Integration (30 min)**

**File:** `frontend/src/pages/student/StudentDashboard.js`
- [ ] Import SpecializationProgress component
- [ ] Add API call to fetch progress data
- [ ] Display progress in dashboard hero section
- [ ] Show "Level Up!" notification if eligible

**File:** `frontend/src/services/apiService.js`
- [ ] Add `getSpecializationProgress(specializationId)` method
- [ ] Add `getAllSpecializationLevels(specializationId)` method
- [ ] Add error handling for progress API calls

#### **UI/UX Requirements:**

**Desktop Layout:**
```
┌─────────────────────────────────────┐
│ 🎓 Your Progress                    │
├─────────────────────────────────────┤
│ ⚽ GanCuju Player                   │
│                                     │
│ Level 2: Hajnali Harmat (Sárga)    │
│ [████████░░░░░░░░] 48% to Level 3   │
│                                     │
│ 25,000 / 45,000 XP                  │
│ 12 / 15 Sessions Completed          │
│                                     │
│ Next Level: Rugalmas Nád (Zöld)    │
│ Need: 20,000 XP, 3 more sessions    │
└─────────────────────────────────────┘
```

**Mobile Layout:**
```
┌──────────────────┐
│ ⚽ Level 2        │
│ Hajnali Harmat   │
│ [████░░] 48%     │
│ 25K / 45K XP     │
└──────────────────┘
```

#### **Expected Outcome:**
- Students see their progression clearly
- Progress bar animates on page load
- Level badges are visually appealing
- Responsive on all devices

---

### 3️⃣ Testing & Validation (30 min)

**Goal:** Ensure everything works end-to-end

#### **Test Cases:**

**3.1 Backend API Tests**
- [ ] Test progress creation for new user
- [ ] Test level up with exact XP requirement
- [ ] Test multi-level up (skip levels)
- [ ] Test max level behavior
- [ ] Test invalid specialization handling

**3.2 Frontend Integration Tests**
- [ ] Test progress component loading
- [ ] Test API error handling
- [ ] Test loading states
- [ ] Test responsive design on mobile
- [ ] Test level up notification display

**3.3 User Journey Test**
- [ ] Register new student
- [ ] Select specialization
- [ ] Complete session → earn XP
- [ ] Check progress updated
- [ ] Reach level 2
- [ ] Verify level up notification
- [ ] Check achievements unlocked

**3.4 Edge Cases**
- [ ] User with no specialization
- [ ] User at max level
- [ ] User with multiple specializations (if allowed)
- [ ] Invalid specialization_id in API call

#### **Expected Outcome:**
- All test cases pass
- No errors in console
- Smooth user experience

---

### 4️⃣ Documentation Update (30 min)

**Goal:** Document the completed system

#### **Files to Update:**

**File:** `API_DOCUMENTATION.md`
- [ ] Document all new specialization endpoints
- [ ] Add request/response examples
- [ ] Document authentication requirements

**File:** `README.md`
- [ ] Add specialization system overview
- [ ] Add setup instructions
- [ ] Add screenshots of UI

**File:** `SPECIALIZATION_USER_GUIDE.md` (new)
- [ ] Explain 3 specializations
- [ ] Explain level system
- [ ] Explain XP earning
- [ ] Explain level requirements

#### **Expected Outcome:**
- Complete documentation for developers
- User-friendly guide for students
- Clear API documentation

---

## 🟡 OPTIONAL TASKS (If Time Permits)

### 5️⃣ Admin Payment Verification System (2 hours)

**Goal:** Control specialization access based on payment

#### **Tasks:**

**5.1 Payment Verification Table (30 min)**
- [ ] Create `semester_payments` table
- [ ] Fields: student_id, semester_id, amount, verified_by, verified_at
- [ ] Migration script

**5.2 Admin UI (1 hour)**
- [ ] Payment management page
- [ ] Student list with payment status
- [ ] "Verify Payment" button
- [ ] Payment history

**5.3 Access Control (30 min)**
- [ ] Block specialization selection until payment verified
- [ ] Show payment status banner to students
- [ ] API endpoint to check payment status

---

### 6️⃣ XP Daily Limits (1 hour)

**Goal:** Prevent XP farming and encourage consistent attendance

#### **Tasks:**

**6.1 Daily XP Tracking (30 min)**
- [ ] Add `daily_xp_earned` field to user or separate table
- [ ] Track XP by date
- [ ] Set daily XP cap (e.g., 500 XP/day)

**6.2 Frontend Display (30 min)**
- [ ] Show "Daily XP remaining" in dashboard
- [ ] Show cooldown timer
- [ ] Show notification when cap reached

---

## 🧪 TESTING CHECKLIST

### **Functional Testing:**
- [ ] User registration with specialization selection
- [ ] Progress tracking after session completion
- [ ] Level up notification display
- [ ] Achievement unlock on specialization milestones
- [ ] API endpoint authentication
- [ ] Mobile responsive design

### **Edge Case Testing:**
- [ ] Max level user behavior
- [ ] User with no specialization
- [ ] Invalid API requests
- [ ] Concurrent progress updates
- [ ] Browser refresh during level up

### **Performance Testing:**
- [ ] Progress API response time (<200ms)
- [ ] Dashboard load time with progress component
- [ ] Database query optimization (indexes)

---

## 📚 DOCUMENTATION CHECKLIST

- [ ] API endpoint documentation
- [ ] User guide for specialization system
- [ ] Admin guide for payment management
- [ ] Developer setup guide
- [ ] Database schema documentation
- [ ] Achievement system documentation

---

## 🎯 SUCCESS CRITERIA

**By End of Session 2:**
1. ✅ Achievement system is specialization-aware
2. ✅ Frontend displays progress beautifully
3. ✅ All tests passing
4. ✅ Documentation complete
5. ✅ User journey smooth and intuitive

**Estimated Total Time:** 4-5 hours

**Priority Order:**
1. Achievement system (must have)
2. Frontend progress display (must have)
3. Testing (must have)
4. Documentation (must have)
5. Payment system (nice to have)
6. XP limits (nice to have)

---

## 📝 NOTES FOR NEXT SESSION

### **Quick Start Commands:**

```bash
# Start backend
cd practice_booking_system
source venv/bin/activate
uvicorn app.main:app --reload

# Start frontend
cd frontend
npm start

# Check database
psql postgresql://lovas.zoltan@localhost:5432/practice_booking_system
```

### **Key API Endpoints to Test:**
```
GET  /api/v1/specializations/progress/PLAYER
GET  /api/v1/specializations/levels/PLAYER
POST /api/v1/specializations/update-progress/PLAYER
```

### **Test User Credentials:**
```
alex.player@lfa.com (PLAYER, Level 2, 25000 XP)
maria.coach@lfa.com (COACH, Level 1, 0 XP)
```

---

## 🐛 KNOWN ISSUES TO ADDRESS

- None currently identified

---

## 💡 IDEAS FOR FUTURE ENHANCEMENTS

1. **Leaderboard by Specialization**
   - Top players by XP in each specialization
   - Weekly/monthly leaderboards

2. **Level Up Rewards**
   - Unlock special content at certain levels
   - Digital badges/certificates

3. **Specialization Switching**
   - Allow users to maintain progress in multiple specs
   - Track primary vs secondary specialization

4. **Progress Sharing**
   - Share level achievements on social media
   - Export progress report PDF

5. **Historical Progress Chart**
   - XP gain over time
   - Sessions completed per week
   - Level progression timeline

---

**Status: Ready for Session 2** 🚀
**Last Updated:** 2025-10-09
