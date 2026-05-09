"""
Sponsor PROMOTION_EVENT REWARDS_DISTRIBUTED Verifier
=====================================================
Verifies up to 38 invariants for sponsor-event tournaments:
  S1–S7   : Standard lifecycle invariants
  SP1–SP7 : Sponsor-specific invariants
  U1–U9   : UI-readiness invariants
  SK1–SK8 : Skill progression invariants (single-tournament)
  SK9–SK18: SC-06 multi-skill / cross-tournament cumulative invariants
            (SK14–SK16, SK18 require a second <sc05_tournament_id> argument)

Usage:
  # SC-05 (single-tournament, 31 invariants):
  PYTHONPATH=. python scripts/verify_sponsor_rewards_distributed.py <tournament_id>

  # SC-06 (multi-tournament, up to 38 invariants):
  PYTHONPATH=. python scripts/verify_sponsor_rewards_distributed.py <sc06_tid> <sc05_tid>

Exit code:
  0  — all invariants pass
  1  — one or more invariants failed
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lfa_intern_system")
os.environ.setdefault("SECRET_KEY", "e2e-test-secret-key-minimum-32-chars-needed")

from sqlalchemy import text

from app.database import SessionLocal
from app.models.semester import Semester
from app.models.semester_enrollment import SemesterEnrollment
from app.models.sponsor import SponsorAudienceEntry, SponsorCampaign
from app.models.team import TournamentPlayerCheckin
from app.models.tournament_instructor_slot import TournamentInstructorSlot
from app.models.tournament_ranking import TournamentRanking
from app.models.tournament_status_history import TournamentStatusHistory
from app.models.license import UserLicense
from app.models.football_skill_assessment import FootballSkillAssessment
from app.models.tournament_achievement import TournamentParticipation
from app.services.skill_progression import get_all_skill_keys


_PASS = "PASS"
_FAIL = "FAIL"


def _check(label: str, condition: bool, detail: str = "") -> bool:
    status = _PASS if condition else _FAIL
    suffix = f"  [{detail}]" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return condition


def verify(tid: int, sc05_tid: int | None = None) -> bool:
    db = SessionLocal()
    try:
        t = db.query(Semester).filter(Semester.id == tid).first()
        if not t:
            print(f"ABORT: tournament {tid} not found")
            return False

        # Active participant baseline (used by S3/S4 count checks)
        active_enrolled = db.query(SemesterEnrollment).filter(
            SemesterEnrollment.semester_id == tid,
            SemesterEnrollment.is_active == True,  # noqa: E712
            SemesterEnrollment.request_status == "APPROVED",
        ).count()

        rankings = db.query(TournamentRanking).filter(
            TournamentRanking.tournament_id == tid
        ).all()

        participations = db.execute(
            text(
                "SELECT placement, xp_awarded FROM tournament_participations "
                "WHERE semester_id = :tid"
            ),
            {"tid": tid},
        ).fetchall()

        hist_rd = db.query(TournamentStatusHistory).filter(
            TournamentStatusHistory.tournament_id == tid,
            TournamentStatusHistory.new_status == "REWARDS_DISTRIBUTED",
        ).first()

        cfg = t.tournament_config_obj

        enrolled_uids = {
            r.user_id
            for r in db.query(SemesterEnrollment).filter(
                SemesterEnrollment.semester_id == tid,
                SemesterEnrollment.is_active == True,  # noqa: E712
            ).all()
        }

        audience_uids: set[int] = set()
        if t.organizer_campaign_id:
            audience_uids = {
                e.user_id
                for e in db.query(SponsorAudienceEntry).filter(
                    SponsorAudienceEntry.campaign_id == t.organizer_campaign_id,
                    SponsorAudienceEntry.user_id.isnot(None),
                ).all()
            }

        # UI-readiness extra data
        from app.models.tournament_configuration import TournamentConfiguration
        from app.models.session import Session as SessionModel

        tc = db.query(TournamentConfiguration).filter(
            TournamentConfiguration.semester_id == tid
        ).first()

        instructor_slot = db.query(TournamentInstructorSlot).filter(
            TournamentInstructorSlot.semester_id == tid,
            TournamentInstructorSlot.role == "MASTER",
        ).first()

        player_checkins = db.query(TournamentPlayerCheckin).filter(
            TournamentPlayerCheckin.tournament_id == tid,
        ).all()
        instructor_checkin = (
            db.query(TournamentPlayerCheckin).filter(
                TournamentPlayerCheckin.tournament_id == tid,
                TournamentPlayerCheckin.user_id == (instructor_slot.instructor_id if instructor_slot else -1),
            ).first()
            if instructor_slot else None
        )

        sessions = db.query(SessionModel).filter(SessionModel.semester_id == tid).all()

        results: list[bool] = []

        # ── Header summary block ──────────────────────────────────────────────
        _W = 60
        print()
        print("╔" + "═" * (_W - 2) + "╗")
        print(f"║  SPONSOR EVENT AUDIT — tournament {tid}".ljust(_W - 1) + "║")
        print("╠" + "═" * (_W - 2) + "╣")
        print(f"║  Name      : {t.name[:40]}".ljust(_W - 1) + "║")
        print(f"║  Status    : {t.tournament_status}".ljust(_W - 1) + "║")
        print(f"║  Sponsor   : {t.organizer_sponsor_id}  Campaign: {t.organizer_campaign_id}  Club: {t.organizer_club_id}".ljust(_W - 1) + "║")
        print(f"║  Age group : {t.age_group}  Category: {str(t.semester_category).split('.')[-1]}".ljust(_W - 1) + "║")
        print(f"║  Enrolled  : {active_enrolled} active   Rankings: {len(rankings)}   Participations: {len(participations)}".ljust(_W - 1) + "║")
        print("╚" + "═" * (_W - 2) + "╝")
        print()

        print("Standard invariants:")
        results.append(_check("S1 status=REWARDS_DISTRIBUTED", t.tournament_status == "REWARDS_DISTRIBUTED"))
        results.append(_check("S2 reward_policy_snapshot IS NOT NULL", bool(t.reward_policy_snapshot)))
        results.append(_check(
            f"S3 TournamentRanking count={len(rankings)} == baseline={active_enrolled}",
            len(rankings) == active_enrolled,
        ))
        results.append(_check(
            f"S4 TournamentParticipation count={len(participations)} == baseline={active_enrolled}",
            len(participations) == active_enrolled,
        ))
        results.append(_check("S5 all xp_awarded >= 0", all((p[1] or 0) >= 0 for p in participations)))
        results.append(_check("S6 at least 1 placement=1", any(p[0] == 1 for p in participations)))
        results.append(_check("S7 REWARDS_DISTRIBUTED in status history", hist_rd is not None))

        print("\nSponsor invariants:")
        results.append(_check("SP1 organizer_sponsor_id IS NOT NULL", t.organizer_sponsor_id is not None))
        results.append(_check("SP2 organizer_campaign_id IS NOT NULL", t.organizer_campaign_id is not None))
        results.append(_check("SP3 organizer_club_id IS NULL", t.organizer_club_id is None))
        results.append(_check(
            "SP4 participant_type=INDIVIDUAL",
            (cfg.participant_type if cfg else None) == "INDIVIDUAL",
            f"got {cfg.participant_type if cfg else 'no cfg'}",
        ))
        results.append(_check(
            "SP5 semester_category=PROMOTION_EVENT",
            str(t.semester_category) in ("PROMOTION_EVENT", "SemesterCategory.PROMOTION_EVENT"),
            str(t.semester_category),
        ))
        results.append(_check(
            "SP6 enrolled_uids ⊆ audience_uids",
            enrolled_uids <= audience_uids,
            f"{len(enrolled_uids - audience_uids)} orphan(s)" if not (enrolled_uids <= audience_uids) else "",
        ))
        results.append(_check("SP7 age_group IS NOT NULL", bool(t.age_group), str(t.age_group)))

        print("\nUI-readiness invariants:")

        # U1 — schedule config populated
        sched_ok = bool(
            tc
            and tc.match_duration_minutes is not None
            and tc.break_duration_minutes is not None
        )
        results.append(_check(
            "U1 match_duration_minutes IS NOT NULL",
            sched_ok,
            f"match={tc.match_duration_minutes if tc else 'no cfg'}"
            f"  break={tc.break_duration_minutes if tc else 'no cfg'}",
        ))

        # U2 — credits > 0 for top-3 in tournament_participations
        top3_credits = db.execute(
            text(
                "SELECT SUM(credits_awarded) FROM tournament_participations "
                "WHERE semester_id = :tid AND placement <= 3"
            ),
            {"tid": tid},
        ).scalar() or 0
        results.append(_check(
            "U2 top-3 credits_awarded > 0",
            top3_credits > 0,
            f"total credits for placements 1-3: {top3_credits}",
        ))

        # U3 — MASTER instructor slot exists
        results.append(_check(
            "U3 MASTER instructor slot exists",
            instructor_slot is not None,
        ))

        # U4 — instructor slot status != ABSENT
        results.append(_check(
            "U4 instructor slot status != ABSENT",
            instructor_slot is not None and instructor_slot.status != "ABSENT",
            f"status={instructor_slot.status if instructor_slot else 'no slot'}",
        ))

        # U5 — instructor check-in record exists in tournament_player_checkins
        results.append(_check(
            "U5 instructor check-in record exists",
            instructor_checkin is not None,
        ))

        # U6 — 9 player check-ins in tournament_player_checkins
        player_only_checkins = [
            c for c in player_checkins
            if not instructor_slot or c.user_id != instructor_slot.instructor_id
        ]
        results.append(_check(
            f"U6 player check-ins == {active_enrolled}",
            len(player_only_checkins) == active_enrolled,
            f"got {len(player_only_checkins)}",
        ))

        # U7 — at least 1 ranking with points > 0 (ranking service parsed game_results)
        rank_pts_ok = db.execute(
            text(
                "SELECT COUNT(*) FROM tournament_rankings "
                "WHERE tournament_id = :tid AND points > 0"
            ),
            {"tid": tid},
        ).scalar() or 0
        results.append(_check(
            "U7 at least 1 ranking with points > 0",
            rank_pts_ok > 0,
            f"rankings with points>0: {rank_pts_ok}",
        ))

        # U8 — rank-1 xp_awarded > 0 (reward was distributed to tournament winner)
        rank1_xp = db.execute(
            text(
                "SELECT xp_awarded FROM tournament_participations "
                "WHERE semester_id = :tid AND placement = 1 LIMIT 1"
            ),
            {"tid": tid},
        ).scalar() or 0
        results.append(_check(
            "U8 rank-1 xp_awarded > 0",
            rank1_xp > 0,
            f"rank-1 xp_awarded={rank1_xp}",
        ))

        # U9 — at least 1 session with rounds_data NOT NULL (score detail visible)
        sessions_with_rounds = sum(1 for s in sessions if s.rounds_data)
        results.append(_check(
            "U9 at least 1 session with rounds_data",
            sessions_with_rounds > 0,
            f"{sessions_with_rounds}/{len(sessions)} sessions have rounds_data",
        ))

        # ── SK: Skill Progression invariants ─────────────────────────────────
        print("\nSkill progression invariants:")

        # Collect all participation ORM rows for this tournament
        tp_rows = db.query(TournamentParticipation).filter(
            TournamentParticipation.semester_id == tid
        ).all()

        # Collect license_ids for all enrolled users
        enrolled_user_ids = list(enrolled_uids)
        licenses = db.query(UserLicense).filter(
            UserLicense.user_id.in_(enrolled_user_ids),
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,  # noqa: E712
        ).all()
        lic_ids = [l.id for l in licenses]
        lic_by_uid = {l.user_id: l for l in licenses}

        # SK1 — skill_rating_delta IS NOT NULL for all participations
        delta_non_null = [p for p in tp_rows if p.skill_rating_delta is not None]
        results.append(_check(
            f"SK1 skill_rating_delta IS NOT NULL ({len(delta_non_null)}/{len(tp_rows)})",
            len(delta_non_null) == len(tp_rows) and len(tp_rows) > 0,
        ))

        # SK2 — at least 1 participation has non-empty skill_rating_delta dict
        delta_non_empty = [p for p in tp_rows if p.skill_rating_delta]
        results.append(_check(
            "SK2 at least 1 non-empty skill_rating_delta",
            len(delta_non_empty) > 0,
            f"{len(delta_non_empty)}/{len(tp_rows)} with delta",
        ))

        # SK3 — FootballSkillAssessment rows exist for enrolled users
        fsa_count = db.query(FootballSkillAssessment).filter(
            FootballSkillAssessment.user_license_id.in_(lic_ids)
        ).count() if lic_ids else 0
        results.append(_check(
            "SK3 FootballSkillAssessment rows > 0",
            fsa_count > 0,
            f"{fsa_count} FSA rows across {len(lic_ids)} licenses",
        ))

        # SK4 — onboarding_completed = True for all enrolled player licenses
        onboard_ok = [l for l in licenses if l.onboarding_completed]
        results.append(_check(
            f"SK4 onboarding_completed=True ({len(onboard_ok)}/{len(licenses)})",
            len(onboard_ok) == len(licenses) and len(licenses) > 0,
        ))

        # SK5 — football_skills IS NOT NULL for all enrolled player licenses
        skills_set = [l for l in licenses if l.football_skills]
        results.append(_check(
            f"SK5 football_skills IS NOT NULL ({len(skills_set)}/{len(licenses)})",
            len(skills_set) == len(licenses) and len(licenses) > 0,
        ))

        # SK6 — rank-1 player card overall >= 60 (proxy: get_skill_profile average_level)
        rank1_part = next((p for p in tp_rows if p.placement == 1), None)
        if rank1_part and rank1_part.user_id in lic_by_uid:
            from app.services.skill_progression import get_skill_profile
            sp = get_skill_profile(db, rank1_part.user_id)
            rank1_overall = round(sp.get("average_level", 0), 1)
        else:
            rank1_overall = 0.0
        results.append(_check(
            "SK6 rank-1 player card overall >= 60",
            rank1_overall >= 60.0,
            f"overall={rank1_overall}",
        ))

        # SK7 — all skill_mappings keys are valid (in get_all_skill_keys())
        valid_keys = get_all_skill_keys()
        rc = t.reward_config or {}
        sm = rc.get("skill_mappings", [])
        invalid_keys = [
            m.get("skill") for m in sm
            if isinstance(m, dict) and m.get("skill") not in valid_keys
        ]
        results.append(_check(
            "SK7 skill_mappings keys all valid",
            len(sm) > 0 and len(invalid_keys) == 0,
            f"invalid={invalid_keys}" if invalid_keys else f"{len(sm)} mapping(s) valid",
        ))

        # SK8 — rank-1 football_skills has at least 1 non-baseline entry (delta applied)
        rank1_lic = lic_by_uid.get(rank1_part.user_id) if rank1_part else None
        if rank1_lic and rank1_lic.football_skills and isinstance(rank1_lic.football_skills, dict):
            baseline = 60.0
            changed = [
                (k, v) for k, v in rank1_lic.football_skills.items()
                if isinstance(v, dict) and abs(v.get("current_level", baseline) - baseline) > 0.05
                or isinstance(v, (int, float)) and abs(float(v) - baseline) > 0.05
            ]
            sk8_ok = len(changed) > 0
            sk8_detail = f"{len(changed)} skill(s) differ from baseline"
        else:
            sk8_ok = False
            sk8_detail = "no football_skills or rank-1 not found"
        results.append(_check(
            "SK8 rank-1 football_skills has delta-applied skill(s)",
            sk8_ok,
            sk8_detail,
        ))

        # ── SK9–SK18: SC-06 multi-skill / cross-tournament invariants ────────
        # Runs when this tournament has 2+ skill mappings (SC-06 preset profile).
        # SK14, SK15, SK16, SK18 additionally require sc05_tid to be provided.
        sc06_skill_mappings = sm  # already extracted above (reward_config.skill_mappings)
        if len(sc06_skill_mappings) >= 2:
            print("\nSC-06 multi-skill / cumulative invariants:")

            # Fetch TP rows with skill_rating_delta for this tournament
            tp_full = db.query(TournamentParticipation).filter(
                TournamentParticipation.semester_id == tid
            ).all()

            # SK9 — SC-06 TP count == active enrolled baseline (alias of S4, explicit label)
            results.append(_check(
                f"SK9 TP count={len(tp_full)} == enrolled={active_enrolled}",
                len(tp_full) == active_enrolled and active_enrolled > 0,
            ))

            # SK10 — all non-null TP deltas contain all 6 preset skill keys
            sc06_preset_keys = {m["skill"] for m in sc06_skill_mappings if isinstance(m, dict) and m.get("enabled")}
            non_null_tps = [p for p in tp_full if p.skill_rating_delta]
            missing_key_tps = [
                p for p in non_null_tps
                if not sc06_preset_keys.issubset(set((p.skill_rating_delta or {}).keys()))
            ]
            results.append(_check(
                f"SK10 all TP deltas contain all {len(sc06_preset_keys)} preset keys",
                len(non_null_tps) > 0 and len(missing_key_tps) == 0,
                f"{len(missing_key_tps)} TP(s) missing preset keys" if missing_key_tps
                else f"{len(non_null_tps)} TP(s) checked, keys={sorted(sc06_preset_keys)}",
            ))

            # SK11 — rank-1 finishing delta > 0
            rank1_tp = next((p for p in tp_full if p.placement == 1), None)
            rank1_finishing_delta = (rank1_tp.skill_rating_delta or {}).get("finishing", 0.0) if rank1_tp else None
            results.append(_check(
                "SK11 rank-1 finishing delta > 0",
                rank1_finishing_delta is not None and rank1_finishing_delta > 0,
                f"finishing delta={rank1_finishing_delta}",
            ))

            # SK12 — last-place finishing delta < 0
            max_placement = max((p.placement or 0) for p in tp_full) if tp_full else 0
            last_tp = next((p for p in tp_full if p.placement == max_placement), None)
            last_finishing_delta = (last_tp.skill_rating_delta or {}).get("finishing", 0.0) if last_tp else None
            results.append(_check(
                f"SK12 rank-{max_placement} finishing delta < 0",
                last_finishing_delta is not None and last_finishing_delta < 0,
                f"finishing delta={last_finishing_delta}",
            ))

            # SK13 — FSA rows with skill_name='sprint_speed' exist (SC-06 archive + new)
            sprint_fsa_count = (
                db.query(FootballSkillAssessment).filter(
                    FootballSkillAssessment.user_license_id.in_(lic_ids),
                    FootballSkillAssessment.skill_name == "sprint_speed",
                ).count()
                if lic_ids else 0
            )
            results.append(_check(
                "SK13 sprint_speed FSA rows exist (archive + current)",
                sprint_fsa_count > 0,
                f"{sprint_fsa_count} sprint_speed FSA rows",
            ))

            # SK17 — rank-1 sprint_speed delta > 0 (winner gains on sprint_speed)
            rank1_ss_delta = (rank1_tp.skill_rating_delta or {}).get("sprint_speed", 0.0) if rank1_tp else None
            results.append(_check(
                "SK17 rank-1 sprint_speed delta > 0",
                rank1_ss_delta is not None and rank1_ss_delta > 0,
                f"sprint_speed delta={rank1_ss_delta}",
            ))

            # ── Cross-tournament invariants (require sc05_tid) ────────────────
            if sc05_tid:
                _q = text(
                    "SELECT skill_rating_delta FROM tournament_participations "
                    "WHERE semester_id = :tid AND placement = 1 LIMIT 1"
                )
                sc05_rank1_row = db.execute(_q, {"tid": sc05_tid}).fetchone()
                sc05_rank1_delta = (sc05_rank1_row[0] or {}) if sc05_rank1_row else {}

                _q_last = text(
                    "SELECT skill_rating_delta FROM tournament_participations "
                    "WHERE semester_id = :tid ORDER BY placement DESC LIMIT 1"
                )
                sc05_last_row = db.execute(_q_last, {"tid": sc05_tid}).fetchone()
                sc05_last_delta = (sc05_last_row[0] or {}) if sc05_last_row else {}

                # SK14 — SC-06 sprint_speed delta < SC-05 sprint_speed delta (rank-1 of SC-05)
                # Diminishing returns: EMA prev_val for sprint_speed was elevated by SC-05.
                # Uses SC-05 tournament's rank-1 delta (the strongest single-tournament signal).
                sc05_ss = sc05_rank1_delta.get("sprint_speed", 0.0)
                sc06_ss = rank1_ss_delta or 0.0
                results.append(_check(
                    "SK14 SC-06 sprint_speed delta < SC-05 delta (diminishing returns)",
                    sc06_ss > 0 and sc05_ss > 0 and sc06_ss < sc05_ss,
                    f"SC-05 rank-1 delta={sc05_ss:.1f}, SC-06 rank-1 delta={sc06_ss:.1f}",
                ))

                # SK15 — SC-06 rank-1 sprint_speed current_level reflects BOTH tournaments.
                # Key: SC-06 rank-1 may be a different user than SC-05 rank-1.
                # Lookup this specific user's own SC-05 TP delta, then check cumulative > SC-05 alone.
                rank1_uid = rank1_tp.user_id if rank1_tp else None
                rank1_lic_sc06 = lic_by_uid.get(rank1_uid) if rank1_uid else None

                sc05_user_row = db.execute(
                    text(
                        "SELECT skill_rating_delta FROM tournament_participations "
                        "WHERE semester_id = :sc05 AND user_id = :uid LIMIT 1"
                    ),
                    {"sc05": sc05_tid, "uid": rank1_uid},
                ).fetchone() if rank1_uid else None
                sc05_user_ss = (sc05_user_row[0] or {}).get("sprint_speed", 0.0) if sc05_user_row else 0.0

                if rank1_lic_sc06 and isinstance(rank1_lic_sc06.football_skills, dict):
                    ss_entry = rank1_lic_sc06.football_skills.get("sprint_speed", {})
                    ss_current = (
                        float(ss_entry.get("current_level", 0))
                        if isinstance(ss_entry, dict) else float(ss_entry or 0)
                    )
                    # SC-05-alone for THIS user: baseline + their own SC-05 sprint_speed delta
                    sc05_alone_for_user = 60.0 + sc05_user_ss
                    sk15_ok = ss_current > sc05_alone_for_user
                    sk15_detail = (
                        f"user={rank1_uid}  current={ss_current:.1f}  "
                        f"SC-05-alone={sc05_alone_for_user:.1f} (60+{sc05_user_ss:.1f})"
                    )
                else:
                    sk15_ok = False
                    sk15_detail = "football_skills not found or not dict for SC-06 rank-1"
                results.append(_check(
                    "SK15 SC-06 rank-1 sprint_speed current_level > their SC-05-alone value",
                    sk15_ok,
                    sk15_detail,
                ))

                # SK16 — last-place sprint_speed current_level < their own SC-05-alone value.
                # SC-06 last-place user may differ from SC-05 last-place; look up their own delta.
                last_uid = last_tp.user_id if last_tp else None
                last_lic = lic_by_uid.get(last_uid) if last_uid else None

                sc05_last_user_row = db.execute(
                    text(
                        "SELECT skill_rating_delta FROM tournament_participations "
                        "WHERE semester_id = :sc05 AND user_id = :uid LIMIT 1"
                    ),
                    {"sc05": sc05_tid, "uid": last_uid},
                ).fetchone() if last_uid else None
                sc05_last_user_ss = (sc05_last_user_row[0] or {}).get("sprint_speed", 0.0) if sc05_last_user_row else 0.0

                if last_lic and isinstance(last_lic.football_skills, dict):
                    ss_entry_last = last_lic.football_skills.get("sprint_speed", {})
                    ss_last_current = (
                        float(ss_entry_last.get("current_level", 0))
                        if isinstance(ss_entry_last, dict) else float(ss_entry_last or 0)
                    )
                    sc05_last_alone = 60.0 + sc05_last_user_ss
                    sk16_ok = ss_last_current < sc05_last_alone
                    sk16_detail = (
                        f"user={last_uid}  current={ss_last_current:.1f}  "
                        f"SC-05-alone={sc05_last_alone:.1f} (60+{sc05_last_user_ss:.1f})"
                    )
                else:
                    sk16_ok = False
                    sk16_detail = "last-place football_skills not found"
                results.append(_check(
                    f"SK16 rank-{max_placement} sprint_speed current_level < their SC-05-alone value",
                    sk16_ok,
                    sk16_detail,
                ))

                # SK18 — rank-1 football_skills sprint_speed tournament_count == 2
                if rank1_lic_sc06 and isinstance(rank1_lic_sc06.football_skills, dict):
                    ss_tc_entry = rank1_lic_sc06.football_skills.get("sprint_speed", {})
                    ss_tc = (
                        int(ss_tc_entry.get("tournament_count", -1))
                        if isinstance(ss_tc_entry, dict) else -1
                    )
                    results.append(_check(
                        "SK18 sprint_speed tournament_count == 2 (both SC-05 + SC-06 counted)",
                        ss_tc == 2,
                        f"tournament_count={ss_tc}",
                    ))
                else:
                    results.append(_check(
                        "SK18 sprint_speed tournament_count == 2",
                        False,
                        "football_skills not accessible for rank-1",
                    ))
            else:
                print("  [SKIP] SK14/SK15/SK16/SK18 — sc05_tid not provided (pass as 2nd arg)")

        # ── SK19: BUG-P0-CARD-01 fix — distribution-time delta == replay delta ──────
        # For rank-1, rank-2 (first non-rank-1 user), and last-place: the stored
        # TP.skill_rating_delta must match a fresh EMA replay.  Pre-fix, rank-2
        # diverged because total_players was partial at distribution time.
        try:
            from app.services.skill_progression._ema_engine import (
                compute_single_tournament_skill_delta,
            )
            probe_ranks = [1, 2, max_placement]
            probe_uids = []
            for pr in probe_ranks:
                rr = db.query(TournamentRanking).filter(
                    TournamentRanking.tournament_id == tid,
                    TournamentRanking.rank == pr,
                ).first()
                if rr and rr.user_id:
                    probe_uids.append((pr, rr.user_id))

            sk19_mismatches = []
            for _rank, _uid in probe_uids:
                _tp = db.query(TournamentParticipation).filter(
                    TournamentParticipation.user_id == _uid,
                    TournamentParticipation.semester_id == tid,
                ).first()
                _stored = _tp.skill_rating_delta or {} if _tp else {}
                _replay = compute_single_tournament_skill_delta(db, _uid, tid)
                for _sk in sorted(set(list(_stored.keys()) + list(_replay.keys()))):
                    _s = round(_stored.get(_sk, 0.0), 1)
                    _r = round(_replay.get(_sk, 0.0), 1)
                    if abs(_s - _r) >= 0.2:
                        sk19_mismatches.append(f"rank{_rank}/{_uid}/{_sk}: stored={_s} replay={_r}")

            sk19_ok = len(sk19_mismatches) == 0
            sk19_detail = (
                f"{len(probe_uids)} users checked, 0 mismatches"
                if sk19_ok
                else f"mismatches: {sk19_mismatches}"
            )
            results.append(_check(
                "SK19 BUG-P0-CARD-01 fix: stored delta == replay for rank-1/2/last",
                sk19_ok,
                sk19_detail,
            ))
        except Exception as _e:
            results.append(_check("SK19 BUG-P0-CARD-01 fix", False, str(_e)))

        print("─" * 60)
        passed = sum(results)
        total = len(results)
        all_ok = passed == total
        print(f"{'PASS' if all_ok else 'FAIL'}  {passed}/{total} invariants passed\n")
        return all_ok

    finally:
        db.close()


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print(
            "Usage: PYTHONPATH=. python scripts/verify_sponsor_rewards_distributed.py"
            " <tournament_id> [<sc05_tournament_id>]"
        )
        sys.exit(1)

    import logging
    logging.basicConfig(level=logging.CRITICAL)  # suppress app logs

    tid = int(sys.argv[1])
    sc05_tid = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else None
    ok = verify(tid, sc05_tid=sc05_tid)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
