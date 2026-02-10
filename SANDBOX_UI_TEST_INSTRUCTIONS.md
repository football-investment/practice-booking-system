# Sandbox UI Test Instructions - CHAMPION Badge Fix Verification

## Setup Complete ✅

### Backend Fixes Applied
1. ✅ `performance_card.py` - Uses `primary_badge` for metadata fallbacks
2. ✅ `tournament_achievement_accordion.py` - Uses `primary_badge` for metrics fetch
3. ✅ Debug panels added to both components (CHAMPION_DEBUG=1)

### Environment Status
- ✅ Streamlit running on http://localhost:8501
- ✅ FastAPI running on http://localhost:8000
- ✅ Database: `lfa_intern_system` (PostgreSQL)
- ✅ All caches cleared
- ✅ Debug mode enabled: `CHAMPION_DEBUG=1`

---

## Test Steps for User

### 1. Hard Refresh Browser
```bash
# Chrome/Edge
Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

# Firefox
Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
```

**Why**: Clear browser cache and force reload all assets

### 2. Clear Browser Application Storage (Critical!)
1. Open DevTools (F12)
2. Go to **Application** tab
3. Click **Storage** → **Clear site data**
4. Reload page

**Why**: Old session_state data might be cached in browser LocalStorage

### 3. Login as Test User
```
Email: k1sqx1@f1rstteam.hu
Password: [Request from admin if unknown]
```

**Alternative test user** (if password unknown):
```
Email: junior.intern@lfa.com
Password: [Check seed script]
```

### 4. Navigate to Tournament Achievements
1. Click **"Player Dashboard"** in sidebar
2. Scroll to **"🏆 Tournament Achievements"** section
3. Find any tournament with **CHAMPION** badge

### 5. Verify Debug Panel Appears

For EVERY CHAMPION badge, you should see a **blue expander box**:
```
🔍 DEBUG: Badge Data Flow
```

**Expand it** and verify:

#### ✅ Expected Debug Output (CORRECT):
```json
{
  "All Badges (API order)": {
    "count": 3,
    "badges": [
      {"index": 0, "badge_type": "CHAMPION", "badge_metadata": {"placement": 1, "total_participants": 8}},
      {"index": 1, "badge_type": "PODIUM_FINISH", "badge_metadata": {"placement": 1, "total_participants": 8}},
      {"index": 2, "badge_type": "TOURNAMENT_PARTICIPANT", "badge_metadata": null}
    ]
  },
  "Primary Badge (Used for Rendering)": {
    "badge_type": "CHAMPION",
    "badge_metadata": {"placement": 1, "total_participants": 8},
    "is_primary": true
  },
  "Computed Values": {
    "rank": 1,
    "rank_source": "snapshot",
    "total_participants": 8,
    "percentile": 12.5,
    "badge_icon": "🏆",
    "badge_title": "CHAMPION"
  }
}
```

**Success indicator**: Green message ✅
```
✅ CHAMPION badge rank correctly set: 1
```

#### ❌ FAILURE Scenario (Bug NOT Fixed):
```json
{
  "Primary Badge (Used for Rendering)": {
    "badge_type": "CHAMPION",
    "badge_metadata": null,  ← NULL = BUG!
    "is_primary": true
  },
  "Computed Values": {
    "rank": null,  ← NULL = BUG!
    "total_participants": null
  }
}
```

**Failure indicator**: Red error message ⚠️
```
⚠️ CHAMPION badge with NULL rank - REGRESSION DETECTED!
```

### 6. Check Performance Card Display

**CORRECT Display** (Expected):
```
🏆 CHAMPION
#1 of 8 players
Top 12.5% (Elite Tier)
```

**INCORRECT Display** (Bug NOT Fixed):
```
🏆 CHAMPION
No ranking data  ← BUG!
```

### 7. Test Multiple Tournaments

Check **at least 3 different CHAMPION badges** to verify consistency:
- SANDBOX-sandbox-2026-02-09-10-23-03-4221
- SANDBOX-sandbox-2026-02-09-10-23-09-3842
- SANDBOX-sandbox-2026-02-09-10-23-12-1505

All should show **green success message** in debug panel.

### 8. Check Accordion Metrics Debug (Optional)

If `CHAMPION_DEBUG=1` is set, you'll also see:
```
🔍 DEBUG: Accordion Metrics Fetch - Tournament {id}
```

Verify:
```json
{
  "primary_badge": {
    "badge_type": "CHAMPION",
    "badge_metadata": {"placement": 1, "total_participants": 8}
  },
  "badges[0]_for_comparison": {
    "badge_type": "CHAMPION",  ← Should match OR be different
    "badge_metadata": {"placement": 1, "total_participants": 8}
  }
}
```

**Key Check**: `primary_badge` should ALWAYS have CHAMPION metadata, even if `badges[0]` doesn't.

---

## Expected Results Summary

| Check | Expected Result | Status |
|-------|----------------|--------|
| Debug panel visible | ✅ For ALL CHAMPION badges | [ ] |
| Primary badge type | ✅ "CHAMPION" | [ ] |
| Primary badge metadata | ✅ `{"placement": 1, "total_participants": 8}` | [ ] |
| Computed rank | ✅ 1 (not null) | [ ] |
| Computed total_participants | ✅ 8 (not null) | [ ] |
| Success message | ✅ Green "rank correctly set" | [ ] |
| Performance card display | ✅ "#1 of 8 players" | [ ] |
| NO "No ranking data" text | ✅ Should NOT appear | [ ] |

---

## Troubleshooting

### If "No ranking data" STILL appears:

1. **Check debug panel primary_badge**:
   - If `badge_metadata` is `null` → Backend bug NOT fixed
   - If `badge_metadata` has data BUT rank is `null` → Performance card bug

2. **Verify Streamlit restarted**:
   ```bash
   lsof -ti:8501  # Should show process ID
   ps aux | grep streamlit  # Check CHAMPION_DEBUG=1 in env
   ```

3. **Check database has valid data**:
   ```sql
   SELECT badge_type, badge_metadata
   FROM tournament_badges
   WHERE user_id = (SELECT id FROM users WHERE email = 'k1sqx1@f1rstteam.hu')
     AND badge_type = 'CHAMPION'
   LIMIT 5;
   ```
   Should show `badge_metadata: {"placement": 1, "total_participants": X}`

4. **Browser DevTools Console**:
   - Check for JavaScript errors
   - Check Network tab for failed API requests

5. **Streamlit server logs**:
   ```bash
   tail -f /tmp/streamlit_debug.log
   ```
   Look for errors or warnings

---

## Reporting Results

### If ALL TESTS PASS ✅
Report back:
```
✅ CHAMPION badge fix VERIFIED
- Debug panel shows correct primary_badge metadata
- All CHAMPION badges display "#1 of X players"
- No "No ranking data" errors
- Tested N tournaments, all passing
```

### If TESTS FAIL ❌
Report back with:
1. Screenshot of debug panel (showing null values)
2. Screenshot of "No ranking data" display
3. Tournament code/name where it failed
4. Browser console errors (if any)

---

## Post-Verification Cleanup

Once fix is confirmed working:
1. Remove debug panels from code
2. Set `CHAMPION_DEBUG=0` or remove env var
3. Restart Streamlit in production mode
4. Merge feature branch to main
5. Deploy to production

---

## Technical Details (For Reference)

### Root Cause (Fixed)
- Old code: Used `badges[0]` (arbitrary API order)
- New code: Uses `_get_primary_badge(badges)` (priority-sorted)

### Files Changed
- `streamlit_app/components/tournaments/performance_card.py`
- `streamlit_app/components/tournaments/tournament_achievement_accordion.py`

### Commits
- `a013113` - Performance card fix
- `569808f` - Accordion metrics fetch fix
- `[pending]` - Debug panels (will be removed after verification)

---

## Quick Reference: Test Checklist

- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Clear browser storage (DevTools → Application → Clear site data)
- [ ] Login as k1sqx1@f1rstteam.hu
- [ ] Navigate to Tournament Achievements
- [ ] Find CHAMPION badge
- [ ] Verify debug panel shows
- [ ] Check primary_badge.badge_metadata is NOT null
- [ ] Check computed rank is NOT null
- [ ] Verify green success message
- [ ] Verify "#1 of X players" displays
- [ ] NO "No ranking data" text appears
- [ ] Test at least 3 different CHAMPION badges
- [ ] Report results back

**Estimated test time**: 5-10 minutes
