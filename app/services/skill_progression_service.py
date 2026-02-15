"""
Skill Progression Service V3 - EMA-Based Placement Assessment

Core principle: Incremental online learning (EMA) replaces the static convergence model.

V3 Formula:
    step  = lr × log(1 + weight) / log(2)         [log-normalised, lr=0.20 at weight=1.0]
    delta = step × (placement_skill - prev_value)  [toward placement evidence]
    adjusted_delta:
        win  (delta≥0): delta × opponent_factor    [boost when beating stronger field]
        loss (delta<0): delta / opponent_factor     [soften when losing to stronger field]
    new_value = clamp(prev_value + adjusted_delta, 40, 99)

V3 Properties vs V2:
    - No "dead baseline anchor": prev_value is the running level, not the onboarding score
    - No volatility amplification: EMA step is constant, oscillation stays bounded (±4–5 pt)
    - No drastic T1 jumps: max step ≈ 0.264 (w=1.5) vs V2 0.300
    - Dominant skills always have norm_delta ≥ supporting peers (mathematical guarantee)
    - ELO-inspired opponent_factor: beating strong opponents rewards more

V2 legacy path: call with prev_value=None for backward-compatible behaviour.
"""

import math
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.user import User
from ..models.license import UserLicense
from ..models.tournament_achievement import TournamentParticipation
from ..skills_config import SKILL_CATEGORIES


# Configuration constants
MIN_SKILL_VALUE = 40.0  # Worst possible skill value (last place)
MAX_SKILL_VALUE = 100.0  # Best possible skill value (1st place) - used for percentile mapping
MAX_SKILL_CAP = 99.0  # Hard cap for final skill values (business rule)
DEFAULT_BASELINE = 50.0  # Default if no onboarding data


def _compute_opponent_factor(
    db: Session,
    tournament_id: int,
    player_user_id: int,
    player_baseline_avg: float,
) -> float:
    """
    Compute ELO-inspired opponent strength factor for one tournament.

    Returns avg_opponent_baseline / player_baseline_avg, clamped to [0.5, 2.0].
    Uses onboarding baselines (football_skills JSON) to avoid any circular
    dependency with the running skill values being computed.

    A value > 1.0 means the field was stronger than the player → bigger reward
    for winning, smaller penalty for losing.  A value < 1.0 means weaker field.
    """
    # All participants in this tournament except the focal player
    opponents = (
        db.query(TournamentParticipation)
        .filter(
            TournamentParticipation.semester_id == tournament_id,
            TournamentParticipation.user_id != player_user_id,
        )
        .all()
    )

    if not opponents:
        return 1.0  # Solo tournament → no adjustment

    baseline_avgs = []
    for opp in opponents:
        # Load the opponent's active football-player license
        lic = db.query(UserLicense).filter(
            UserLicense.user_id == opp.user_id,
            UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
            UserLicense.is_active == True,
        ).first()

        if not lic or not isinstance(lic.football_skills, dict):
            continue

        # Average the numeric values from football_skills
        vals = []
        for v in lic.football_skills.values():
            if isinstance(v, dict):
                raw = v.get("baseline", DEFAULT_BASELINE)
            else:
                raw = v
            try:
                vals.append(float(raw))
            except (TypeError, ValueError):
                pass

        if vals:
            baseline_avgs.append(sum(vals) / len(vals))

    if not baseline_avgs:
        return 1.0  # Could not resolve any opponent baseline → neutral

    avg_opponent = sum(baseline_avgs) / len(baseline_avgs)

    # Guard against division by zero
    if player_baseline_avg <= 0:
        return 1.0

    raw_factor = avg_opponent / player_baseline_avg
    return round(max(0.5, min(2.0, raw_factor)), 4)


def _compute_match_performance_modifier(
    db: Session,
    tournament_id: int,
    user_id: int,
) -> float:
    """
    Compute match-level performance modifier for the V3 EMA formula.

    Returns a delta-scale factor in [-1.0, +1.0] used as a multiplicative
    modifier on the EMA raw_delta (not a target shift).

    Formula:
      win_rate_signal = (wins/total - 0.5) × 2       range [-1, +1]
      score_signal    = (gf-ga)/(gf+ga)               range [-1, +1]  (0 if no scores)
      raw_signal      = 0.7 × win_rate_signal + 0.3 × score_signal
      confidence      = 1 - exp(-n/5)                 dampens small samples
      modifier        = raw_signal × confidence        range [-1, +1]

    Confidence behaviour:
      n=1  → 0.18  (minimal weight — 1-match tournament barely shifts delta)
      n=5  → 0.63
      n=10 → 0.86
      n=∞  → 1.00

    0.0 returned if no match data is available.
    For INDIVIDUAL_RANKING tournaments (no score data), score_signal=0 naturally.
    """
    import json as _json
    from app.models.session import Session as SessionModel

    sessions = db.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id,
        SessionModel.is_tournament_game == True,
        SessionModel.game_results.isnot(None),
    ).all()

    wins = losses = draws = 0
    goals_for = goals_against = 0.0

    for sess in sessions:
        if user_id not in (sess.participant_user_ids or []):
            continue
        raw = sess.game_results
        results = _json.loads(raw) if isinstance(raw, str) else raw
        if not results:
            continue
        participants = results.get("participants") or []
        for p in participants:
            if p.get("user_id") == user_id:
                r = str(p.get("result", "")).upper()
                if r == "WIN":
                    wins += 1
                elif r == "LOSS":
                    losses += 1
                else:
                    draws += 1
                goals_for += float(p.get("score") or 0)
            else:
                goals_against += float(p.get("score") or 0)

    total_matches = wins + losses + draws
    if total_matches == 0:
        return 0.0

    win_rate_signal = ((wins / total_matches) - 0.5) * 2.0   # [-1, +1]

    total_goals = goals_for + goals_against
    score_signal = (
        (goals_for - goals_against) / total_goals
        if total_goals > 0 else 0.0
    )                                                          # [-1, +1]

    raw_signal = 0.7 * win_rate_signal + 0.3 * score_signal
    confidence = 1.0 - math.exp(-total_matches / 5.0)
    modifier = raw_signal * confidence

    return round(max(-1.0, min(1.0, modifier)), 4)


def calculate_skill_value_from_placement(
    baseline: float,
    placement: int,
    total_players: int,
    tournament_count: int,
    skill_weight: float = 1.0,
    prev_value: Optional[float] = None,
    learning_rate: float = 0.20,
    opponent_factor: float = 1.0,
    match_performance_modifier: float = 0.0,
) -> float:
    """
    Calculate new skill value from tournament placement.

    V3 EMA path (prev_value is provided):
        Uses Exponential Moving Average (online learning) with:
        - Log-normalised step: step = lr × log(1+w) / log(2)
          → weight=1.0 anchors at lr=0.20; high weights grow sub-linearly (no hard cap needed)
        - Asymmetric ELO opponent factor:
          win  (delta≥0): delta × opponent_factor  (bonus for beating stronger field)
          loss (delta<0): delta / opponent_factor  (reduced penalty for losing to stronger field)
        → Mathematical guarantee: norm_delta ratio = log(1+w_dom)/log(1+w_sup) = constant
        - Match performance multiplier (sign-symmetric delta scaling):
          delta>0: raw × (1+m) — good perf amplifies gain,  bad perf softens gain
          delta<0: raw × (1-m) — good perf softens loss,    bad perf amplifies loss
          modifier ∈ [-1, +1]; confidence-weighted so sparse data → 0 naturally.

    V2 legacy path (prev_value=None):
        Original weighted-average convergence formula (unchanged for backward compat).

    Args:
        baseline:                   Onboarding skill value (used as fallback / legacy anchor)
        placement:                  Tournament placement (1 = best)
        total_players:              Field size
        tournament_count:           Number of prior tournaments for this skill (legacy path only)
        skill_weight:               Reactivity multiplier (0.1–5.0). 1.0 = neutral.
        prev_value:                 Current running skill level (EMA path). None → legacy path.
        learning_rate:              EMA base learning rate (default 0.20, calibrated at weight=1.0)
        opponent_factor:            avg_opponent_baseline / player_baseline, clamped [0.5, 2.0].
                                    1.0 = equal field (no adjustment).
        match_performance_modifier: Confidence-weighted signal in [-1, +1] from
                                    _compute_match_performance_modifier(). 0.0 = no data.

    Returns:
        New skill value, capped to [40.0, 99.0].
    """
    # Shared: placement → placement_skill (unchanged in both paths)
    if total_players == 1:
        percentile = 0.0
    else:
        percentile = (placement - 1) / (total_players - 1)
    placement_skill = MAX_SKILL_VALUE - (percentile * (MAX_SKILL_VALUE - MIN_SKILL_VALUE))

    if prev_value is not None:
        # ── V3 EMA PATH ────────────────────────────────────────────────────────
        # Log-normalised step: anchored at lr when weight=1.0
        step = learning_rate * math.log(1.0 + skill_weight) / math.log(2.0)

        # Raw delta toward placement evidence
        raw_delta = step * (placement_skill - prev_value)

        # Match performance: sign-symmetric delta scaling
        #   raw_delta > 0 (placement says: go up)   → good perf amplifies gain,  bad perf softens gain
        #   raw_delta < 0 (placement says: go down)  → good perf softens loss,   bad perf amplifies loss
        # Formula: coeff = (1 + m) for gain, (1 - m) for loss
        #   m=+1: gain×2, loss×0  →  great perf always helps, never hurts
        #   m=-1: gain×0, loss×2  →  poor perf always hurts, never helps
        if match_performance_modifier != 0.0:
            if raw_delta >= 0:
                raw_delta = raw_delta * (1.0 + match_performance_modifier)
            else:
                raw_delta = raw_delta * (1.0 - match_performance_modifier)

        # Asymmetric opponent factor
        f = max(0.5, min(2.0, opponent_factor))
        if raw_delta >= 0:
            adjusted_delta = raw_delta * f      # win vs strong → bigger reward
        else:
            adjusted_delta = raw_delta / f      # loss vs strong → smaller penalty

        new_val = max(MIN_SKILL_VALUE, min(MAX_SKILL_CAP, prev_value + adjusted_delta))
        return round(new_val, 1)

    # ── V2 LEGACY PATH (unchanged) ─────────────────────────────────────────────
    baseline_weight = 1.0 / (tournament_count + 1)
    placement_weight = tournament_count / (tournament_count + 1)
    new_skill_base = (baseline * baseline_weight) + (placement_skill * placement_weight)
    delta = new_skill_base - baseline
    weighted_delta = delta * skill_weight
    new_skill = baseline + weighted_delta
    return round(max(MIN_SKILL_VALUE, min(MAX_SKILL_CAP, new_skill)), 1)


def get_all_skill_keys() -> List[str]:
    """
    Get list of all skill keys from skills_config.

    Returns:
        List of skill keys (e.g., ["ball_control", "dribbling", ...])
    """
    skill_keys = []
    for category in SKILL_CATEGORIES:
        for skill in category["skills"]:
            skill_keys.append(skill["key"])
    return skill_keys


def get_baseline_skills(db: Session, user_id: int) -> Dict[str, float]:
    """
    Get baseline skill values from UserLicense.football_skills (onboarding).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dict of skill_key → baseline_value (0-100)

    ⚠️ FALLBACK BEHAVIOR FOR MISSING SKILLS:
        If a skill is NOT found in UserLicense.football_skills, it defaults to DEFAULT_BASELINE (50.0).
        This is INTENTIONAL and handles cases where:
        - User completed onboarding with old skill set (before migration to 29 skills)
        - User's onboarding data is incomplete
        - New skills were added to system after user onboarding

        The DEFAULT_BASELINE (50.0) represents "neutral" skill level - neither strong nor weak.
        Tournament placements will then adjust this value up or down based on performance.

    Example:
        User has onboarding data: {"ball_control": 70, "dribbling": 65}
        System now has 29 skills total.
        Result: {"ball_control": 70.0, "dribbling": 65.0, "speed": 50.0, ...other skills... → 50.0}
    """
    # Get active LFA_FOOTBALL_PLAYER license
    license = db.query(UserLicense).filter(
        UserLicense.user_id == user_id,
        UserLicense.specialization_type == "LFA_FOOTBALL_PLAYER",
        UserLicense.is_active == True
    ).first()

    if not license or not license.football_skills:
        # 🔒 GUARD: No onboarding data at all → return all skills at DEFAULT_BASELINE
        return {skill_key: DEFAULT_BASELINE for skill_key in get_all_skill_keys()}

    # 🔒 GUARD: Ensure football_skills is a dict
    if not isinstance(license.football_skills, dict):
        return {skill_key: DEFAULT_BASELINE for skill_key in get_all_skill_keys()}

    baseline_skills = {}
    for skill_key in get_all_skill_keys():
        # ⚠️ FALLBACK: Missing skill defaults to DEFAULT_BASELINE (50.0)
        # This is INTENTIONAL - allows graceful handling of skill migrations
        skill_value = license.football_skills.get(skill_key, DEFAULT_BASELINE)

        if isinstance(skill_value, dict):
            # New format: {"baseline": 70, "current_level": 85, ...}
            baseline_skills[skill_key] = float(skill_value.get("baseline", DEFAULT_BASELINE))
        else:
            # Old format: {"ball_control": 70, ...}
            baseline_skills[skill_key] = float(skill_value)

    return baseline_skills


def calculate_tournament_skill_contribution(
    db: Session,
    user_id: int,
    skill_keys: List[str]
) -> Dict[str, Dict[str, float]]:
    """
    Calculate tournament-based skill contributions for specified skills.

    Args:
        db: Database session
        user_id: User ID
        skill_keys: List of skill keys to calculate (from tournament reward config)

    Returns:
        Dict of skill_key → {
            "contribution": float,  # Net contribution from all tournaments
            "tournament_count": int,  # Number of tournaments affecting this skill
            "current_value": float,  # Current skill value after all tournaments
            "baseline": float  # Original onboarding value
        }

    Logic:
        1. Get user's baseline skills from onboarding
        2. For each tournament participation:
           - Get tournament's selected skills (from reward_config)
           - For each selected skill:
             - Calculate new skill value based on placement
             - Track contribution vs baseline
        3. Return aggregated data per skill
    """
    # Get baseline skills from UserLicense
    baseline_skills = get_baseline_skills(db, user_id)

    # Get all tournament participations for this user (ordered by date)
    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    # Player's average baseline (used to compute opponent_factor per tournament)
    all_baseline_vals = list(baseline_skills.values())
    player_baseline_avg = (sum(all_baseline_vals) / len(all_baseline_vals)) if all_baseline_vals else DEFAULT_BASELINE

    # Track skill evolution across tournaments
    skill_data = {}
    skill_tournament_counts = {}  # Track how many tournaments affected each skill
    skill_previous_values: Dict[str, float] = {}  # Running EMA value per skill

    for skill_key in skill_keys:
        baseline = baseline_skills.get(skill_key, DEFAULT_BASELINE)
        skill_data[skill_key] = {
            "baseline": baseline,
            "current_value": baseline,  # Start with baseline
            "contribution": 0.0,
            "tournament_count": 0
        }
        skill_tournament_counts[skill_key] = 0
        skill_previous_values[skill_key] = baseline

    # Process each tournament participation
    for participation in participations:
        tournament = participation.tournament

        if not tournament:
            continue

        # Build dict of enabled skills with their weights.
        # Priority 1: reward_config.skill_mappings (V2 config-based)
        # Priority 2: TournamentSkillMapping table (legacy / E2E seeded tournaments)
        tournament_skills_with_weights = {}

        reward_config = tournament.reward_config or {}
        skill_mappings = reward_config.get("skill_mappings", [])

        if isinstance(skill_mappings, list) and skill_mappings:
            # V2 format: [{"skill": "passing", "enabled": true, "weight": 1.0}, ...]
            for mapping in skill_mappings:
                if mapping.get("enabled", False) and mapping.get("skill") in skill_keys:
                    tournament_skills_with_weights[mapping["skill"]] = mapping.get("weight", 1.0)
        elif isinstance(skill_mappings, dict) and skill_mappings:
            # Legacy dict format: {"passing": {...}, ...}
            for sk in skill_mappings:
                if sk in skill_keys:
                    tournament_skills_with_weights[sk] = 1.0

        # Fallback: TournamentSkillMapping table (covers tournaments without reward_config skill_mappings)
        if not tournament_skills_with_weights:
            from app.models.tournament_achievement import TournamentSkillMapping as TSM
            table_mappings = (
                db.query(TSM)
                .filter(TSM.semester_id == tournament.id)
                .all()
            )
            for tm in table_mappings:
                if tm.skill_name in skill_keys:
                    tournament_skills_with_weights[tm.skill_name] = float(tm.weight) if tm.weight else 1.0

        if not tournament_skills_with_weights:
            continue

        # Get placement data
        placement = participation.placement
        if not placement:
            continue

        # Get total players in tournament
        total_players = (
            db.query(TournamentParticipation)
            .filter(TournamentParticipation.semester_id == tournament.id)
            .count()
        )

        if total_players == 0:
            continue

        # Opponent factor for this tournament (ELO-inspired)
        opp_factor = _compute_opponent_factor(
            db, tournament.id, user_id, player_baseline_avg
        )
        # Match-level performance modifier (win rate + score differential)
        match_modifier = _compute_match_performance_modifier(
            db, tournament.id, user_id
        )

        # Update each affected skill with its weight
        for skill_key, skill_weight in tournament_skills_with_weights.items():
            if skill_key not in skill_data:
                continue

            baseline = skill_data[skill_key]["baseline"]
            current_count = skill_tournament_counts[skill_key]
            prev_val = skill_previous_values[skill_key]

            new_value = calculate_skill_value_from_placement(
                baseline=baseline,
                placement=placement,
                total_players=total_players,
                tournament_count=current_count + 1,
                skill_weight=skill_weight,
                prev_value=prev_val,
                opponent_factor=opp_factor,
                match_performance_modifier=match_modifier,
            )

            # Update skill data
            skill_data[skill_key]["current_value"] = new_value
            skill_data[skill_key]["contribution"] = new_value - baseline
            skill_data[skill_key]["tournament_count"] = current_count + 1

            # Advance running state
            skill_tournament_counts[skill_key] += 1
            skill_previous_values[skill_key] = new_value

    return skill_data


def compute_single_tournament_skill_delta(
    db: Session,
    user_id: int,
    tournament_id: int,
) -> Dict[str, float]:
    """
    Compute the isolated V3 EMA skill delta for ONE specific tournament.

    Replays the full EMA history up to (but not including) the target tournament,
    then computes the EMA step for the target tournament alone.

    Returns:
        Dict of skill_key → delta (new_value - prev_value), rounded to 1 decimal.
        Only skills affected by this tournament are included.
        Empty dict if the tournament has no valid placement data.

    This is the authoritative source for TournamentParticipation.skill_rating_delta.
    It is written once at reward-distribution time and never recomputed.
    """
    baseline_skills = get_baseline_skills(db, user_id)
    all_baseline_vals = list(baseline_skills.values())
    player_baseline_avg = (
        sum(all_baseline_vals) / len(all_baseline_vals)
        if all_baseline_vals else DEFAULT_BASELINE
    )

    # All participations in chronological order (includes target tournament)
    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    all_skill_keys = get_all_skill_keys()
    skill_previous_values: Dict[str, float] = {
        sk: baseline_skills.get(sk, DEFAULT_BASELINE) for sk in all_skill_keys
    }
    skill_tournament_counts: Dict[str, int] = {sk: 0 for sk in all_skill_keys}

    for participation in participations:
        tournament = participation.tournament
        if not tournament:
            continue

        placement = participation.placement
        if not placement:
            continue

        # Resolve which skills (with weights) this tournament affects
        tournament_skills_with_weights: Dict[str, float] = {}
        reward_config = tournament.reward_config or {}
        skill_mappings = reward_config.get("skill_mappings", [])

        if isinstance(skill_mappings, list) and skill_mappings:
            for mapping in skill_mappings:
                if mapping.get("enabled", False) and mapping.get("skill") in all_skill_keys:
                    tournament_skills_with_weights[mapping["skill"]] = mapping.get("weight", 1.0)
        elif isinstance(skill_mappings, dict) and skill_mappings:
            for sk in skill_mappings:
                if sk in all_skill_keys:
                    tournament_skills_with_weights[sk] = 1.0

        if not tournament_skills_with_weights:
            from app.models.tournament_achievement import TournamentSkillMapping as TSM
            table_mappings = (
                db.query(TSM)
                .filter(TSM.semester_id == tournament.id)
                .all()
            )
            for tm in table_mappings:
                if tm.skill_name in all_skill_keys:
                    tournament_skills_with_weights[tm.skill_name] = (
                        float(tm.weight) if tm.weight else 1.0
                    )

        if not tournament_skills_with_weights:
            continue

        total_players = (
            db.query(TournamentParticipation)
            .filter(TournamentParticipation.semester_id == tournament.id)
            .count()
        )
        if total_players == 0:
            continue

        opp_factor = _compute_opponent_factor(db, tournament.id, user_id, player_baseline_avg)
        match_modifier = _compute_match_performance_modifier(db, tournament.id, user_id)

        is_target = (tournament.id == tournament_id)
        target_delta: Dict[str, float] = {}

        for skill_key, skill_weight in tournament_skills_with_weights.items():
            if skill_key not in skill_previous_values:
                continue

            prev_val = skill_previous_values[skill_key]
            current_count = skill_tournament_counts[skill_key]
            baseline = baseline_skills.get(skill_key, DEFAULT_BASELINE)

            new_value = calculate_skill_value_from_placement(
                baseline=baseline,
                placement=placement,
                total_players=total_players,
                tournament_count=current_count + 1,
                skill_weight=skill_weight,
                prev_value=prev_val,
                opponent_factor=opp_factor,
                match_performance_modifier=match_modifier,
            )

            if is_target:
                delta = round(new_value - prev_val, 1)
                if delta != 0.0:
                    target_delta[skill_key] = delta

            skill_previous_values[skill_key] = new_value
            skill_tournament_counts[skill_key] += 1

        if is_target:
            return target_delta

    return {}


def get_skill_profile(db: Session, user_id: int) -> Dict[str, any]:
    """
    Get complete skill profile for user (for dashboard display).

    Returns:
        {
            "skills": {
                "ball_control": {
                    "baseline": 70.0,
                    "current_level": 85.0,
                    "total_delta": +15.0,
                    "tournament_delta": +15.0,
                    "assessment_delta": 0.0,  # Future: assessments
                    "tournament_count": 3,
                    "assessment_count": 0,
                    "tier": "ADVANCED",
                    "tier_emoji": "🔥"
                },
                ...
            },
            "average_level": 78.5,
            "total_tournaments": 5,
            "total_assessments": 0
        }
    """
    # Get all skill keys
    all_skill_keys = get_all_skill_keys()

    # Calculate tournament contributions for all skills
    skill_data = calculate_tournament_skill_contribution(db, user_id, all_skill_keys)

    # Get total tournament count
    total_tournaments = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .count()
    )

    # Build skill profile
    skill_profile = {}
    total_level = 0.0

    for skill_key in all_skill_keys:
        data = skill_data.get(skill_key, {
            "baseline": DEFAULT_BASELINE,
            "current_value": DEFAULT_BASELINE,
            "contribution": 0.0,
            "tournament_count": 0
        })

        current_level = data["current_value"]
        total_delta = data["contribution"]

        # Determine tier
        tier, tier_emoji = get_skill_tier(current_level)

        skill_profile[skill_key] = {
            "baseline": data["baseline"],
            "current_level": current_level,
            "total_delta": total_delta,
            "tournament_delta": total_delta,  # Currently only tournaments
            "assessment_delta": 0.0,  # Future: assessments
            "tournament_count": data["tournament_count"],
            "assessment_count": 0,
            "tier": tier,
            "tier_emoji": tier_emoji
        }

        total_level += current_level

    average_level = total_level / len(all_skill_keys) if all_skill_keys else 0.0

    return {
        "skills": skill_profile,
        "average_level": round(average_level, 1),
        "total_tournaments": total_tournaments,
        "total_assessments": 0  # Future: assessments
    }


def get_skill_timeline(
    db: Session,
    user_id: int,
    skill_key: str
) -> Dict:
    """
    Build a per-tournament timeline for a single skill showing how it evolved
    across all tournaments the player participated in.

    The timeline replays the same sequential weighted-average formula used by
    calculate_tournament_skill_contribution(), but captures the intermediate
    value after every tournament instead of only the final aggregated result.

    No schema changes required: all data lives in TournamentParticipation +
    TournamentSkillMapping / reward_config.

    Returns:
        {
            "skill": "passing",
            "baseline": 80.0,
            "current_level": 97.5,
            "total_delta": 17.5,
            "timeline": [
                {
                    "tournament_id":   10,
                    "tournament_name": "League Cup 2026",
                    "achieved_at":     "2026-02-11T15:33:11+00:00",
                    "placement":       1,
                    "total_players":   4,
                    "placement_skill": 100.0,
                    "skill_weight":    1.0,
                    "skill_value_after": 88.5,
                    "delta_from_baseline": 8.5,
                    "delta_from_previous": 8.5,
                },
                ...
            ]
        }
        Returns None if the player has no participation data or the skill is unknown.
    """
    all_skill_keys = get_all_skill_keys()
    if skill_key not in all_skill_keys:
        return None

    # --- baseline --------------------------------------------------------
    baseline_skills = get_baseline_skills(db, user_id)
    baseline = baseline_skills.get(skill_key, DEFAULT_BASELINE)

    # Player average baseline for opponent_factor computation
    all_baseline_vals = list(baseline_skills.values())
    player_baseline_avg = (sum(all_baseline_vals) / len(all_baseline_vals)) if all_baseline_vals else DEFAULT_BASELINE

    # --- participations in chronological order ---------------------------
    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    timeline = []
    tournament_count = 0      # How many tournaments have already affected this skill
    previous_value = baseline

    for participation in participations:
        tournament = participation.tournament
        if not tournament or not participation.placement:
            continue

        # Resolve skill weights (same priority as calculate_tournament_skill_contribution)
        tournament_skills_with_weights: Dict[str, float] = {}

        reward_config = tournament.reward_config or {}
        skill_mappings = reward_config.get("skill_mappings", [])

        if isinstance(skill_mappings, list) and skill_mappings:
            for mapping in skill_mappings:
                if mapping.get("enabled", False) and mapping.get("skill") in all_skill_keys:
                    tournament_skills_with_weights[mapping["skill"]] = mapping.get("weight", 1.0)
        elif isinstance(skill_mappings, dict) and skill_mappings:
            for sk in skill_mappings:
                if sk in all_skill_keys:
                    tournament_skills_with_weights[sk] = 1.0

        if not tournament_skills_with_weights:
            from app.models.tournament_achievement import TournamentSkillMapping as TSM
            table_mappings = (
                db.query(TSM)
                .filter(TSM.semester_id == tournament.id)
                .all()
            )
            for tm in table_mappings:
                if tm.skill_name in all_skill_keys:
                    tournament_skills_with_weights[tm.skill_name] = (
                        float(tm.weight) if tm.weight else 1.0
                    )

        # This tournament does not affect the requested skill → skip
        if skill_key not in tournament_skills_with_weights:
            continue

        skill_weight = tournament_skills_with_weights[skill_key]

        # Total players in this tournament
        total_players = (
            db.query(TournamentParticipation)
            .filter(TournamentParticipation.semester_id == tournament.id)
            .count()
        )
        if total_players == 0:
            continue

        # Placement → placement_skill (100 for 1st, 40 for last)
        if total_players == 1:
            percentile = 0.0
        else:
            percentile = (participation.placement - 1) / (total_players - 1)
        placement_skill = MAX_SKILL_VALUE - (percentile * (MAX_SKILL_VALUE - MIN_SKILL_VALUE))

        opp_factor = _compute_opponent_factor(
            db, tournament.id, user_id, player_baseline_avg
        )

        tournament_count += 1
        skill_value_after = calculate_skill_value_from_placement(
            baseline=baseline,
            placement=participation.placement,
            total_players=total_players,
            tournament_count=tournament_count,
            skill_weight=skill_weight,
            prev_value=previous_value,
            opponent_factor=opp_factor,
        )

        timeline.append({
            "tournament_id":        tournament.id,
            "tournament_name":      tournament.name,
            "achieved_at":          participation.achieved_at.isoformat() if participation.achieved_at else None,
            "placement":            participation.placement,
            "total_players":        total_players,
            "placement_skill":      round(placement_skill, 1),
            "skill_weight":         skill_weight,
            "skill_value_after":    skill_value_after,
            "delta_from_baseline":  round(skill_value_after - baseline, 1),
            "delta_from_previous":  round(skill_value_after - previous_value, 1),
        })
        previous_value = skill_value_after

    if not timeline:
        return {
            "skill": skill_key,
            "baseline": baseline,
            "current_level": baseline,
            "total_delta": 0.0,
            "timeline": []
        }

    current_level = timeline[-1]["skill_value_after"]
    return {
        "skill":         skill_key,
        "baseline":      baseline,
        "current_level": current_level,
        "total_delta":   round(current_level - baseline, 1),
        "timeline":      timeline,
    }


def get_skill_audit(db: Session, user_id: int) -> List[Dict]:
    """
    Build a per-tournament audit log showing which skills were expected to change
    and whether they actually changed.

    For each tournament the player participated in, returns one row per mapped skill:
        {
          "tournament_id":   17,
          "tournament_name": "E2E Phase 4d",
          "achieved_at":     "2026-02-11T...",
          "placement":       1,
          "total_players":   4,
          "skill":           "finishing",
          "skill_weight":    1.50,
          "avg_weight":      1.00,        # average weight of all skills in this tournament
          "is_dominant":     True,        # weight > avg_weight
          "expected_change": True,        # skill was in the tournament's skill_mappings
          "placement_skill": 100.0,       # raw score from placement (100=1st, 40=last)
          "delta_this_tournament": +2.0,  # actual change produced by THIS tournament
                                          # (cumulative formula, so derived from timeline)
          "actual_changed":  True,        # abs(delta_this_tournament) > 0.0
          "fairness_ok":     True,        # dominant skill had |delta| >= balanced peers
        }

    Sorted: tournament chronological ASC, then skill name ASC within each tournament.
    """
    all_skill_keys = get_all_skill_keys()
    baseline_skills = get_baseline_skills(db, user_id)

    # Player average baseline for opponent_factor computation
    all_baseline_vals = list(baseline_skills.values())
    player_baseline_avg = (sum(all_baseline_vals) / len(all_baseline_vals)) if all_baseline_vals else DEFAULT_BASELINE

    participations = (
        db.query(TournamentParticipation)
        .filter(TournamentParticipation.user_id == user_id)
        .order_by(TournamentParticipation.achieved_at.asc())
        .all()
    )

    # We need to replay the sequential formula per skill (same as get_skill_timeline),
    # tracking previous_value per skill to compute delta_this_tournament.
    skill_tournament_counts: Dict[str, int] = {}    # cumulative count per skill
    skill_previous_values: Dict[str, float] = {}    # last computed value per skill

    for sk in all_skill_keys:
        skill_tournament_counts[sk] = 0
        skill_previous_values[sk] = baseline_skills.get(sk, DEFAULT_BASELINE)

    audit_rows: List[Dict] = []

    for participation in participations:
        tournament = participation.tournament
        if not tournament or not participation.placement:
            continue

        # Resolve skill weights for this tournament (same priority logic)
        tournament_skills_with_weights: Dict[str, float] = {}
        reward_config = tournament.reward_config or {}
        skill_mappings = reward_config.get("skill_mappings", [])

        if isinstance(skill_mappings, list) and skill_mappings:
            for mapping in skill_mappings:
                if mapping.get("enabled", False) and mapping.get("skill") in all_skill_keys:
                    tournament_skills_with_weights[mapping["skill"]] = mapping.get("weight", 1.0)
        elif isinstance(skill_mappings, dict) and skill_mappings:
            for sk in skill_mappings:
                if sk in all_skill_keys:
                    tournament_skills_with_weights[sk] = 1.0

        if not tournament_skills_with_weights:
            from app.models.tournament_achievement import TournamentSkillMapping as TSM
            table_mappings = (
                db.query(TSM)
                .filter(TSM.semester_id == tournament.id)
                .all()
            )
            for tm in table_mappings:
                if tm.skill_name in all_skill_keys:
                    tournament_skills_with_weights[tm.skill_name] = (
                        float(tm.weight) if tm.weight else 1.0
                    )

        if not tournament_skills_with_weights:
            continue

        # Stats for this tournament
        total_players = (
            db.query(TournamentParticipation)
            .filter(TournamentParticipation.semester_id == tournament.id)
            .count()
        )
        if total_players == 0:
            continue

        # Placement → placement_skill
        if total_players == 1:
            percentile = 0.0
        else:
            percentile = (participation.placement - 1) / (total_players - 1)
        placement_skill = round(
            MAX_SKILL_VALUE - (percentile * (MAX_SKILL_VALUE - MIN_SKILL_VALUE)), 1
        )

        achieved_at_str = (
            participation.achieved_at.isoformat() if participation.achieved_at else None
        )

        # Compute avg weight for this tournament (to flag dominant skills)
        avg_weight = (
            sum(tournament_skills_with_weights.values()) / len(tournament_skills_with_weights)
        )

        # Opponent factor for this tournament (ELO-inspired)
        opp_factor = _compute_opponent_factor(
            db, tournament.id, user_id, player_baseline_avg
        )

        # Calculate delta and normalised delta for each mapped skill.
        #
        # Normalised delta = delta / headroom
        #   where headroom = max_cap - prev_val  (when improving)
        #                  = prev_val - min_floor (when declining)
        #
        # This is the correct fairness metric: it measures what fraction of the
        # available development range was consumed, independent of the skill's
        # absolute position.  A skill capped at 99 has headroom=0 → norm_delta=0,
        # which is a physical limit, NOT an unfairness signal.
        skill_deltas: Dict[str, float] = {}
        skill_norm_deltas: Dict[str, float] = {}

        for skill_key, skill_weight in tournament_skills_with_weights.items():
            prev = skill_previous_values[skill_key]
            count = skill_tournament_counts[skill_key] + 1
            new_val = calculate_skill_value_from_placement(
                baseline=baseline_skills.get(skill_key, DEFAULT_BASELINE),
                placement=participation.placement,
                total_players=total_players,
                tournament_count=count,
                skill_weight=skill_weight,
                prev_value=prev,
                opponent_factor=opp_factor,
            )
            delta = round(new_val - prev, 2)
            skill_deltas[skill_key] = delta

            # Normalised delta: fraction of available headroom consumed
            if delta > 0:
                headroom = max(0.001, MAX_SKILL_CAP - prev)
            elif delta < 0:
                headroom = max(0.001, prev - MIN_SKILL_VALUE)
            else:
                headroom = 0.0   # no movement at all
            skill_norm_deltas[skill_key] = (
                round(delta / headroom, 6) if headroom > 0 else 0.0
            )

        # Fairness check (normalised):
        #   A dominant skill (weight > avg * 1.05) should have
        #   |norm_delta| >= |norm_delta| of every lower-weight peer.
        #
        #   Exception: if the dominant skill is at the hard cap (headroom=0),
        #   its norm_delta is 0 by definition — that is a physical limit,
        #   NOT an unfair outcome.  We skip the check in that case.
        for skill_key, skill_weight in tournament_skills_with_weights.items():
            delta = skill_deltas.get(skill_key, 0.0)
            my_norm = abs(skill_norm_deltas.get(skill_key, 0.0))
            is_dominant = skill_weight > avg_weight * 1.05

            fairness_ok = True
            if is_dominant and skill_norm_deltas.get(skill_key, 0.0) != 0.0:
                # Only check when dominant skill actually had room to move
                for peer_key, peer_weight in tournament_skills_with_weights.items():
                    if peer_key == skill_key:
                        continue
                    if peer_weight < skill_weight:
                        peer_norm = abs(skill_norm_deltas.get(peer_key, 0.0))
                        # Flag if peer consumed more headroom than dominant skill
                        # (0.005 tolerance for floating-point imprecision)
                        if my_norm + 0.005 < peer_norm:
                            fairness_ok = False

            audit_rows.append({
                "tournament_id":          tournament.id,
                "tournament_name":        tournament.name,
                "achieved_at":            achieved_at_str,
                "placement":              participation.placement,
                "total_players":          total_players,
                "skill":                  skill_key,
                "skill_weight":           round(skill_weight, 2),
                "avg_weight":             round(avg_weight, 2),
                "is_dominant":            is_dominant,
                "expected_change":        True,   # by definition: it's in the mapping
                "placement_skill":        placement_skill,
                "delta_this_tournament":  delta,
                "norm_delta":             skill_norm_deltas.get(skill_key, 0.0),
                "actual_changed":         abs(delta) > 0.001,
                "fairness_ok":            fairness_ok,
                "opponent_factor":        opp_factor,
                "ema_path":               skill_tournament_counts.get(skill_key, 0) > 0,
            })

        # Advance running state
        for skill_key, skill_weight in tournament_skills_with_weights.items():
            skill_tournament_counts[skill_key] += 1
            prev = skill_previous_values[skill_key]
            count = skill_tournament_counts[skill_key]
            new_val = calculate_skill_value_from_placement(
                baseline=baseline_skills.get(skill_key, DEFAULT_BASELINE),
                placement=participation.placement,
                total_players=total_players,
                tournament_count=count,
                skill_weight=skill_weight,
                prev_value=prev,
                opponent_factor=opp_factor,
            )
            skill_previous_values[skill_key] = new_val

    return audit_rows


def get_skill_tier(level: float) -> tuple[str, str]:
    """
    Get skill tier name and emoji based on level.

    Args:
        level: Skill level (0-100)

    Returns:
        (tier_name, tier_emoji)
    """
    if level >= 95:
        return ("MASTER", "💎")
    elif level >= 85:
        return ("ADVANCED", "🔥")
    elif level >= 70:
        return ("INTERMEDIATE", "⚡")
    elif level >= 50:
        return ("DEVELOPING", "📈")
    else:
        return ("BEGINNER", "🌱")
