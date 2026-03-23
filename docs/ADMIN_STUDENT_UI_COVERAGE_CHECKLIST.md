# Admin & Student UI — Field Coverage Checklist
> Branch: `feature/admin-ui-phase1-architecture` · Updated: 2026-03-22

## Admin Tournament Edit UI (`/admin/tournaments/{id}/edit`)

### Section 1 — Basic Info

| Field | HTML element | API field | PATCH endpoint | UI→DB round-trip test |
|---|---|---|---|---|
| Tournament Name | `#basic-name` | `name` | `PATCH /api/v1/tournaments/{id}` | ✅ (saveBasicInfo JS) |
| Start Date | `#basic-start-date` | `start_date` | same | ✅ |
| End Date | `#basic-end-date` | `end_date` | same | ✅ |
| Enrollment Cost | `#basic-enrollment-cost` | `enrollment_cost` | same | ✅ |
| Age Group | `#basic-age-group` | `age_group` | same | ✅ |
| Max Players | `#basic-max-players` | `max_players` | same | ✅ |
| Location | `#basic-location-id` | `location_id` → `Semester.location_id` | same | ✅ BIND-01 |
| Campus | `#basic-campus-id` | `campus_id` | same | ✅ |
| Tournament Type | `#basic-tournament-type` | `tournament_type_id` → `TournamentConfiguration` | same | ✅ BIND-02 |
| **Participant Type** | **`#basic-participant-type`** | **`participant_type` → `TournamentConfiguration`** | same | **✅ BIND-03 + BIND-07** |
| **Number of Rounds** | **`#basic-rounds`** | **`number_of_rounds` → `TournamentConfiguration`** | same | **✅ BIND-06 + BIND-08** |
| Game Preset | read-only input | n/a — set at creation | n/a | ✅ (read-only, no save) |

### Section 2 — Schedule Configuration

| Field | HTML element | API field | Endpoint | Test |
|---|---|---|---|---|
| Match Duration | `#sched-match-duration` | `match_duration_minutes` | `PATCH /api/v1/tournaments/{id}/schedule-config` | ✅ |
| Break Duration | `#sched-break-duration` | `break_duration_minutes` | same | ✅ |
| Parallel Fields | `#sched-parallel-fields` | `parallel_fields` | same | ✅ |

### Section 4 — Enrolled Players

| Element | Shows | Test |
|---|---|---|
| Player check-in table | enrolled users, check-in status | ✅ SECT-01 (IN_PROGRESS) |

### Section 5 — Session Generation Wizard

| Step | Field | JS widget | Covered |
|---|---|---|---|
| Step 2 | Number of Rounds slider | `#sgw-rounds` (1–10, INDIVIDUAL_RANKING only) | ✅ wizard-coverage CI job |
| Step 2 | Match Duration | `#sgw-match-duration` | ✅ |
| Step 2 | Break Duration | `#sgw-break-duration` | ✅ |
| Step 2 | Parallel Fields | `#sgw-parallel` | ✅ |

### Section 6 — Results & Finalization (Status Lifecycle)

| Status transition | Button text | Endpoint | Test |
|---|---|---|---|
| DRAFT → ENROLLMENT_OPEN | 📢 Open Enrollment | `PATCH /api/v1/tournaments/{id}/status` | ✅ SECT-01 status buttons present |
| ENROLLMENT_OPEN → ENROLLMENT_CLOSED | 🔒 Close Enrollment | same | ✅ |
| ENROLLMENT_CLOSED → IN_PROGRESS | 🚀 Start Tournament | same | ✅ |
| IN_PROGRESS → COMPLETED | 🏁 Finalize Tournament | `POST /api/v1/tournaments/{id}/finalize-tournament` | ✅ FLOW-01 |
| COMPLETED → REWARDS_DISTRIBUTED | 🎁 Distribute Rewards | `POST /api/v1/tournaments/{id}/distribute-rewards-v2` | ✅ FLOW-01 |

### Section 7 — Session Results (IN_PROGRESS+)

| Element | When visible | Format | Endpoint | Test |
|---|---|---|---|---|
| Session result table | IN_PROGRESS / COMPLETED / REWARDS_DISTRIBUTED | INDIVIDUAL_RANKING: per-player scores | `PATCH /api/v1/sessions/{id}/results` | ✅ SECT-01 |
| Session result table | same | HEAD_TO_HEAD: A vs B scores | `PATCH /api/v1/sessions/{id}/head-to-head-results` | ✅ SECT-01 |
| ✅ / ⬜ result badge | per session row | indicates `has_results` | n/a | ✅ SECT-02 |

### Section 8 — Rankings & Skill Delta

| Element | When visible | Endpoint | Test |
|---|---|---|---|
| Calculate Rankings button | session_count > 0, IN_PROGRESS+ | `POST /api/v1/tournaments/{id}/calculate-rankings` | ✅ SECT-02 |
| Rankings table (rank/name/score) | after calculate | `GET /api/v1/tournaments/{id}/rankings` | ✅ SECT-02 |
| XP / Credits / Skill Δ columns | REWARDS_DISTRIBUTED | same | ✅ SECT-03 |

---

## Lifecycle Variant Coverage

| Variant | Template field | API field | Integration test | Cypress test |
|---|---|---|---|---|
| **INDIVIDUAL** participant | `#basic-participant-type` = INDIVIDUAL | `participant_type=INDIVIDUAL` | ✅ BIND-03 + BIND-07 | ⬜ no Cypress admin test |
| **TEAM** participant | `#basic-participant-type` = TEAM | `participant_type=TEAM` | ✅ BIND-03 (PATCH) + BIND-07 (UI) | ⬜ |
| **MIXED** participant | `#basic-participant-type` = MIXED | `participant_type=MIXED` | ⬜ (API exists, no dedicated test) | ⬜ |
| **Single-round** (default) | `#basic-rounds` = 1 | `number_of_rounds=1` | ✅ (default) | ⬜ |
| **Multi-round** (e.g. 3) | `#basic-rounds` = 3 | `number_of_rounds=3` | ✅ BIND-06 (PATCH) + BIND-08 (UI) | ⬜ |
| **HEAD_TO_HEAD** format | auto-set from tournament_type | derived | ✅ LC-01 / LC-02 | ⬜ |

---

## Student UI Checklist (`/dashboard`, `/skills`, `/credits`, `/sessions`, etc.)

| Page | Element | Test (Cypress) | Status |
|---|---|---|---|
| `/dashboard` (hub) | `.site-header` present | STU-JOURNEY-01 | ✅ Fixed 2026-03-22 |
| `/dashboard` (hub) | No server 500 | STU-JOURNEY-01 | ✅ |
| `/dashboard/LFA_FOOTBALL_PLAYER` | `.student-header` present | STU-JOURNEY-08 | ✅ Fixed 2026-03-22 |
| `/dashboard/LFA_FOOTBALL_PLAYER` | `.student-nav a[href=…lfa-football-player"]` active | STU-JOURNEY-08 | ✅ Fixed 2026-03-22 |
| `/dashboard/LFA_FOOTBALL_PLAYER` | `.footer-links a[href="/dashboard"]` (Hub) | STU-JOURNEY-08 | ✅ Already in template |
| `/dashboard/LFA_FOOTBALL_PLAYER` | `.s-kpi-row` 4 cards, Skill Snapshot, Last Skill Event | STU-JOURNEY-08 | ✅ |
| `/skills` | Skills data loads (29 skills) | STU-JOURNEY-03/04 | ✅ |
| `/skills/history` | Chart renders, timeline entries | STU-JOURNEY-05/06/07 | ✅ |
| `/skills/history` (0 tournaments) | `#sh-empty` visible | STU-JOURNEY-EC-01b | ✅ Fixed 2026-03-22 |
| `/credits` | `.credit-badge` visible with "credits" | STU-WF-04 | ✅ Fixed 2026-03-22 |
| `/credits` | `.balance-amount` visible | STU-WF-04 | ✅ |
| `/sessions` | "Training Sessions" heading visible | BW-BOOK-01, INST-WF-01 | ✅ Fixed 2026-03-22 |

---

## CI Pipeline — Cypress Trigger Matrix

| Trigger | cypress-web-e2e runs? | Blocking? |
|---|---|---|
| Push to `feature/*` | ❌ No (Test Baseline Check only) | — |
| Push to `develop` | ✅ Yes (added 2026-03-22) | Student / instructor / business = blocking; admin = allow_failure |
| Push to `main` | ✅ Yes | same |
| PR to `main` | ✅ Yes | same |
| PR to `develop` | ✅ Yes (added 2026-03-22) | same |
| Manual dispatch | ✅ Yes | same |

### Role matrix

| Role | allow_failure | Blocking failures after 2026-03-22 fix |
|---|---|---|
| admin | true | None (pre-existing, informational) |
| instructor | false | INST-WF-01 ✅ fixed |
| student | false | STU-WF-04, STU-JOURNEY-01/08, EC-01 ✅ all fixed |
| business-workflow | false | BW-BOOK-01 ✅ fixed |
