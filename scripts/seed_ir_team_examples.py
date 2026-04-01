"""
Seed IR+TEAM Examples: Relay Race & Push-Up Challenge
======================================================
Two INDIVIDUAL_RANKING + TEAM tournaments that demonstrate correct ranking direction.

Example 1 — RELAY RACE  (TIME_BASED, ASC)
  Csapatok futóidőt küldenek be. A LEGKISEBB idő = legjobb helyezés.
  ranking_direction='ASC' → növekvő sorrendbe → legalacsonyabb score kap #1-et.

  LFA U15   → 58.30 s   → #3  (leglassabb)
  LFA U18   → 55.10 s   → #2
  LFA Adult → 52.70 s   → #1  (leggyorsabb)

Example 2 — PUSH-UP CHALLENGE  (SCORE_BASED, DESC)
  Csapatok fekvőtámasz-darabszámot küldenek be. A LEGTÖBB ismétlés = legjobb.
  ranking_direction='DESC' → csökkenő sorrendbe → legmagasabb score kap #1-et.

  LFA U15   → 450 reps  → #3  (legkevesebb)
  LFA U18   → 520 reps  → #2
  LFA Adult → 610 reps  → #1  (legtöbb)

Mindkét torna teljes életcikluson megy végig:
  DRAFT → ENROLLMENT_OPEN → (3 csapat beiratkozik) → ENROLLMENT_CLOSED
  → CHECK_IN_OPEN (session-ök autogenerálódnak) → IN_PROGRESS
  → (eredmények beküldése) → (rangsor számítás) → COMPLETED
  → (jutalmak kiosztása) → REWARDS_DISTRIBUTED

Futtatás:
    DATABASE_URL="postgresql://..." PYTHONPATH=. python scripts/seed_ir_team_examples.py
"""
import os
import sys
import uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from fastapi.testclient import TestClient
from sqlalchemy import text as _sql
from sqlalchemy.orm.attributes import flag_modified

from app.main import app
from app.database import SessionLocal
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.session import Session as SessionModel
from app.models.tournament_configuration import TournamentConfiguration
from app.models.game_configuration import GameConfiguration
from app.models.game_preset import GamePreset
from app.models.campus import Campus
from app.models.club import Club
from app.models.team import Team, TeamMember, TournamentTeamEnrollment
from app.models.tournament_reward_config import TournamentRewardConfig
from app.models.tournament_ranking import TournamentRanking
from app.models.user import User
from app.dependencies import (
    get_current_user_web,
    get_current_admin_user_hybrid,
    get_current_admin_or_instructor_user_hybrid,
)

# ── Console helpers ─────────────────────────────────────────────────────────
def ok(msg):   print(f"  ✅  {msg}")
def info(msg): print(f"       {msg}")
def err(msg):  print(f"  ❌  {msg}")


def head(msg):
    bar = "=" * 62
    print(f"\n{bar}\n  {msg}\n{bar}")


# ── DB + prerequisite checks ────────────────────────────────────────────────
db = SessionLocal()

admin = db.query(User).filter(User.email == "admin@lfa.com").first()
instructor = db.query(User).filter(User.email == "instructor@lfa.com").first()
if not admin or not instructor:
    print("❌ admin@lfa.com or instructor@lfa.com not found — run bootstrap_clean.py first")
    sys.exit(1)

campus = db.query(Campus).first()
if not campus:
    print("❌ No campus found — run bootstrap_clean.py first")
    sys.exit(1)

relay_preset = db.query(GamePreset).filter(GamePreset.code == "sprint_relay").first()
pushup_preset = db.query(GamePreset).filter(GamePreset.code == "strength_challenge").first()
if not relay_preset or not pushup_preset:
    print("❌ sprint_relay / strength_challenge preset not found — run bootstrap_clean.py first")
    sys.exit(1)

boot_club = db.query(Club).filter(Club.code == "LFA-BOOT").first()
if not boot_club:
    print("❌ LFA-BOOT club not found — run bootstrap_clean.py first")
    sys.exit(1)

# Fetch the 3 bootstrap teams ordered by name for deterministic assignment
boot_teams: list[Team] = (
    db.query(Team)
    .filter(
        Team.club_id == boot_club.id,
        Team.name.in_(["LFA U15", "LFA U18", "LFA Adult"]),
    )
    .order_by(Team.name)
    .all()
)
if len(boot_teams) != 3:
    print(f"❌ Expected 3 bootstrap teams, found {len(boot_teams)} — run bootstrap_clean.py first")
    sys.exit(1)

app.dependency_overrides[get_current_user_web] = lambda: admin
app.dependency_overrides[get_current_admin_user_hybrid] = lambda: admin
app.dependency_overrides[get_current_admin_or_instructor_user_hybrid] = lambda: admin

client = TestClient(app, follow_redirects=False)


# ── Per-player individual scores ────────────────────────────────────────────
# 12 fő / csapat, 36 játékos összesen. A globális sorrend alapján egyéni
# pozíció kerül kiszámításra; csapatpont = pozíció-összeg (ASC: kisebb = jobb).

RELAY_PLAYER_SCORES = {
    # TIME_BASED: kisebb idő → jobb egyéni pozíció (ASC sort)
    # Adult: leggyorsabb, U18: közepes, U15: leglassabb — de interleaved
    "LFA Adult": [11.80, 11.95, 12.10, 12.20, 12.35, 12.50,
                  12.65, 12.70, 12.85, 13.00, 13.10, 13.25],
    "LFA U18":   [12.00, 12.15, 12.40, 12.55, 12.75, 12.90,
                  13.05, 13.20, 13.40, 13.55, 13.70, 13.90],
    "LFA U15":   [12.60, 12.80, 13.15, 13.35, 13.60, 13.80,
                  14.00, 14.20, 14.40, 14.60, 14.80, 15.00],
}

PUSHUP_PLAYER_SCORES = {
    # SCORE_BASED: több ismétlés → jobb egyéni pozíció (DESC sort)
    # csapatpont = pozíció-összeg (ASC: kisebb összeg = jobb csapat)
    "LFA Adult": [62, 59, 57, 55, 53, 51, 49, 48, 46, 45, 44, 43],
    "LFA U18":   [56, 52, 50, 47, 43, 42, 41, 40, 39, 38, 37, 36],
    "LFA U15":   [44, 42, 40, 38, 35, 34, 33, 32, 31, 30, 29, 28],
}

# ── Reward configs (sport-specific skill mappings) ───────────────────────────

# RELAY RACE — sprint sebesség, gyorsulás, állóképesség fókusz
_RELAY_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "sprint_speed",  "weight": 2.0, "category": "PHYSICAL", "enabled": True},
        {"skill": "stamina",       "weight": 1.5, "category": "PHYSICAL", "enabled": True},
        {"skill": "acceleration",  "weight": 1.3, "category": "PHYSICAL", "enabled": True},
        {"skill": "agility",       "weight": 1.2, "category": "PHYSICAL", "enabled": True},
        {"skill": "reactions",     "weight": 1.0, "category": "MENTAL",   "enabled": True},
    ],
}

# PUSH-UP CHALLENGE — erő, állóképesség, mentális fókusz
_PUSHUP_REWARD_CONFIG = {
    "skill_mappings": [
        {"skill": "strength",   "weight": 2.0, "category": "PHYSICAL", "enabled": True},
        {"skill": "stamina",    "weight": 1.5, "category": "PHYSICAL", "enabled": True},
        {"skill": "composure",  "weight": 1.0, "category": "MENTAL",   "enabled": True},
        {"skill": "balance",    "weight": 0.7, "category": "PHYSICAL", "enabled": True},
        {"skill": "reactions",  "weight": 0.8, "category": "MENTAL",   "enabled": True},
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uid() -> str:
    return uuid.uuid4().hex[:6]


def create_ir_team_tournament(
    name: str,
    scoring_type: str,
    ranking_direction: str,
    measurement_unit: str,
    game_preset: GamePreset,
    reward_config: dict,
) -> Semester:
    """
    Create an INDIVIDUAL_RANKING + TEAM tournament.
      tournament_type_id=None  → format resolves to INDIVIDUAL_RANKING
      participant_type="TEAM"  → csapatok versenyeznek, nem egyéni játékosok
    """
    t = Semester(
        name=name,
        code=f"IRTM-{_uid()}",
        master_instructor_id=instructor.id,
        campus_id=campus.id,
        location_id=campus.location_id,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        status=SemesterStatus.ONGOING,
        semester_category=SemesterCategory.TOURNAMENT,
        tournament_status="DRAFT",
    )
    db.add(t)
    db.flush()

    db.add(TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=None,       # None → INDIVIDUAL_RANKING format
        participant_type="TEAM",       # csapatok versenyeznek
        max_players=6,                 # max 6 csapat
        number_of_rounds=1,
        parallel_fields=1,
        scoring_type=scoring_type,
        ranking_direction=ranking_direction,
        measurement_unit=measurement_unit,
    ))
    db.add(GameConfiguration(semester_id=t.id, game_preset_id=game_preset.id))
    db.add(TournamentRewardConfig(
        semester_id=t.id,
        reward_policy_name=game_preset.name,
        reward_config=reward_config,
    ))
    db.commit()
    db.expire_all()
    ok(f"Created '{t.name}'  id={t.id}")
    info(f"scoring_type={scoring_type}  ranking_direction={ranking_direction}  unit={measurement_unit}")
    return t


def enroll_teams(tid: int) -> list[Team]:
    """Beiratkoztatja mind a 3 bootstrap csapatot a tornára."""
    db.expire_all()
    enrolled = []
    for team in boot_teams:
        existing = (
            db.query(TournamentTeamEnrollment)
            .filter(
                TournamentTeamEnrollment.semester_id == tid,
                TournamentTeamEnrollment.team_id == team.id,
            )
            .first()
        )
        if not existing:
            db.add(TournamentTeamEnrollment(
                semester_id=tid,
                team_id=team.id,
                is_active=True,
                payment_verified=True,
            ))
        else:
            existing.is_active = True
        enrolled.append(team)
    db.commit()
    info(f"Enrolled: {[t.name for t in enrolled]}")
    return enrolled


def transition(tid: int, new_status: str) -> bool:
    r = client.patch(
        f"/api/v1/tournaments/{tid}/status",
        json={"new_status": new_status, "reason": "seed-ir-team-example"},
    )
    if r.status_code != 200:
        err(f"Transition → {new_status} failed: {r.status_code}  {r.text[:200]}")
        return False
    db.expire_all()
    ok(f"→ {new_status}")
    return True


def submit_ir_team_results(tid: int, team_scores: dict) -> int:
    """
    Eredmények beküldése IR+TEAM sessionökhöz.

    team_scores: {csapat neve: numerikus eredmény}
      Relay Race: {"LFA U15": 58.30, "LFA U18": 55.10, "LFA Adult": 52.70}
      Push-Up:    {"LFA U15": 450.0, "LFA U18": 520.0, "LFA Adult": 610.0}

    Endpoint: PATCH /api/v1/sessions/{id}/team-results
    Payload:  {"results": [{"team_id": X, "score": Y}, ...], "round_number": 1}

    A session.rounds_data["round_results"]["1"] így fog kinézni:
      {"team_123": "52.70", "team_456": "55.10", "team_789": "58.30"}

    calculate_rankings() ezeket a "team_{id}" kulcsokat olvassa és rendezi
    ranking_direction szerint (ASC: legkisebb = #1, DESC: legnagyobb = #1).
    """
    db.expire_all()
    sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()
    submitted = 0

    for sess in sessions:
        enrolled_ids = list(sess.participant_team_ids or [])
        if not enrolled_ids:
            continue

        # Felépítjük a results listát: minden csapatra megkeressük a nevét és a hozzá tartozó score-t
        results = []
        for team_id in enrolled_ids:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team and team.name in team_scores:
                score = team_scores[team.name]
                results.append({"team_id": team_id, "score": score})
                info(f"  {team.name:<12} score={score}")

        if not results:
            err(f"Session {sess.id}: no matching teams found in team_scores dict")
            continue

        r = client.patch(
            f"/api/v1/sessions/{sess.id}/team-results",
            json={"results": results, "round_number": 1},
        )
        if r.status_code in (200, 201):
            submitted += 1
        else:
            err(f"Session {sess.id}: {r.status_code}  {r.text[:150]}")

    info(f"Submitted {submitted} session(s)")
    return submitted


def calculate_rankings(tid: int) -> bool:
    """POST /api/v1/tournaments/{tid}/calculate-rankings"""
    r = client.post(f"/api/v1/tournaments/{tid}/calculate-rankings", json={})
    if r.status_code == 200:
        ok("Rankings calculated")
        return True
    err(f"Rankings failed: {r.status_code}  {r.text[:150]}")
    return False


def distribute_rewards(tid: int) -> bool:
    """POST /api/v1/tournaments/{tid}/distribute-rewards-v2"""
    r = client.post(
        f"/api/v1/tournaments/{tid}/distribute-rewards-v2",
        json={"tournament_id": tid, "force_redistribution": False},
    )
    if r.status_code == 200:
        db.expire_all()
        final = db.query(Semester).filter(Semester.id == tid).first()
        ok(f"Rewards distributed → status: {final.tournament_status}")
        return True
    err(f"Rewards failed: {r.status_code}  {r.text[:150]}")
    return False


def _build_player_scores(player_score_lists: dict) -> dict:
    """
    player_score_lists: {team_name: [score, score, ...]}  (12 érték / csapat)
    Returns: {team_id: {user_id: score}}

    A csapattagokat User.name szerint sorba rendezi, majd index szerint
    rendeli hozzájuk a score listát.
    """
    result = {}
    for team in boot_teams:
        if team.name not in player_score_lists:
            continue
        scores = player_score_lists[team.name]
        members = (
            db.query(TeamMember, User)
            .join(User, User.id == TeamMember.user_id)
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .order_by(User.name)
            .all()
        )
        if len(members) != len(scores):
            err(f"  {team.name}: {len(members)} tag, de {len(scores)} score → skip")
            continue
        result[team.id] = {tm.user_id: score for (tm, _u), score in zip(members, scores)}
    return result


def _add_player_data(sess_id: int, team_player_scores: dict, ranking_direction: str):
    """
    team_player_scores: {team_id: {user_id: float}}
    ranking_direction: "ASC" (kisebb = jobb pozíció, pl. futóidő)
                       "DESC" (nagyobb = jobb pozíció, pl. fekvőtámasz)

    1. Globális pozíciósorend kiszámítása (1=legjobb)
    2. player_data dict felépítése: {"user_{id}": {score, position, team_id}}
    3. Csapat pozíció-összegek kiszámítása
    4. rounds_data frissítése: player_data + team_{id}=pozíció-összeg
    5. session_status="completed" beállítása
    """
    db.expire_all()
    sess = db.query(SessionModel).filter(SessionModel.id == sess_id).first()
    if not sess:
        err(f"  Session {sess_id} not found")
        return

    # Lapítás: [(user_id, score, team_id)]
    all_players = [
        (uid, score, tid)
        for tid, umap in team_player_scores.items()
        for uid, score in umap.items()
    ]
    reverse_sort = (ranking_direction == "DESC")
    sorted_players = sorted(all_players, key=lambda x: x[1], reverse=reverse_sort)
    positions = {uid: pos + 1 for pos, (uid, _, _) in enumerate(sorted_players)}

    # player_data + csapat pozíció-összegek
    player_data: dict = {}
    team_pos_sums: dict = {}
    for uid, score, tid in all_players:
        pos = positions[uid]
        player_data[f"user_{uid}"] = {
            "score": str(score),
            "position": pos,
            "team_id": tid,
        }
        team_pos_sums[tid] = team_pos_sums.get(tid, 0) + pos

    # rounds_data frissítése
    rd = dict(sess.rounds_data or {})
    if "round_results" not in rd:
        rd["round_results"] = {}
    rr = dict(rd["round_results"].get("1", {}))
    rr["player_data"] = player_data
    for tid, pos_sum in team_pos_sums.items():
        rr[f"team_{tid}"] = str(pos_sum)
    rd["round_results"]["1"] = rr
    rd["completed_rounds"] = max(rd.get("completed_rounds", 0), 1)
    sess.rounds_data = rd
    flag_modified(sess, "rounds_data")  # required: SQLAlchemy JSONB mutation detection
    sess.session_status = "completed"
    db.commit()
    db.expire_all()

    # Összefoglaló
    info(f"  player_data: {len(player_data)} bejegyzés")
    for tid, pos_sum in sorted(team_pos_sums.items(), key=lambda x: x[1]):
        team = db.query(Team).filter(Team.id == tid).first()
        info(f"  {(team.name if team else str(tid)):<14}  pos-sum={pos_sum}")


def print_final_rankings(tid: int, measurement_unit: str):
    """Kiírja a végső rangsort a TournamentRanking táblából."""
    db.expire_all()
    rankings = (
        db.query(TournamentRanking)
        .filter(TournamentRanking.tournament_id == tid)
        .order_by(TournamentRanking.rank)
        .all()
    )
    info(f"  {'Rank':<6}  {'Team':<20}  Score")
    info(f"  {'────':<6}  {'────':<20}  ─────")
    for rk in rankings:
        team = db.query(Team).filter(Team.id == rk.team_id).first()
        team_name = team.name if team else f"team_{rk.team_id}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rk.rank, "  ")
        info(f"  {medal} #{rk.rank:<4}  {team_name:<20}  {rk.points} {measurement_unit}")


# ── Cleanup: delete previous runs ───────────────────────────────────────────
_SEED_PATTERNS = ["Relay Race —", "Push-Up Challenge —"]
_existing_ids = []
for pattern in _SEED_PATTERNS:
    rows = db.execute(
        _sql(f"SELECT id FROM semesters WHERE name LIKE :p"), {"p": f"{pattern}%"}
    ).fetchall()
    _existing_ids.extend(r[0] for r in rows)

if _existing_ids:
    print(f"\n🧹  Cleaning up {len(_existing_ids)} previous example tournament(s)...")
    id_list = ", ".join(str(i) for i in _existing_ids)
    for tbl in [
        "tournament_reward_configs", "tournament_skill_mappings",
        "tournament_configurations", "game_configurations",
        "semester_enrollments", "tournament_team_enrollments",
        "tournament_player_checkins", "tournament_rankings",
        "tournament_participations", "tournament_reward_distributions",
        "tournament_instructor_slots", "sessions",
    ]:
        try:
            db.execute(_sql(f"DELETE FROM {tbl} WHERE semester_id IN ({id_list})"))
        except Exception:
            db.rollback()
    for col, tbl in [
        ("related_semester_id", "notifications"),
        ("tournament_id", "tournament_status_history"),
    ]:
        try:
            db.execute(_sql(f"DELETE FROM {tbl} WHERE {col} IN ({id_list})"))
        except Exception:
            db.rollback()
    try:
        db.execute(_sql(f"DELETE FROM semesters WHERE id IN ({id_list})"))
    except Exception:
        db.rollback()
    db.commit()
    print("✅  Cleanup done.\n")


# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE 1 — RELAY RACE
# IR + TEAM · TIME_BASED · ranking_direction='ASC' (kisebb idő = jobb helyezés)
# ══════════════════════════════════════════════════════════════════════════════
head("EXAMPLE 1 — RELAY RACE  (IR + TEAM · TIME_BASED · ASC)")
print()
print("  📐 Logika: KISEBB idő = JOBB helyezés")
print("     ranking_direction='ASC' → növekvő sorrend → legkisebb score lesz #1")
print()
print("  Csapatok és várt eredmény:")
print("    LFA U15   →  58.30 s  →  #3  (leglassabb)")
print("    LFA U18   →  55.10 s  →  #2")
print("    LFA Adult →  52.70 s  →  #1  (leggyorsabb)")
print()

# Placeholder csapatpontok (csak a session completion triggerhez — _add_player_data felülírja)
RELAY_SCORES = {
    "LFA U15":   1.0,
    "LFA U18":   1.0,
    "LFA Adult": 1.0,
}

print("  [1/9] Torna létrehozása (DRAFT)")
t_relay = create_ir_team_tournament(
    name="Relay Race — 4×100m Championship 2026",
    scoring_type="TIME_BASED",
    ranking_direction="ASC",
    measurement_unit="s",
    game_preset=relay_preset,
    reward_config=_RELAY_REWARD_CONFIG,
)

print("\n  [2/9] Beiratkozás megnyitása")
transition(t_relay.id, "ENROLLMENT_OPEN")

print("\n  [3/9] 3 csapat beiratkoztatása")
enroll_teams(t_relay.id)

print("\n  [4/9] Beiratkozás lezárása")
transition(t_relay.id, "ENROLLMENT_CLOSED")

print("\n  [5/9] Bejelentkezés megnyitása  (session-ök autogenerálódnak)")
if transition(t_relay.id, "CHECK_IN_OPEN"):
    db.expire_all()
    sc = db.query(SessionModel).filter(SessionModel.semester_id == t_relay.id).count()
    info(f"Generált session-ök: {sc} db")

print("\n  [6/9] Torna indítása (IN_PROGRESS)")
transition(t_relay.id, "IN_PROGRESS")

print("\n  [7/9] Egyéni futóidők beküldése + session lezárása")
print("       (a) session completion trigger")
submit_ir_team_results(t_relay.id, RELAY_SCORES)
print("       (b) egyéni player_data + pozíció-összegek beírása")
db.expire_all()
_relay_sessions = db.query(SessionModel).filter(SessionModel.semester_id == t_relay.id).all()
_relay_player_scores = _build_player_scores(RELAY_PLAYER_SCORES)
for sess in _relay_sessions:
    _add_player_data(sess.id, _relay_player_scores, "ASC")

print("\n  [8/9] Rangsor számítás")
print("       calculate_rankings: sum(pozíció-összeg / csapat), sort ASC")
print("       → Adult pos-sum < U18 < U15 → Adult=#1, U18=#2, U15=#3")
calculate_rankings(t_relay.id)
print()
print_final_rankings(t_relay.id, "s")

print("\n  [9/9] Lezárás + jutalmak kiosztása")
if transition(t_relay.id, "COMPLETED"):
    distribute_rewards(t_relay.id)


# ══════════════════════════════════════════════════════════════════════════════
# EXAMPLE 2 — PUSH-UP CHALLENGE
# IR + TEAM · SCORE_BASED · ranking_direction='DESC' (több ismétlés = jobb)
# ══════════════════════════════════════════════════════════════════════════════
head("EXAMPLE 2 — PUSH-UP CHALLENGE  (IR + TEAM · SCORE_BASED · ASC position-sum)")
print()
print("  📐 Logika: egyéni pozíció (1=legtöbb rep), csapatpont = pozíció-összeg")
print("     ranking_direction='ASC' → kisebb pozíció-összeg = jobb csapateredmény")
print()
print("  Csapatok és várt eredmény:")
print("    LFA U15   →  legtöbb rep = kis pos-sum  → #3  (legkevesebb)")
print("    LFA U18   →  ...                         → #2")
print("    LFA Adult →  legtöbb rep = kis pos-sum  → #1  (legtöbb)")
print()

# Placeholder csapatpontok (csak a session completion triggerhez — _add_player_data felülírja)
PUSHUP_SCORES = {
    "LFA U15":   1.0,
    "LFA U18":   1.0,
    "LFA Adult": 1.0,
}

print("  [1/9] Torna létrehozása (DRAFT)")
t_pushup = create_ir_team_tournament(
    name="Push-Up Challenge — Team Edition 2026",
    scoring_type="SCORE_BASED",
    ranking_direction="ASC",   # position-sum modell: kisebb összeg = jobb csapat
    measurement_unit="reps",
    game_preset=pushup_preset,
    reward_config=_PUSHUP_REWARD_CONFIG,
)

print("\n  [2/9] Beiratkozás megnyitása")
transition(t_pushup.id, "ENROLLMENT_OPEN")

print("\n  [3/9] 3 csapat beiratkoztatása")
enroll_teams(t_pushup.id)

print("\n  [4/9] Beiratkozás lezárása")
transition(t_pushup.id, "ENROLLMENT_CLOSED")

print("\n  [5/9] Bejelentkezés megnyitása  (session-ök autogenerálódnak)")
if transition(t_pushup.id, "CHECK_IN_OPEN"):
    db.expire_all()
    sc = db.query(SessionModel).filter(SessionModel.semester_id == t_pushup.id).count()
    info(f"Generált session-ök: {sc} db")

print("\n  [6/9] Torna indítása (IN_PROGRESS)")
transition(t_pushup.id, "IN_PROGRESS")

print("\n  [7/9] Egyéni fekvőtámasz darabszámok beküldése + session lezárása")
print("       (a) session completion trigger")
submit_ir_team_results(t_pushup.id, PUSHUP_SCORES)
print("       (b) egyéni player_data + pozíció-összegek beírása")
db.expire_all()
_pushup_sessions = db.query(SessionModel).filter(SessionModel.semester_id == t_pushup.id).all()
_pushup_player_scores = _build_player_scores(PUSHUP_PLAYER_SCORES)
for sess in _pushup_sessions:
    _add_player_data(sess.id, _pushup_player_scores, "DESC")  # több rep → jobb pozíció

print("\n  [8/9] Rangsor számítás")
print("       calculate_rankings: sum(pozíció-összeg / csapat), sort ASC")
print("       → Adult pos-sum < U18 < U15 → Adult=#1, U18=#2, U15=#3")
calculate_rankings(t_pushup.id)
print()
print_final_rankings(t_pushup.id, "reps")

print("\n  [9/9] Lezárás + jutalmak kiosztása")
if transition(t_pushup.id, "COMPLETED"):
    distribute_rewards(t_pushup.id)


# ── Összefoglalás ──────────────────────────────────────────────────────────
print()
head("KÉSZ — Mindkét példa REWARDS_DISTRIBUTED állapotban")
db.expire_all()
r1 = db.query(Semester).filter(Semester.id == t_relay.id).first()
r2 = db.query(Semester).filter(Semester.id == t_pushup.id).first()
print()
print(f"  Relay Race:        id={r1.id:<6}  status={r1.tournament_status}")
print(f"  Push-Up Challenge: id={r2.id:<6}  status={r2.tournament_status}")
print()
print("  Admin nézet: http://localhost:8000/admin/promotion-events")
print()
print(f"  '{r1.name}'")
print(f"    kártya:  IR · Teams · Time (s) · ↓ Low wins")
print(f"    modell:  pozíció-összeg (ASC) · 36 egyéni futóidő")
print()
print(f"  '{r2.name}'")
print(f"    kártya:  IR · Teams · Score (reps) · ↓ Low wins (position-sum)")
print(f"    modell:  pozíció-összeg (ASC) · 36 egyéni darabszám")
print()
db.close()
