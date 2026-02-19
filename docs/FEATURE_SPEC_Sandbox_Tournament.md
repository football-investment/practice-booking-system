# Feature Spec: Sandbox Tournament Testing UI

**Priority**: P2 (Enhancement - Not blocking current functionality)
**Status**: 📋 Backlog (Phase 1 - Spec Complete)
**Target Phase**: Phase 2 - Implementation when demo/product testing begins
**Date Created**: 2026-01-27

---

## 🎯 Goal

Provide a **non-technical validation interface** for testing tournament skill progression without requiring CLI access or bash script knowledge.

**Target Users**:
- Product managers
- QA testers
- Stakeholders during demos
- Non-technical team members

---

## 🔍 Problem Statement

**Current State**:
- Skill progression validation requires:
  - Running bash scripts (`test_league_with_checkpoints.sh`)
  - Reading checkpoint files (`/tmp/checkpoint_*.txt`)
  - Command-line access
  - Technical knowledge of the testing flow

**Pain Points**:
- ❌ **Barrier to entry**: Non-developers cannot validate the system
- ❌ **Demo friction**: Cannot show skill progression live in product demos
- ❌ **Slow feedback**: Must context-switch between CLI and frontend
- ❌ **Limited visibility**: Skill changes hidden in text files, not visual

**Desired State**:
- ✅ **Self-service testing**: Anyone can run a test tournament from the UI
- ✅ **Instant feedback**: Visual skill change comparison (before/after)
- ✅ **Demo-ready**: Live demonstration of skill progression in 5 minutes
- ✅ **Reproducible**: Same test configuration can be run multiple times

---

## 📦 Scope

### ✅ In Scope (MVP)

1. **Sandbox Tournament Creation UI**
   - Tournament type: **League only** (HEAD_TO_HEAD format)
   - Skill mappings: Configure 2 skills (passing + dribbling)
   - Player selection: Multi-select from existing users
   - Auto-generate results: Random match outcomes

2. **Automated Test Execution**
   - Create tournament
   - Enroll players
   - Generate sessions
   - Simulate match results (random outcomes)
   - Complete tournament
   - Distribute rewards

3. **Visual Results Display**
   - Final standings table
   - **Skill changes visualization** (before/after comparison)
   - Rewards summary (XP + badges)
   - Clear indication: ✅ Test successful / ❌ Test failed

### ⚠️ Clearly Out of Scope

- ❌ **Production tournaments**: Sandbox is **test-only**, isolated from real data
- ❌ **Custom scoring rules**: Fixed placement-based scoring for MVP
- ❌ **Multi-round tournaments**: Only single-round league for MVP
- ❌ **Manual match input**: Auto-generated results only
- ❌ **Historical test results**: No persistence of past sandbox runs

### 🔮 Future Enhancements (Post-MVP)

- Knockout tournament support
- Custom reward policies
- Test result history/comparison
- Export test results as PDF report
- Batch testing (run multiple configurations)

---

## 🏗️ Architecture

### Frontend Components

#### **1. Sandbox Tournament Configuration Page**
**Route**: `/admin/tournaments/sandbox`

**UI Elements**:
```
┌─────────────────────────────────────────────────────┐
│ 🧪 Sandbox Tournament Tester                        │
│ ⚠️  Test Environment - Not Production Data          │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Tournament Configuration                             │
│ ┌──────────────────────────────────────────────┐   │
│ │ Type: [League ▼] (HEAD_TO_HEAD)             │   │
│ │ Duration: ~30 seconds                        │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ Skill Mappings                                       │
│ ┌──────────────────────────────────────────────┐   │
│ │ ✓ Passing (weight: 1.0)   [─────●───] 0-2.0 │   │
│ │ ✓ Dribbling (weight: 0.8) [────●────] 0-2.0 │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ Select Test Players (6-8 players)                    │
│ ┌──────────────────────────────────────────────┐   │
│ │ Search: [_____________]                      │   │
│ │                                               │   │
│ │ ✓ User 4 - Junior Intern                     │   │
│ │ ✓ User 5 - Sarah Player                      │   │
│ │ ✓ User 6 - Mike Player                       │   │
│ │ ✓ User 14 - Alex Player                      │   │
│ │ ✓ User 15 - Emma Player                      │   │
│ │ ✓ User 16 - John Player                      │   │
│ │                                               │   │
│ │ [Select All] [Clear] [Use Default Test Set]  │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│     [🚀 Run Test Tournament] [📋 View History]     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Form State**:
```typescript
interface SandboxTournamentConfig {
  tournamentType: "league";  // Fixed for MVP
  format: "HEAD_TO_HEAD";    // Fixed for MVP
  scoringType: "PLACEMENT";  // Fixed for MVP
  skillMappings: Array<{
    skill: string;  // e.g., "passing"
    weight: number; // 0.0 - 2.0
  }>;
  playerIds: number[];
  autoGenerateResults: true; // Fixed for MVP
}
```

#### **2. Test Execution Progress Modal**
**Trigger**: After clicking "Run Test Tournament"

```
┌─────────────────────────────────────────────────────┐
│ ⏳ Running Test Tournament...                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Progress: ████████████░░░░░░░░░░ 60%               │
│                                                      │
│ ✅ Tournament created (ID: 123)                     │
│ ✅ Players enrolled (6 players)                     │
│ ✅ Sessions generated (3 matches)                   │
│ ⏳ Simulating matches...                            │
│ ⬜ Completing tournament                            │
│ ⬜ Distributing rewards                             │
│                                                      │
│ Estimated time remaining: 15s                        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**WebSocket Updates** (optional enhancement):
- Real-time progress updates
- Live log streaming

#### **3. Test Results Page**
**Route**: `/admin/tournaments/sandbox/results/{test_id}`

```
┌─────────────────────────────────────────────────────┐
│ ✅ Test Tournament Complete                         │
│ Tournament ID: 123 | Duration: 28s                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│ 📊 Final Standings                                  │
│ ┌──────────────────────────────────────────────┐   │
│ │ Rank | Player      | Points | Result        │   │
│ │──────┼─────────────┼────────┼───────────────│   │
│ │  🥇  │ User 5      │  3 pts │ 1 Win, 0 Loss │   │
│ │  🥈  │ User 6      │  3 pts │ 1 Win, 0 Loss │   │
│ │  🥉  │ User 4      │  3 pts │ 1 Win, 0 Loss │   │
│ │  4   │ User 16     │  2 pts │ 0 Win, 1 Loss │   │
│ │  5   │ User 15     │  2 pts │ 0 Win, 1 Loss │   │
│ │  6   │ User 14     │  2 pts │ 0 Win, 1 Loss │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ 📈 Skill Changes - BEFORE vs AFTER                  │
│ ┌──────────────────────────────────────────────┐   │
│ │ User 5 (1st place) 🥇                        │   │
│ │   Passing:   60.0 → 74.0  (+14.0) ↗️         │   │
│ │   [█████████████░░░░░░░] +23%                │   │
│ │   Dribbling: 50.0 → 65.2  (+15.2) ↗️         │   │
│ │   [██████████████░░░░░░] +30%                │   │
│ │                                               │   │
│ │ User 4 (3rd place) 🥉                        │   │
│ │   Passing:   80.0 → 90.0  (+10.0) ↗️         │   │
│ │   [████████░░░░░░░░░░░░] +13%                │   │
│ │   Dribbling: 50.0 → 70.0  (+20.0) ↗️         │   │
│ │   [█████████████░░░░░░░] +40%                │   │
│ │                                               │   │
│ │ User 16 (6th place)                          │   │
│ │   Passing:   100.0 → 76.0 (-24.0) ↘️         │   │
│ │   [░░░░░░░░░░░░░░░█████] -24%                │   │
│ │   Dribbling: 50.0 → 40.8  (-9.2) ↘️          │   │
│ │   [░░░░░░░░░░░░░██████░] -18%                │   │
│ │                                               │   │
│ │ [Show All Players ▼]                         │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ 🏆 Rewards Summary                                  │
│ ┌──────────────────────────────────────────────┐   │
│ │ • Total XP Awarded: 1,780                    │   │
│ │ • Total Badges: 12                           │   │
│ │ • Players Rewarded: 6                        │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ ✅ Validation: Skill progression working correctly  │
│                                                      │
│ [🔄 Run Another Test] [📥 Export Results]          │
│ [🗑️ Delete Test Data]                              │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🔌 Backend API

### **Endpoint: Run Sandbox Tournament**

```http
POST /api/v1/tournaments/sandbox/run-test
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "tournament_type": "league",
  "format": "HEAD_TO_HEAD",
  "scoring_type": "PLACEMENT",
  "skill_mappings": [
    {"skill": "passing", "weight": 1.0},
    {"skill": "dribbling", "weight": 0.8}
  ],
  "player_ids": [4, 5, 6, 14, 15, 16],
  "auto_generate_results": true
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "test_id": "sandbox_20260127_143052",
  "tournament_id": 123,
  "execution_time_seconds": 28.3,
  "results": {
    "final_standings": [
      {"rank": 1, "user_id": 5, "name": "Sarah Player", "points": 3},
      {"rank": 2, "user_id": 6, "name": "Mike Player", "points": 3},
      {"rank": 3, "user_id": 4, "name": "Junior Intern", "points": 3}
    ],
    "skill_changes": [
      {
        "user_id": 5,
        "name": "Sarah Player",
        "placement": 1,
        "skills": {
          "passing": {
            "before": 60.0,
            "after": 74.0,
            "change": 14.0,
            "change_percent": 23.3
          },
          "dribbling": {
            "before": 50.0,
            "after": 65.2,
            "change": 15.2,
            "change_percent": 30.4
          }
        }
      }
    ],
    "rewards_summary": {
      "total_xp_awarded": 1780,
      "total_badges_awarded": 12,
      "players_rewarded": 6
    }
  },
  "validation_status": "PASSED",
  "validation_checks": {
    "skills_updated": true,
    "winners_gained_skills": true,
    "losers_lost_skills": true,
    "rewards_distributed": true
  }
}
```

**Response** (400 Bad Request - Validation Failed):
```json
{
  "success": false,
  "error": {
    "code": "SKILL_VALIDATION_FAILED",
    "message": "Skills did not update after reward distribution",
    "details": {
      "expected": "6 players with skill changes",
      "actual": "0 players with skill changes"
    }
  }
}
```

### **Implementation Logic**

```python
@router.post("/sandbox/run-test")
async def run_sandbox_test(
    request: SandboxTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Runs a complete sandbox tournament test with automatic validation.

    Steps:
    1. Create tournament with reward_config (skill mappings)
    2. Force status transitions via SQL (bypass workflow for testing)
    3. Enroll players
    4. Generate sessions
    5. Simulate match results (random outcomes)
    6. Complete tournament
    7. Distribute rewards
    8. Validate skill changes occurred
    9. Return comprehensive results

    Authorization: Admin only
    """
    # Validate admin permission
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(403, "Sandbox testing requires admin privileges")

    # Step 1: Create tournament with reward_config
    tournament_id = create_sandbox_tournament(
        db=db,
        config=request,
        created_by=current_user.id
    )

    # Step 2-7: Execute test flow
    try:
        test_results = execute_sandbox_test_flow(
            db=db,
            tournament_id=tournament_id,
            player_ids=request.player_ids,
            skill_mappings=request.skill_mappings
        )

        # Step 8: Validate results
        validation = validate_sandbox_results(db, tournament_id, test_results)

        return {
            "success": True,
            "test_id": f"sandbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "tournament_id": tournament_id,
            "execution_time_seconds": test_results.execution_time,
            "results": test_results.to_dict(),
            "validation_status": "PASSED" if validation.passed else "FAILED",
            "validation_checks": validation.checks
        }

    except Exception as e:
        # Cleanup: Mark tournament as ARCHIVED (sandbox test failed)
        mark_sandbox_tournament_failed(db, tournament_id)
        raise HTTPException(500, f"Sandbox test failed: {str(e)}")
```

---

## 🎨 Visual Design Requirements

### **Skill Change Visualization**

**Key Requirements**:
1. **Before/After Comparison**: Side-by-side or inline display
2. **Visual Indicators**:
   - ↗️ Green for increases
   - ↘️ Red for decreases
   - Progress bars showing magnitude of change
3. **Percentage Change**: Alongside absolute values
4. **Grouping**: Winners (top 3) vs Losers (bottom 3) clearly separated

**Color Coding**:
- 🟢 Green: Positive skill change (winners)
- 🔴 Red: Negative skill change (losers)
- ⚪ Gray: No change (inactive skills)

---

## ✅ Acceptance Criteria

### **MVP Must-Have**

- [ ] Admin can access `/admin/tournaments/sandbox` page
- [ ] Form allows selection of:
  - [ ] 6-8 players from existing users
  - [ ] 2 skill mappings (passing + dribbling) with weight sliders
- [ ] "Run Test Tournament" button triggers backend execution
- [ ] Progress modal shows real-time status updates
- [ ] Results page displays:
  - [ ] Final standings table
  - [ ] **Skill changes for all players** (before/after with visual diff)
  - [ ] Rewards summary (XP + badges)
  - [ ] ✅/❌ Validation status indicator
- [ ] Entire test completes in < 60 seconds
- [ ] Test tournament is **clearly marked** as sandbox (not production)
- [ ] Test data can be deleted after viewing results

### **Quality Gates**

- [ ] Skill changes are **visually obvious** (not buried in JSON)
- [ ] Winners show positive skill changes (↗️ green)
- [ ] Losers show negative skill changes (↘️ red)
- [ ] UI clearly communicates: "This is a TEST, not real data"

---

## 📊 Success Metrics

**Usage Indicators**:
- Number of sandbox tests run per week
- User feedback: "Easier to validate skill progression" (survey)

**Efficiency Gains**:
- Time to validate skill progression: **From 10 min (CLI) → 5 min (UI)**
- Non-tech validation: **From 0% → 80%** (product managers can self-serve)

---

## 🚦 Implementation Phases

### **Phase 1: Spec + Backlog** ✅ CURRENT
**Status**: Complete
**Deliverables**:
- [x] Feature spec document (this file)
- [x] Backlog item created (P2 priority)
- [x] Design mockups included
- [x] API contract defined

**Decision**:
- ✅ Current development validation (bash scripts + manual guide) is **sufficient**
- ✅ Sandbox UI is **nice-to-have**, not **must-have** for development

### **Phase 2: Implementation** 🔮 FUTURE
**Trigger Conditions** (any of):
- Product demo schedule confirmed (need live demonstration)
- QA team requires self-service testing
- Stakeholder validation sessions increase (> 2 per week)
- Non-technical team members need to verify skill progression

**Estimated Effort**:
- Backend: 4-6 hours (endpoint + test orchestration)
- Frontend: 8-10 hours (form + results page + styling)
- Testing: 2-3 hours (E2E test for sandbox UI)
- **Total**: ~2 days (1 developer)

**Dependencies**:
- None (self-contained feature)

---

## 🔗 Related Documentation

- [E2E Skill Progression Manual Verification Guide](./E2E_SKILL_PROGRESSION_MANUAL_VERIFICATION.md) - Current validation process
- [Technical Debt](./TECHNICAL_DEBT.md) - Known limitations
- [Tournament Types Audit](./TOURNAMENT_TYPES_AUDIT.md) - Tournament system overview

---

## 📝 Notes

### **Why Not Now?**

This is a **disciplined, mature decision**:
1. ✅ Current tools (bash scripts + manual guide) work well for **development validation**
2. ✅ ROI is low **until demo/product testing phase**
3. ✅ No stakeholder pressure to implement immediately
4. ✅ Clear implementation path when needed (spec ready)

### **Why P2 (Not P3)**

- **Not P1**: Development validation already works
- **Not P3**: Clear ROI when demo phase begins
- **P2**: Important for product maturity, but not urgent

### **Design Philosophy**

- **Simplicity over flexibility**: Fixed league/HEAD_TO_HEAD for MVP
- **Automation over control**: Random results (no manual match input)
- **Clarity over features**: Visual skill diff is the #1 priority
- **Safety over speed**: Clear "test only" warnings throughout

---

**Last Updated**: 2026-01-27
**Owner**: Development Team
**Stakeholders**: Product, QA, Leadership (for demos)
