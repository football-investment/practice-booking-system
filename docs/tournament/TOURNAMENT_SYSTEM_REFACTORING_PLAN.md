# 🏆 Tournament System - Complete Refactoring Plan

**Date:** 2026-01-03
**Status:** 🚧 IN PROGRESS
**Priority:** CRITICAL

---

## 📋 Executive Summary

Complete refactoring of the tournament system to support:
1. Multiple tournament types (League, Knockout, Round-Robin)
2. Leaderboard & ranking system
3. Tournament-specific XP/rewards
4. Team-based tournaments
5. Multi-day tournaments
6. Tournament notifications
7. Analytics & statistics

---

## 🎯 Requirements Specification

### 1. Tournament Types 🏆

**Supported Types:**
- **League Format** - All participants play each other, ranked by points
- **Knockout Bracket** - Single/double elimination
- **Round Robin** - Everyone plays everyone
- **Custom** - Extensible for future types

**Implementation:**
- Add `tournament_type` enum to `semesters` table
- Each type has different logic for:
  - Match scheduling
  - Point calculation
  - Winner determination
  - Bracket generation (for knockout)

---

### 2. Leaderboard / Ranking System 📊

**Features:**
- Auto-updated based on game results
- Multiple leaderboard types:
  - Overall tournament ranking
  - Age group rankings
  - Team vs Individual rankings
  - Historical rankings

**Database:**
- `tournament_rankings` table
  - tournament_id (FK to semesters)
  - participant_id (user_id or team_id)
  - participant_type (INDIVIDUAL / TEAM)
  - rank (integer)
  - points (decimal)
  - wins / losses / draws
  - updated_at

**API Endpoints:**
- `GET /api/v1/tournaments/{id}/leaderboard`
- `GET /api/v1/tournaments/{id}/leaderboard?age_group=YOUTH`
- `GET /api/v1/tournaments/{id}/leaderboard?team_id={id}`

---

### 3. Tournament-Specific XP / Reward System 🎁

**Requirements:**
- Different XP calculation than regular sessions
- Tournament-specific rewards (trophies, badges, credits)
- Position-based rewards (1st place = 500 XP, 2nd = 300 XP, etc.)

**Database:**
- Add `tournament_rewards` table
  - tournament_id
  - position (1st, 2nd, 3rd, participant)
  - xp_amount
  - credits_reward
  - badge_id (optional)

**XP Calculation:**
```python
def calculate_tournament_xp(tournament_id, user_id, final_rank):
    # Different logic than session XP
    # Based on: tournament type, rank, participation
    base_xp = get_tournament_base_xp(tournament_id)
    rank_multiplier = get_rank_multiplier(final_rank)
    return base_xp * rank_multiplier
```

---

### 4. Team-Based Tournaments 👥

**Requirements:**
- Support for team registration (not just individuals)
- Team roster management
- Team results tracking
- Mixed tournaments (teams + individuals)

**Database Schema:**

```sql
-- Teams table
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) UNIQUE,
    captain_user_id INTEGER REFERENCES users(id),
    specialization_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Team members
CREATE TABLE team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(50), -- CAPTAIN, PLAYER
    joined_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(team_id, user_id)
);

-- Tournament team enrollments
CREATE TABLE tournament_team_enrollments (
    id SERIAL PRIMARY KEY,
    semester_id INTEGER REFERENCES semesters(id),
    team_id INTEGER REFERENCES teams(id),
    enrollment_date TIMESTAMP DEFAULT NOW(),
    payment_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(semester_id, team_id)
);

-- Update semesters table
ALTER TABLE semesters ADD COLUMN tournament_type VARCHAR(50); -- LEAGUE, KNOCKOUT, ROUND_ROBIN
ALTER TABLE semesters ADD COLUMN participant_type VARCHAR(50); -- INDIVIDUAL, TEAM, MIXED
ALTER TABLE semesters ADD COLUMN is_multi_day BOOLEAN DEFAULT FALSE;
```

**API Endpoints:**
- `POST /api/v1/teams` - Create team
- `POST /api/v1/teams/{id}/members` - Add member
- `POST /api/v1/tournaments/{id}/enroll-team` - Team enrollment
- `GET /api/v1/teams/{id}/tournaments` - Team's tournaments

---

### 5. Multi-Day Tournaments 📅

**Requirements:**
- Tournaments spanning multiple days
- Daily sessions/matches
- Progressive elimination/ranking
- Day-by-day results

**Database:**
- `semesters.is_multi_day` boolean flag
- Sessions spread across multiple dates
- Frontend shows tournament schedule by day

**Example:**
```
Tournament: Winter Cup 2026
- Day 1 (Jan 5): Group Stage (4 sessions)
- Day 2 (Jan 6): Quarterfinals (2 sessions)
- Day 3 (Jan 7): Semifinals + Finals (3 sessions)
```

---

### 6. Tournament-Specific Notification System 🔔

**Events to Notify:**
- Tournament created / opened for enrollment
- Enrollment confirmed
- Tournament starting soon (24h before)
- Match schedule released
- Your match is starting (1h before)
- Match results posted
- Tournament completed - final rankings
- Rewards distributed

**Database:**
```sql
-- Tournament notifications (extends existing notifications table)
-- Add tournament-specific notification types
INSERT INTO notification_types VALUES
    ('TOURNAMENT_ENROLLMENT_OPEN'),
    ('TOURNAMENT_STARTING_SOON'),
    ('TOURNAMENT_MATCH_REMINDER'),
    ('TOURNAMENT_RESULTS_POSTED'),
    ('TOURNAMENT_COMPLETED');
```

**API:**
- Reuse existing notification system
- Add tournament-specific templates
- Background job: Send reminders before matches

---

### 7. Analytics & Statistics 📈

**Metrics to Track:**

**Tournament-Level:**
- Total participants (individuals / teams)
- Enrollment rate
- Completion rate
- Average attendance per session
- Revenue generated (credits collected)

**Participant-Level:**
- Matches played
- Win/loss/draw record
- Average score
- Ranking progression
- XP earned

**Database:**
```sql
CREATE TABLE tournament_stats (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES semesters(id),
    total_participants INTEGER DEFAULT 0,
    total_teams INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    completed_matches INTEGER DEFAULT 0,
    total_revenue INTEGER DEFAULT 0, -- credits
    avg_attendance_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE participant_tournament_stats (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES semesters(id),
    user_id INTEGER REFERENCES users(id), -- NULL if team-based
    team_id INTEGER REFERENCES teams(id), -- NULL if individual
    matches_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    total_score DECIMAL(10,2) DEFAULT 0,
    avg_score DECIMAL(5,2),
    final_rank INTEGER,
    xp_earned INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tournament_id, user_id),
    UNIQUE(tournament_id, team_id)
);
```

**API Endpoints:**
- `GET /api/v1/tournaments/{id}/stats` - Tournament stats
- `GET /api/v1/tournaments/{id}/participants/{id}/stats` - Participant stats
- `GET /api/v1/analytics/tournaments` - Admin analytics dashboard

---

## 🗂️ Database Migration Plan

### Phase 1: Add Core Tournament Fields
```sql
-- Migration: add_tournament_core_fields.sql
ALTER TABLE semesters
    ADD COLUMN tournament_type VARCHAR(50),
    ADD COLUMN participant_type VARCHAR(50) DEFAULT 'INDIVIDUAL',
    ADD COLUMN is_multi_day BOOLEAN DEFAULT FALSE;

-- Backfill existing tournaments
UPDATE semesters
SET tournament_type = 'LEAGUE',
    participant_type = 'INDIVIDUAL',
    is_multi_day = FALSE
WHERE code LIKE 'TOURN-%';
```

### Phase 2: Create Teams Tables
```sql
-- Migration: create_teams_tables.sql
-- (See schema above)
```

### Phase 3: Create Ranking & Stats Tables
```sql
-- Migration: create_tournament_rankings.sql
-- (See schema above)
```

### Phase 4: Create Rewards Tables
```sql
-- Migration: create_tournament_rewards.sql
-- (See schema above)
```

---

## 🏗️ Implementation Phases

### **PHASE 1: Database & Models** (Priority: HIGH)
**Duration:** 2-3 hours

1. ✅ Write Alembic migrations
2. ✅ Update SQLAlchemy models
3. ✅ Add new enums (TournamentType, ParticipantType)
4. ✅ Create Team, TeamMember models
5. ✅ Create TournamentRanking, TournamentStats models

**Files:**
- `alembic/versions/2026_01_03_xxxx_add_tournament_system.py`
- `app/models/tournament.py` (NEW)
- `app/models/team.py` (NEW)
- `app/models/tournament_stats.py` (NEW)

---

### **PHASE 2: Backend Services** (Priority: HIGH)
**Duration:** 4-5 hours

1. ✅ `TournamentTypeService` - Logic for League/Knockout/RoundRobin
2. ✅ `LeaderboardService` - Ranking calculations
3. ✅ `TournamentXPService` - XP/rewards distribution
4. ✅ `TeamService` - Team CRUD, member management
5. ✅ `TournamentStatsService` - Analytics calculations

**Files:**
- `app/services/tournament/tournament_type_service.py` (NEW)
- `app/services/tournament/leaderboard_service.py` (NEW)
- `app/services/tournament/tournament_xp_service.py` (NEW)
- `app/services/team_service.py` (NEW)
- `app/services/tournament/stats_service.py` (NEW)

---

### **PHASE 3: API Endpoints** (Priority: MEDIUM)
**Duration:** 3-4 hours

1. ✅ Teams API (`/api/v1/teams/**`)
2. ✅ Tournament Enrollment (update for teams)
3. ✅ Leaderboard API (`/api/v1/tournaments/{id}/leaderboard`)
4. ✅ Stats API (`/api/v1/tournaments/{id}/stats`)
5. ✅ Results API (update for tournament types)

**Files:**
- `app/api/api_v1/endpoints/teams/**` (NEW)
- `app/api/api_v1/endpoints/tournaments/leaderboard.py` (NEW)
- `app/api/api_v1/endpoints/tournaments/stats.py` (NEW)

---

### **PHASE 4: Frontend Components** (Priority: MEDIUM)
**Duration:** 5-6 hours

**Admin:**
1. ✅ Tournament Type selector (when creating)
2. ✅ Participant Type selector (Individual / Team / Mixed)
3. ✅ Multi-day tournament setup
4. ✅ Leaderboard viewer
5. ✅ Analytics dashboard

**Student:**
1. ✅ Team creation & management
2. ✅ Team enrollment in tournaments
3. ✅ Leaderboard display
4. ✅ Personal tournament stats
5. ✅ Multi-day schedule view

**Instructor:**
1. ✅ Enter match results (updated for tournament types)
2. ✅ View leaderboard during tournament
3. ✅ Team management (if needed)

**Files:**
- `streamlit_app/components/teams/**` (NEW)
- `streamlit_app/components/tournaments/leaderboard.py` (NEW)
- `streamlit_app/components/tournaments/tournament_stats.py` (NEW)
- `streamlit_app/components/admin/tournament_type_manager.py` (UPDATE)

---

### **PHASE 5: Notifications** (Priority: LOW)
**Duration:** 2-3 hours

1. ✅ Add tournament notification types
2. ✅ Create tournament notification templates
3. ✅ Background job: Send reminders before matches
4. ✅ Result notifications

**Files:**
- `app/services/notification_service.py` (UPDATE)
- `app/background/tournament_reminders.py` (NEW)

---

### **PHASE 6: Testing & Documentation** (Priority: MEDIUM)
**Duration:** 3-4 hours

1. ✅ Update E2E tests for tournament types
2. ✅ Test team enrollment flow
3. ✅ Test leaderboard calculations
4. ✅ Test XP distribution
5. ✅ Update documentation

**Files:**
- `tests/e2e/tournament/**` (UPDATE)
- `docs/TOURNAMENT_SYSTEM_COMPLETE.md` (NEW)

---

## 🚀 Quick Start Implementation Order

**TODAY (CRITICAL):**
1. Database migrations (Phase 1)
2. Models (Phase 1)
3. Core services (Phase 2: TournamentTypeService, LeaderboardService)

**TOMORROW:**
4. API endpoints (Phase 3)
5. Frontend components (Phase 4: Admin tournament type selector)

**DAY 3:**
6. Team support (Backend + Frontend)
7. Multi-day support

**DAY 4:**
8. Notifications (Phase 5)
9. Analytics (Phase 4 + Frontend)

**DAY 5:**
10. Testing (Phase 6)
11. Documentation cleanup

---

## ❌ What to Remove (Cleanup)

**Delete these outdated concepts:**
1. ❌ "Half-day / Full-day / Intensive" templates → Replace with Tournament Types
2. ❌ Single-day only assumptions → Support multi-day
3. ❌ Individual-only tournaments → Support teams
4. ❌ Generic XP calculation → Tournament-specific XP

**Files to review/cleanup:**
- `streamlit_app/components/tournaments/player_tournament_generator.py` - Remove day-based templates
- `app/services/tournament_service.py` - Add tournament type logic
- `docs/TOURNAMENT_GAME_WORKFLOW.md` - Update with new specs

---

## 📊 Success Criteria

**Minimum Viable Product (MVP):**
- ✅ Create League tournament
- ✅ Students enroll (individual)
- ✅ Instructor enters results
- ✅ Leaderboard auto-updates
- ✅ XP distributed based on rank
- ✅ Stats visible to participants

**Full Feature Set:**
- ✅ All 3 tournament types working
- ✅ Team-based tournaments functional
- ✅ Multi-day tournaments supported
- ✅ Notifications sent automatically
- ✅ Analytics dashboard complete
- ✅ E2E tests passing

---

## 🎯 Next Immediate Action

**START HERE:**
1. Create Alembic migration for core tournament fields
2. Update Semester model with new fields
3. Create TournamentType enum
4. Test migration on dev database

**Command:**
```bash
# Create migration
alembic revision -m "add_tournament_system_core_fields"

# Edit migration file
# Run migration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system" alembic upgrade head
```

---

**Prepared by:** Claude Sonnet 4.5
**Last Updated:** 2026-01-03 21:45 CET
**Status:** 🚧 Ready to implement
