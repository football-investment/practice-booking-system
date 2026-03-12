"""
Tournament Leaderboard Renderer

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Displays tournament rankings with rewards (XP, credits, skill points, rating delta).
"""

from typing import Any, Dict, List
import streamlit as st

# Constants
_TOP_N_LEADERBOARD = 10


def render_leaderboard(
    rankings: List[Dict[str, Any]],
    status: str = "",
    has_knockout: bool = False,
    scoring_type: str = "",
    is_individual_ranking: bool = False,
) -> None:
    """
    Render tournament leaderboard with rewards.

    Args:
        rankings:              List of ranking entries (user_id, name, rank, points, wins, etc.)
        status:                Tournament status ("IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED")
        has_knockout:          Whether tournament has knockout phase (affects display)
        scoring_type:          Scoring type string (e.g. "TIME_BASED") — used for unit labels.
        is_individual_ranking: Explicit flag: True for INDIVIDUAL_RANKING tournaments.
                               Controls whether measured_value is shown instead of W/D/L stats.
    """
    if not rankings:
        st.caption("Leaderboard not yet available.")
        return

    rewards_distributed = status == "REWARDS_DISTRIBUTED"
    is_ir = is_individual_ranking

    # Unit label for Individual Ranking measured_value display
    if "TIME" in scoring_type or scoring_type == "ROUNDS_BASED":
        _mv_unit = "s"
        _agg_label = "best"   # TIME_BASED / ROUNDS_BASED ranks by lowest (best) time
    elif "DISTANCE" in scoring_type:
        _mv_unit = "m"
        _agg_label = "best"
    else:
        _mv_unit = "pts"
        _agg_label = "best"

    top = rankings[:_TOP_N_LEADERBOARD]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for entry in top:
        # Fix: rank can be None for unranked IR entries
        rank = entry.get("rank")
        rank_display = rank if rank is not None else "?"
        medal = medals.get(rank_display, f"#{rank_display}")

        name = entry.get("name") or entry.get("player_name") or f"Player {entry.get('user_id', '?')}"

        # Round-by-round results (present only for ROUNDS_BASED sessions)
        _rr_raw: dict = entry.get("round_results") or {}
        total_rounds = int(_rr_raw.get("total_rounds", 0))
        # Round entries are numeric-keyed; exclude the metadata key
        rr = {k: v for k, v in _rr_raw.items() if k != "total_rounds"}
        has_rounds = bool(rr) and total_rounds > 1

        # W/D/L stats — only meaningful for H2H tournaments
        w = entry.get("wins", 0) or 0
        d = entry.get("draws", 0) or 0
        l = entry.get("losses", 0) or 0
        pts = entry.get("points", 0) or 0
        gf = entry.get("goals_for", 0) or 0
        ga = entry.get("goals_against", 0) or 0
        has_h2h_stats = bool(w or d or l) and not is_ir  # wins/draws/losses only make sense for H2H

        if rewards_distributed:
            xp = entry.get("xp_earned") or entry.get("xp_reward") or ""
            cr = entry.get("credits_earned") or entry.get("credits_reward") or ""
            reward_str = ""
            if xp:
                reward_str += f" +{xp} XP"
            if cr:
                reward_str += f" +{cr} cr"

            if is_ir:
                # Individual Ranking: show measured_value instead of W/D/L
                mv = entry.get("measured_value")
                if mv is not None and has_rounds:
                    # Multi-round: show aggregate label so it's clear
                    stats_str = f"  *({_agg_label}: {mv} {_mv_unit})*"
                elif mv is not None:
                    stats_str = f"  *({mv} {_mv_unit})*"
                else:
                    stats_str = ""
            else:
                stats_str = f"  *({w}W {d}D {l}L · {gf}:{ga})*" if has_h2h_stats else ""

            st.markdown(f"{medal} **{name}**{reward_str}{stats_str}")

            # Round-by-round breakdown for multi-round IR
            if has_rounds:
                sorted_rounds = sorted(rr.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
                round_parts = [f"R{rn}: {val} {_mv_unit}" for rn, val in sorted_rounds]
                st.caption(f"  🔁 Rounds: {' · '.join(round_parts)}")

            # Skill deltas (from game preset)
            skills: dict = entry.get("skills_awarded") or {}
            if skills:
                skill_parts = [f"+{v:.1f} {k.replace('_', ' ')}" for k, v in skills.items() if v]
                if skill_parts:
                    st.caption(f"  ↑ Skills: {' · '.join(skill_parts)}")

            # Rating delta (V3 EMA — actual skill level change, can be negative)
            rating_delta: dict = entry.get("skill_rating_delta") or {}
            if rating_delta:
                rd_parts = []
                for k, v in rating_delta.items():
                    sign = "+" if v > 0 else ""
                    rd_parts.append(f"{sign}{v:.1f} {k.replace('_', ' ')}")
                st.caption(f"  📊 Rating Δ: {' · '.join(rd_parts)}")

        elif is_ir:
            # IN_PROGRESS / COMPLETED Individual Ranking: show measured_value
            mv = entry.get("measured_value")
            if mv is not None and has_rounds:
                st.markdown(f"{medal} **{name}** — {_agg_label}: {mv} {_mv_unit}")
                sorted_rounds = sorted(rr.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
                round_parts = [f"R{rn}: {val} {_mv_unit}" for rn, val in sorted_rounds]
                st.caption(f"  🔁 Rounds: {' · '.join(round_parts)}")
            elif mv is not None:
                st.markdown(f"{medal} **{name}** — {mv} {_mv_unit}")
            else:
                st.markdown(f"{medal} **{name}**")

        elif has_h2h_stats:
            # H2H IN_PROGRESS or COMPLETED: show full stats
            gd = gf - ga
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            st.markdown(f"{medal} **{name}** — {pts} pts · {w}W {d}D {l}L · {gf}:{ga} (GD {gd_str})")
        else:
            # Knockout-only rank: no point totals available
            st.markdown(f"{medal} **{name}**")
