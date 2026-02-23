# Admin Guide: Tournament Skill Selection

## Overview

When creating a tournament, you **must explicitly select** which skills will earn points for participants.

**Why?** Each tournament tests different abilities:
- NIKE Speed Test → only speed + agility matter
- Plank Competition → only stamina counts
- Penalty Shootout → only shooting + composure matter

**No default skills are enabled.** You decide what's relevant per tournament.

---

## 📋 Quick Start

### Step 1: Create Tournament
1. Go to **Tournament Generator**
2. Fill in tournament details (name, date, location, etc.)

### Step 2: Select Reward Template
Choose a template as your starting point:
- **Standard**: 500/300/200 credits
- **Championship**: 1000/600/400 credits (premium)
- **Friendly**: 200/100/50 credits (casual)

⚠️ **Important**: Templates start with **0 skills enabled** by default.

### Step 3: Enable Relevant Skills
Scroll to **⚠️ SKILL SELECTION (REQUIRED)**

Check the boxes for skills relevant to your tournament:
- Physical: speed, agility, stamina, strength
- Technical: ball_control, shooting, passing, dribbling
- Mental: decision_making, composure

Adjust weights if needed (default: 1.0x to 2.0x).

### Step 4: Validate & Save
- ✅ At least 1 skill selected → "Create Tournament" button enabled
- ❌ 0 skills selected → Error message shown

---

## 🏆 Example 1: NIKE Speed Test

**Tournament Type**: INDIVIDUAL_RANKING
**Measurement**: 40-yard sprint time (seconds, Lower is Better)

### Relevant Skills:
✅ **Speed** (weight: 2.0x) - Primary skill tested
✅ **Agility** (weight: 1.5x) - Secondary skill tested
❌ Stamina - NOT relevant (short sprint)
❌ Ball Control - NOT relevant (no ball)
❌ All others - NOT relevant

### Configuration:
```
Template: Championship (premium event)
Skills:
  ☑ Speed (weight: 2.0x)
  ☑ Agility (weight: 1.5x)
  ☐ All others disabled

1st Place: 1000 credits, 2.0x XP, Champion badge
2nd Place: 600 credits, 1.5x XP, Runner-Up badge
3rd Place: 400 credits, 1.3x XP, Third Place badge
```

### Skill Points Calculation:
- **1st Place (10 base points)**:
  - Speed: (2.0 / 3.5) × 10 = 5.7 points
  - Agility: (1.5 / 3.5) × 10 = 4.3 points
  - **Total**: 10.0 points → ~100 bonus XP

- **2nd Place (7 base points)**:
  - Speed: 4.0 points
  - Agility: 3.0 points
  - **Total**: 7.0 points → ~70 bonus XP

- **Participation (1 base point)**:
  - Speed: 0.6 points
  - Agility: 0.4 points
  - **Total**: 1.0 points → ~10 bonus XP

### Why This Config?
- Speed weighted higher (2.0x) because it's the **primary** skill tested
- Agility weighted lower (1.5x) as a **secondary** factor
- Stamina NOT included - short sprints don't test endurance
- Ball skills NOT included - no ball involved

---

## 🏋️ Example 2: Plank Hold Competition

**Tournament Type**: INDIVIDUAL_RANKING
**Measurement**: Plank hold duration (seconds, Higher is Better)

### Relevant Skills:
✅ **Stamina** (weight: 2.5x) - Primary skill tested
✅ **Strength** (weight: 1.5x) - Core strength required
❌ Speed - NOT relevant (static hold)
❌ Agility - NOT relevant (static hold)
❌ Ball Control - NOT relevant (no ball)
❌ All others - NOT relevant

### Configuration:
```
Template: Standard (regular event)
Skills:
  ☑ Stamina (weight: 2.5x)
  ☑ Strength (weight: 1.5x)
  ☐ All others disabled

1st Place: 500 credits, 1.5x XP, Champion badge
2nd Place: 300 credits, 1.3x XP, Runner-Up badge
3rd Place: 200 credits, 1.2x XP, Third Place badge
```

### Skill Points Calculation:
- **1st Place (10 base points)**:
  - Stamina: (2.5 / 4.0) × 10 = 6.3 points
  - Strength: (1.5 / 4.0) × 10 = 3.8 points
  - **Total**: 10.0 points → ~100 bonus XP

- **2nd Place (7 base points)**:
  - Stamina: 4.4 points
  - Strength: 2.6 points
  - **Total**: 7.0 points → ~70 bonus XP

- **Participation (1 base point)**:
  - Stamina: 0.6 points
  - Strength: 0.4 points
  - **Total**: 1.0 points → ~10 bonus XP

### Why This Config?
- Stamina weighted highest (2.5x) - holding a plank is **pure endurance**
- Strength weighted lower (1.5x) - core strength helps but stamina is key
- Speed/Agility NOT included - no movement required
- Ball skills NOT included - bodyweight exercise

---

## ⚠️ Common Mistakes

### ❌ Mistake 1: Not Selecting Any Skills
**Error**: "You must select at least 1 skill to continue"

**Fix**: Check at least 1 skill box before clicking "Create Tournament"

### ❌ Mistake 2: Selecting Irrelevant Skills
**Example**: Speed Test with "Passing" enabled

**Why Bad?**: Passing has nothing to do with sprint performance. It dilutes reward calculation and confuses players.

**Fix**: Only enable skills that are **directly tested** by the tournament.

### ❌ Mistake 3: Equal Weights for Unequal Skills
**Example**: Speed Test with Speed (1.0x) and Agility (1.0x)

**Why Bad?**: Speed is the PRIMARY metric, agility is secondary. They should have different weights.

**Fix**: Assign higher weight to primary skills (1.5x-2.5x), lower to secondary (1.0x-1.5x).

---

## 🔒 Validation Rules

### Frontend Validation:
- ✅ At least 1 skill selected → "Create Tournament" button **enabled**
- ❌ 0 skills selected → "Create Tournament" button **disabled** + error message

### Backend Validation (Safety Net):
If you somehow bypass frontend validation, the API will reject the config:

```
HTTP 400 Bad Request
{
  "detail": "Invalid skill configuration: At least 1 skill must be enabled for tournament rewards. You must select at least 1 skill for this tournament."
}
```

---

## 📊 Skill Categories

### Physical Skills
- **speed**: Sprint speed, acceleration
- **agility**: Quick direction changes, footwork
- **stamina**: Endurance, sustained effort
- **strength**: Power, physicality

### Technical Skills
- **ball_control**: First touch, close control
- **shooting**: Finishing, accuracy
- **passing**: Distribution, vision
- **dribbling**: Ball manipulation, 1v1 ability

### Mental Skills
- **decision_making**: Tactical awareness, reading the game
- **composure**: Handling pressure, staying calm

---

## 💡 Pro Tips

### Tip 1: Match Skills to Tournament Format
- **Sprint events** → speed + agility
- **Endurance events** → stamina + strength
- **Technical events** → ball_control + shooting/passing
- **Tactical events** → decision_making + composure

### Tip 2: Use Weights to Reflect Importance
- **Primary skill**: 2.0x - 2.5x
- **Secondary skill**: 1.2x - 1.5x
- **Tertiary skill**: 1.0x

### Tip 3: Review Templates First
Before creating custom configs, check if a template matches your needs:
- **Standard**: Balanced rewards, good for regular competitions
- **Championship**: Premium rewards, use for flagship events
- **Friendly**: Low rewards, use for practice/training tournaments

### Tip 4: Test Your Config
After creating the tournament, check the **Preview Rewards** tab to see:
- How many skill points each placement earns
- Total bonus XP distribution
- Badge allocation

---

## ✅ Checklist

Before clicking "Create Tournament":

- [ ] Tournament name and details filled
- [ ] Location and campus selected
- [ ] Reward template selected
- [ ] **At least 1 skill enabled** (check the boxes!)
- [ ] Skill weights adjusted (if needed)
- [ ] Badge configuration reviewed
- [ ] Credits and XP multipliers set

---

## 🚀 Summary

**Key Rule**: You MUST explicitly select which skills earn points per tournament.

**No shortcuts**: Templates start with 0 enabled skills by default.

**Real Examples**:
1. **NIKE Speed Test** → Speed (2.0x) + Agility (1.5x)
2. **Plank Competition** → Stamina (2.5x) + Strength (1.5x)

**Validation**: System enforces at least 1 skill selected (frontend + backend).

**Questions?** Check [SKILL_SELECTION_VALIDATION.md](SKILL_SELECTION_VALIDATION.md) for technical details.
