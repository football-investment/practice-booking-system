# Feature Summary: Tournament Templates

**TL;DR**: Add template save/load to sandbox → Save instructors 70-80% of configuration time (5-8 min → 90 sec)

---

## 📊 One-Page Summary

| Aspect | Details |
|--------|---------|
| **User Story** | As an instructor, I want to save tournament configs as templates, so I don't re-enter 30+ fields every time |
| **Pain Point** | 5-8 min manual data entry × 4 tournaments/week = 20-32 min/week wasted |
| **Solution** | Save/Load/Manage templates (like game presets, but for full tournament config) |
| **Time Savings** | **70-80% reduction** (20-32 min/week → 6 min/week) |
| **Implementation** | 5-7 hours (client-side only, no backend changes) |
| **Risk** | 🟢 LOW (single file, localStorage, zero backend impact) |
| **ROI** | Payback in 3-4 weeks (70-130 min/week saved across team) |
| **User Delight** | 🔥 HIGH (addresses #1 sandbox feedback: "wish I didn't have to re-enter everything") |

---

## 🎯 The Problem (Real User Pain)

**Current Flow**:
```
Configuration Screen
  ↓ Fill 30+ fields manually:
    - Tournament name, age group, location, campus
    - Format, scoring mode, max players
    - Schedule (start/end dates)
    - Game preset + 12-20 skill checkboxes
    - 10-30 participant toggles
    - 6 reward fields (XP + Credits for 1st/2nd/3rd/participation/session)
  ↓ 5-8 minutes
Submit → Workflow

REPEAT for next tournament 🔁
```

**User Quote**: _"I just created this exact YOUTH tournament yesterday. Why do I need to select all 15 skills again?"_

---

## 💡 The Solution

**Enhanced Flow**:
```
Configuration Screen
  ↓ Load Template (optional)
    [YOUTH Budapest Weekly] → Auto-fills all 30+ fields
  ↓ 30 seconds
  ↓ Adjust 1-2 fields (if needed)
  ↓ 30 seconds
Submit → Workflow

Total: 90 seconds (vs 5-8 min)
```

**UI Mockup**:
```
┌────────────────────────────────────────────┐
│ 📋 Tournament Templates                    │
├────────────────────────────────────────────┤
│ [Select Template ▼]  [Load]  [Manage]     │
│   - YOUTH Budapest Weekly                  │
│   - PRO Debrecen Monthly                   │
│   - AMATEUR Pest Tournament                │
└────────────────────────────────────────────┘

[Configuration Form - auto-filled...]

┌────────────────────────────────────────────┐
│ [💾 Save as Template]  [Submit →]          │
└────────────────────────────────────────────┘
```

---

## 📈 Impact

**Time Savings**:
- Per instructor: 14-26 min/week (70-80% reduction)
- Team (5 instructors): 70-130 min/week
- Annual: 60-110 hours saved

**User Experience**:
- ✅ Less cognitive load (no need to remember settings)
- ✅ Fewer errors (no typos, wrong age group, etc.)
- ✅ Faster experimentation (try 3 tournament variations in 5 min)
- ✅ Consistency (same structure across weeks)

**Business Value**:
- 🎯 Increases sandbox usage (less friction → more testing)
- 🎯 Enables complex experiments (templates lower barrier)
- 🎯 Product polish signal (small feature, big UX impact)

---

## 🔧 Implementation

**Scope**: Client-side only (ZERO backend changes)

**Changes**:
- 1 file: `streamlit_sandbox_v3_admin_aligned.py` (configuration screen)
- Storage: Browser localStorage (or session_state + export/import for MVP)
- No API endpoints, no database migrations, no backend risk

**MVP (5 hours)**:
1. Save template (capture form config) - 1h
2. Load template (auto-fill form) - 2h
3. Manage templates (list/delete) - 1h
4. Export/import JSON - 1h

**Enhancement (optional, +2h)**:
5. localStorage persistence component - 2h

**Total**: 5-7 hours

---

## ⚖️ Risk Assessment

| Risk Factor | Level | Mitigation |
|-------------|-------|------------|
| **Backend Impact** | 🟢 NONE | Client-side only |
| **Production Risk** | 🟢 NONE | No backend/DB changes |
| **Complexity** | 🟢 LOW | Single file, 300 lines |
| **Failure Mode** | 🟢 SAFE | Worst case: templates don't save, user continues manually (current state) |
| **User Impact** | 🟡 MEDIUM | If buggy, affects config screen UX |

**Overall Risk**: 🟢 **LOW** (high reward, low risk)

---

## ✅ Recommendation

**APPROVE FOR WEEK 5-6 IMPLEMENTATION**

**Why Now?**:
1. ✅ P3 Week 3 complete (sandbox stable, component library ready)
2. ✅ Sprint 3 complete (location_venue cleanup done)
3. ✅ High user value for low effort (best ROI available)
4. ✅ Perfect fit for "value creation" phase (not technical cleanup)

**Why This Feature?**:
1. ✅ Addresses #1 user pain point in sandbox feedback
2. ✅ 70-80% time savings (measurable impact)
3. ✅ Low implementation risk (client-side, isolated)
4. ✅ Fast ROI (payback in 3-4 weeks)
5. ✅ User delight factor HIGH ("finally!" moment)

---

## 📋 Next Steps

1. **User Validation** (30 min): Show mockup to 2-3 instructors, confirm value
2. **Technical Spike** (30 min): Test localStorage in Streamlit
3. **Implementation** (5-7 hours): Build MVP (Week 5 or 6)
4. **Deploy & Iterate** (ongoing): Collect usage metrics, refine UX

---

**Full Details**: See [PRODUCT_FEATURE_SANDBOX_TEMPLATES.md](PRODUCT_FEATURE_SANDBOX_TEMPLATES.md)

**Created**: 2026-01-31
**Status**: ✅ APPROVED_PENDING_IMPLEMENTATION
**Decision**: 2026-01-31 - Approved for MVP implementation (client-side, session_state)
**Next**: Awaiting GO signal for implementation
