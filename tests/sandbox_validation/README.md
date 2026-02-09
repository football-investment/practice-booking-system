# Sandbox Validation Test Suite

**Purpose:** Iterative validation of skill progression logic across tournament scenarios

**Documentation:** See [SANDBOX_VALIDATION_PLAN.md](../../SANDBOX_VALIDATION_PLAN.md) for full execution protocol

---

## Directory Structure

```
tests/sandbox_validation/
├── README.md                    # This file
├── results/                     # Test execution outputs
│   ├── sandbox_S1_league_pre.csv
│   ├── sandbox_S1_league_post.csv
│   ├── sandbox_S1_league_summary.md
│   ├── sandbox_S2_knockout_pre.csv
│   ├── ...
├── scripts/                     # Automation scripts
│   ├── export_skills.py         # Extract player skills from DB
│   ├── calculate_deltas.py      # Compute skill changes
│   └── generate_report.py       # Create validation report
└── SANDBOX_VALIDATION_REPORT.md # Final consolidated report
```

---

## Quick Start

### 1. Start Sandbox Environment
```bash
cd /Users/lovas.zoltan/Seafile/Football\ Investment/Projects/Football\ Investment\ Internship/practice_booking_system
source venv/bin/activate
streamlit run streamlit_sandbox.py --server.port 8502 --server.headless false
```

### 2. Export Pre-Tournament Skills
```bash
python tests/sandbox_validation/scripts/export_skills.py --scenario S1 --phase pre
```

### 3. Run Tournament in Sandbox UI
- Navigate to `http://localhost:8502`
- Configure tournament (type, players, format)
- Execute full simulation
- Record results

### 4. Export Post-Tournament Skills
```bash
python tests/sandbox_validation/scripts/export_skills.py --scenario S1 --phase post
```

### 5. Calculate & Validate
```bash
python tests/sandbox_validation/scripts/calculate_deltas.py --scenario S1
```

---

## Test Status

| Scenario | Status | Executor | Date | Result |
|----------|--------|----------|------|--------|
| S1 - League | ⚫ PENDING | TBD | TBD | - |
| S2 - Knockout | ⚫ PENDING | TBD | TBD | - |
| S3 - Hybrid | ⚫ PENDING | TBD | TBD | - |
| S4 - Individual Ranking | ⚫ PENDING | TBD | TBD | - |
| S5 - Group Stage Only | ⚫ PENDING | TBD | TBD | - |

**Overall Status:** NOT STARTED
**Deadline:** TBD (assign team & set target date)

---

## Validation Criteria

**PASS if:**
- Winners gain skills (positive Δ)
- Losers lose skills (negative Δ)
- Skill changes correlate with tournament placement
- No boundary violations (10 ≤ skill ≤ 100)

**FAIL if:**
- Logic inversion (winner loses skills)
- Boundary violations
- XP/skill inconsistency

---

**Next Action:** Assign QA engineer & set execution deadline
