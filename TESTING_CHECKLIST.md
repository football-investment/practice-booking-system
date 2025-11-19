# 🧪 WORKFLOW TESTING CHECKLIST - Session 3

**Date:** 2025-11-19
**Status:** Ready for testing
**Backend:** ✅ Running on port 8000
**Frontend:** Ready to start

---

## 🎯 TESTING OBJECTIVES

Verify the 5 core features work after massive cleanup:
1. Dashboard
2. Specialization Selection
3. Learning Profile
4. Achievements
5. Profile

---

## 🚀 STEP 1: START SERVICES

### Backend (Already Running ✅)
```bash
# Backend is running on port 8000
# Verified: curl http://localhost:8000/api/v1/specializations/ works
```

### Frontend
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system/frontend
npm start
```

**Expected:** Browser opens to http://localhost:3000

---

## 🧑‍🎓 STEP 2: LOGIN

**URL:** http://localhost:3000

**Test Credentials:**
- Email: `student13@test.com`
- Password: `student123`

**Expected Results:**
- ✅ Login form visible
- ✅ Login succeeds
- ✅ Redirect to /student/dashboard
- ✅ No console errors

---

## 📊 STEP 3: DASHBOARD

**URL:** http://localhost:3000/student/dashboard

**Check:**
- [ ] Dashboard header visible
- [ ] Navigation sidebar visible on left
- [ ] 5 navigation links present:
  1. Dashboard
  2. Specialization
  3. Learning Profile
  4. Achievements
  5. Profile
- [ ] Dashboard widgets display (if any)
- [ ] No 404 errors
- [ ] No red console errors

**Screenshot:** Take screenshot if any errors

---

## 🎓 STEP 4: SPECIALIZATION SELECTION

**URL:** http://localhost:3000/student/specialization-select

**Check:**
- [ ] Header shows "🎓 Specialization Selection"
- [ ] 4 specialization cards visible:
  - ⚽ GānCuju Player
  - 🏃 LFA Football Player
  - 👨‍🏫 LFA Coach
  - 💼 Internship Program
- [ ] Cards show descriptions
- [ ] Cards show requirements (Age, Payment)
- [ ] "Start Specialization" button visible on each card

**CRITICAL TEST: Click a Card**
- [ ] Click "Start Specialization" on one card
- [ ] Button shows "Starting..." state
- [ ] API call to `/parallel-specializations/start` succeeds
- [ ] Card moves to "Active Specializations" section
- [ ] OR error message displays clearly

**DevTools Check:**
- Open Console (F12 → Console)
- Open Network (F12 → Network → Filter: XHR)
- Look for:
  - `GET /api/v1/parallel-specializations/dashboard` → 200 OK
  - `POST /api/v1/parallel-specializations/start` → 201 Created

**BUG 2 TEST (from Giorgio's report):**
- [ ] Cards are clickable? (not stuck/broken)
- [ ] onClick handler fires? (check Console for errors)

**Screenshot:** Capture if cards don't click or error appears

---

## 📚 STEP 5: LEARNING PROFILE

**URL:** http://localhost:3000/student/learning-profile

**Check:**
- [ ] Header shows "🎓 Your Learning Profile"
- [ ] If specialization started: License card displays
  - License Number
  - Issue Date
  - Level badge
  - XP progress bar
- [ ] If no specialization: "Start a specialization" message
- [ ] No Ant Design errors (we removed it)
- [ ] Refresh button works

**DevTools Check:**
- `GET /api/v1/licenses/my-licenses` → 200 OK

**Screenshot:** Capture license card display

---

## 🏆 STEP 6: ACHIEVEMENTS

**URL:** http://localhost:3000/student/gamification

**Check:**
- [ ] Header shows "🏆 Your Achievements"
- [ ] Stats overview shows:
  - Total XP
  - Current Level
  - Achievement count
- [ ] Progress bar to next level displays
- [ ] Achievement cards visible (earned vs locked)
- [ ] Icons display correctly (emoji icons)
- [ ] Refresh button works

**DevTools Check:**
- `GET /api/v1/gamification/my-achievements` → 200 OK

**Screenshot:** Capture achievements grid

---

## 👤 STEP 7: PROFILE

**URL:** http://localhost:3000/student/profile

**Check:**
- [ ] Profile page loads
- [ ] User information displays
- [ ] No errors

---

## 🔍 STEP 8: DEVTOOLS INSPECTION

**Open DevTools (F12):**

### Console Tab
Look for:
- [ ] Any red errors?
- [ ] Any warnings about missing components?
- [ ] Any "404 Not Found" messages?

**If errors found:** Copy full error message

### Network Tab
Filter by XHR, check all API calls:
- [ ] All API calls return 200/201?
- [ ] Any 404 errors?
- [ ] Any 500 errors?
- [ ] Response data looks correct?

**If errors found:** Note which endpoint and status code

### Elements Tab
- [ ] Navigation sidebar HTML present?
- [ ] All 5 route links clickable?

---

## 📋 REPORTING FORMAT

After testing, report using this format:

```markdown
## ✅ WORKING FEATURES

1. **Dashboard:** Loads perfectly, navigation visible
2. **Specialization:** Cards display, clicking works, API succeeds
3. **Learning Profile:** License displays with XP progress
4. **Achievements:** Stats and badges display correctly
5. **Profile:** User info displays

## ⚠️ ISSUES FOUND

### Issue 1: Specialization Cards Not Clickable
- **Page:** /student/specialization-select
- **Error:** onClick handler doesn't fire
- **Console Error:** [paste error here]
- **Network:** GET dashboard → 200 OK, POST start → never called
- **Screenshot:** [attach]

### Issue 2: Learning Profile Empty
- **Page:** /student/learning-profile
- **Error:** "Failed to load" message
- **Console Error:** [paste error here]
- **Network:** GET /api/v1/licenses/my-licenses → 404 Not Found
- **Screenshot:** [attach]

## 🎯 NEXT ACTIONS

- Fix Issue 1: Debug onClick handler
- Fix Issue 2: Check backend endpoint
- OR: All working! Session 3 COMPLETE! ✅
```

---

## 🔧 TROUBLESHOOTING TIPS

### If pages show 404:
- Check App.js routes are correctly configured
- Verify path matches navigation config

### If API calls fail:
- Verify backend is running: `lsof -ti:8000`
- Check CORS settings
- Verify API endpoint exists

### If "Ant Design" errors appear:
- We removed Ant Design, should not appear
- If it does, some file still imports it

### If specialization click doesn't work:
- Open DevTools → Console
- Click card
- Look for JavaScript error
- Check Network → XHR for API call

---

## ✅ SUCCESS CRITERIA

**All tests pass if:**
- ✅ All 5 pages load without errors
- ✅ Navigation works smoothly
- ✅ At least 1 specialization can be started successfully
- ✅ Learning Profile displays license data
- ✅ Achievements display with stats
- ✅ No critical console errors
- ✅ Bundle size is 164 KB (verified ✅)

---

## 🎉 COMPLETION

If all tests pass → **SESSION 3 COMPLETE!**

Total achievements:
- 2,500 lines removed
- 79% bundle reduction (780 KB → 164 KB)
- 5 core features working
- Clean, maintainable codebase
- Professional quality frontend

**Ready for production student testing!** 🚀
