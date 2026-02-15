"""
Tournament Leaderboard Renderer

Extracted from tournament_monitor.py as part of Iteration 3 refactoring.
Displays tournament rankings with rewards (XP, credits, skill points, rating delta).
"""

from typing import Any, Dict, List
import streamlit as st

# Constants
_TOP_N_LEADERBOARD = 10


def render_leaderboard(rankings: List[Dict[str, Any]], status: str = "", has_knockout: bool = False) -> None:
    """
    Render tournament leaderboard with rewards.

    Args:
        rankings: List of ranking entries (user_id, name, rank, points, wins, etc.)
        status: Tournament status ("IN_PROGRESS", "COMPLETED", "REWARDS_DISTRIBUTED")
        has_knockout: Whether tournament has knockout phase (affects display)

    Displays:
        - Top N players with medals (🥇🥈🥉) or rank numbers
        - W/D/L stats and points (if available)
        - XP and credits rewards (if REWARDS_DISTRIBUTED)
        - Skill points awarded (↑ Skills:) from game preset
        - Rating delta (📊 Rating Δ:) from V3 EMA skill progression
    """
    if not rankings:
        st.caption("Leaderboard not yet available.")
        return

    is_ongoing = status not in ("COMPLETED", "REWARDS_DISTRIBUTED")
    rewards_distributed = status == "REWARDS_DISTRIBUTED"

    top = rankings[:_TOP_N_LEADERBOARD]
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for entry in top:
        rank = entry.get("rank", "?")
        name = entry.get("name") or entry.get("player_name") or f"Player {entry.get('user_id', '?')}"
        medal = medals.get(rank, f"#{rank}")

        # Build stats suffix (W/D/L + pts) when available
        w = entry.get("wins", 0) or 0
        d = entry.get("draws", 0) or 0
        l = entry.get("losses", 0) or 0
        pts = entry.get("points", 0) or 0
        gf = entry.get("goals_for", 0) or 0
        ga = entry.get("goals_against", 0) or 0
        has_stats = w or d or l or pts

        if rewards_distributed:
            xp = entry.get("xp_earned") or entry.get("xp_reward") or ""
            cr = entry.get("credits_earned") or entry.get("credits_reward") or ""
            reward_str = ""
            if xp:
                reward_str += f" +{xp} XP"
            if cr:
                reward_str += f" +{cr} cr"
            stats_str = f"  *({w}W {d}D {l}L · {gf}:{ga})*" if has_stats else ""
            st.markdown(f"{medal} **{name}**{reward_str}{stats_str}")

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
        elif has_stats:
            # Always show W/D/L/pts when the data is there (IN_PROGRESS or COMPLETED)
            gd = gf - ga
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            st.markdown(f"{medal} **{name}** — {pts} pts · {w}W {d}D {l}L · {gf}:{ga} (GD {gd_str})")
        else:
            # Knockout-only rank: no point totals available
            st.markdown(f"{medal} **{name}**")
