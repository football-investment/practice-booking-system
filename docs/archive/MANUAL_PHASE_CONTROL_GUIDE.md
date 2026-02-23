# Manual Phase Control Guide

**Date:** 2026-02-14
**Feature:** Step-by-Step Tournament Phase Simulation
**Status:** ✅ READY

---

## Overview

You can now **manually step through tournament phases** one at a time, observing each phase's completion before moving to the next.

---

## How to Use

### Step 1: Launch Tournament in Manual Mode

1. **Open Tournament Monitor:** http://localhost:8501
2. **Login:** admin@lfa.com
3. **Use OPS Wizard:**
   - **Step 1:** Choose scenario (e.g., "Large Field Monitor")
   - **Step 2:** Choose format: HEAD_TO_HEAD
   - **Step 3:** Choose type: group_knockout
   - **Step 4:** Player count: 64
   - **Step 5:** **IMPORTANT:** Choose simulation mode: **📝 Manual (No Auto-Simulation)**
   - **Step 6:** Review and launch

### Step 2: Simulate Phase by Phase

Once the tournament is created, you'll see:

```
Tournament Phases
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

─────────────────────────────────
### ⚽ GROUP STAGE     ⏳ 0/96 (0%)
📍 Parallel venues: Óbuda · Pest · Buda · Újpest · ...

[Group matches grid]

[No completion banner yet - phase incomplete]
─────────────────────────────────

[KNOCKOUT phase hidden until GROUP_STAGE complete]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Manual Result Entry — 96 pending match(es)

▶️ Simulate Group Stage  |  ⚡ Simulate All Phases

▶️ Simulate Group Stage: 96 matches in current phase only
⚡ Simulate All Phases: 144 matches across all phases
```

### Step 3: Click "▶️ Simulate Group Stage"

This will:
1. Simulate **only the Group Stage matches** (96 matches)
2. Show completion toast: "✅ Group Stage complete: 96 matches!"
3. Auto-refresh the page

You'll now see:

```
─────────────────────────────────
### ⚽ GROUP STAGE     ✅ COMPLETE
📍 Parallel venues: Óbuda · Pest · Buda · Újpest · ...

[All group matches completed ✅]

🎉 GROUP STAGE COMPLETE — Qualifiers (Top 2 from each group):
✅ Felix Müller (GA)    ✅ Emma Schmidt (GA)
✅ Lukas Schneider (GB) ✅ Anna Fischer (GB)
✅ Finn Weber (GC)      ✅ Mia Meyer (GC)
✅ Paul Wagner (GD)     ✅ Lea Becker (GD)
─────────────────────────────────

─────────────────────────────────
### 🏆 KNOCKOUT     ⏳ 0/48 (0%)
📍 Parallel venues: Óbuda Sports Complex

[Knockout bracket matches - seeding info visible]

[No completion banner yet - phase incomplete]
─────────────────────────────────
```

### Step 4: Click "▶️ Simulate Knockout"

This will simulate the knockout phase matches, showing final results.

---

## Button Comparison

### ▶️ Simulate {Phase Name}
- **What it does:** Simulates **only the current incomplete phase**
- **Example:** "▶️ Simulate Group Stage" → Only group matches
- **Use case:** Step through phases one at a time
- **Button type:** Primary (green)

### ⚡ Simulate All Phases
- **What it does:** Simulates **all pending matches across all phases**
- **Example:** Simulates Group Stage + Knockout + Finals all at once
- **Use case:** Quick completion of entire tournament
- **Button type:** Secondary (gray)

---

## Visual Flow

```
LAUNCH TOURNAMENT (Manual Mode)
          ↓
┌─────────────────────────────────┐
│ ⚽ GROUP STAGE     ⏳ 0/96 (0%)  │ ← Only this phase visible
│ [pending matches]               │
└─────────────────────────────────┘

Click "▶️ Simulate Group Stage"
          ↓
┌─────────────────────────────────┐
│ ⚽ GROUP STAGE     ✅ COMPLETE   │ ← Phase completed
│ [completed matches]             │
│ 🎉 Qualifiers: [list]           │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ 🏆 KNOCKOUT       ⏳ 0/48 (0%)  │ ← Next phase revealed
│ [pending matches]               │
└─────────────────────────────────┘

Click "▶️ Simulate Knockout"
          ↓
┌─────────────────────────────────┐
│ ⚽ GROUP STAGE     ✅ COMPLETE   │
│ [completed matches]             │
│ 🎉 Qualifiers: [list]           │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ 🏆 KNOCKOUT       ✅ COMPLETE   │ ← Phase completed
│ [completed matches]             │
│ 🎉 Qualifiers: [list]           │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ 🏅 FINALS         ⏳ 0/1 (0%)   │ ← Final phase revealed
│ [pending match]                 │
└─────────────────────────────────┘
```

---

## Key Features

### 1. **Progressive Phase Reveal**
- Only the first incomplete phase is visible
- Next phase appears automatically when previous phase completes
- Prevents confusion from seeing all phases at once

### 2. **Phase Completion Banners**
- Clear "🎉 PHASE COMPLETE" message
- Lists qualifiers advancing to next phase
- Shown for: Group Stage, Knockout, Finals, etc.

### 3. **Real User Names**
- No more "Player 0001" placeholders
- Shows actual seed user names: Felix Müller, Emma Schmidt, Lukas Schneider, etc.

### 4. **Campus-Parallel Display**
- Group Stage: Shows all parallel campuses (8 venues)
- Knockout: Shows main venue (Óbuda)
- Each phase clearly labeled with venue info

### 5. **English UI**
- All text in English (no Hungarian mixed in)
- Professional, consistent terminology

---

## Simulation Mode Comparison

### 📝 Manual (No Auto-Simulation)
- **When to use:** Step-by-step observation, testing phase logic
- **Behavior:** No matches simulated automatically, you control each phase
- **Control:** "▶️ Simulate {Phase}" button for phase-by-phase progression

### 🤖 Auto-Simulation (Immediate)
- **When to use:** Quick testing, load validation
- **Behavior:** All matches auto-simulated immediately on launch
- **Control:** No manual control needed, tournament completes automatically

### ⚡ Accelerated Simulation
- **When to use:** End-to-end testing, algorithm validation
- **Behavior:** Entire lifecycle simulated instantly (create → complete → rankings)
- **Control:** No manual interaction, full automation

---

## Troubleshooting

### Issue: Tournament auto-simulates even in Manual mode
**Solution:** Ensure you selected "📝 Manual (No Auto-Simulation)" in Step 5 of the wizard.

### Issue: All phases show at once
**Solution:** This is expected if auto-simulation ran. Create a new tournament in Manual mode to see progressive reveal.

### Issue: "▶️ Simulate" button not appearing
**Solution:** Ensure there are pending matches. If all matches are complete, the button won't appear.

### Issue: Duplicate names in leaderboard
**Solution:** This is a backend ranking calculation issue. Check if the tournament completed successfully.

### Issue: Hungarian text appears
**Solution:** This has been fixed. Refresh the page (F5) to reload the updated UI.

---

## Example Workflow

**Goal:** Create and observe a 64-player Group+Knockout tournament step-by-step.

1. **Launch:**
   - OPS Wizard → Large Field Monitor → HEAD_TO_HEAD → group_knockout → 64 players → **Manual** → Launch

2. **Observe GROUP_STAGE:**
   - See 96 group matches pending across 8 campuses
   - Matches show: "⏳ Müller vs Fischer · 📍Óbuda"

3. **Simulate GROUP_STAGE:**
   - Click "▶️ Simulate Group Stage"
   - Wait for toast: "✅ Group Stage complete: 96 matches!"

4. **View Qualifiers:**
   - See completion banner: "🎉 GROUP STAGE COMPLETE"
   - Review top 2 from each group (8 qualifiers total)

5. **Observe KNOCKOUT:**
   - Knockout phase now visible
   - See 48 bracket matches pending at Óbuda
   - Matches show seeding: "⏳ A1 vs B2 · 📍Óbuda"

6. **Simulate KNOCKOUT:**
   - Click "▶️ Simulate Knockout"
   - Wait for toast: "✅ Knockout complete: 48 matches!"

7. **View Final Results:**
   - See completion banner: "🎉 KNOCKOUT COMPLETE"
   - Review leaderboard with final rankings

---

## Benefits

✅ **Full Control:** Step through phases at your own pace
✅ **Clear Visualization:** Each phase displayed separately with completion status
✅ **Traceability:** Qualifiers listed after each phase
✅ **Real Names:** Actual user names (Felix Müller, Emma Schmidt, etc.)
✅ **English UI:** Professional, consistent terminology
✅ **Legal Compliance:** Every phase documented and traceable

---

**Ready to test!** Launch a tournament in Manual mode and use the "▶️ Simulate" buttons to step through phases. 🎯
