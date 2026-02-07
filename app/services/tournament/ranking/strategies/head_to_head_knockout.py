"""
HEAD_TO_HEAD Knockout (Single Elimination) Ranking Strategy

Calculates rankings for knockout tournaments based on:
1. Round reached (Final winner > Runner-up > Semifinal losers > Quarterfinal losers)
2. Score in final match (for tied ranks like semifinal losers)
"""
from typing import Dict, List
from collections import defaultdict
import json


class HeadToHeadKnockoutRankingStrategy:
    """
    Ranking strategy for HEAD_TO_HEAD Knockout (Single Elimination) tournaments

    Ranking logic:
    - Round 3 (Final) winner: Rank 1
    - Round 3 (Final) loser: Rank 2
    - Round 2 (Semifinal) losers: Rank 3 (tied)
    - Round 1 (Quarterfinal) losers: Rank 5 (tied)
    - And so on...

    For tied ranks, secondary sort by score in their elimination match.
    """

    def calculate_rankings(
        self,
        sessions: List,
        db_session
    ) -> List[Dict]:
        """
        Calculate knockout rankings from bracket results

        Args:
            sessions: List of Session objects with game_results populated
            db_session: SQLAlchemy database session

        Returns:
            List of ranking dicts:
            [
                {
                    "user_id": 4,
                    "rank": 1,
                    "round_reached": 3,  # Final
                    "result": "winner",
                    "elimination_score": None  # Not eliminated
                },
                {
                    "user_id": 5,
                    "rank": 2,
                    "round_reached": 3,  # Final
                    "result": "runner_up",
                    "elimination_score": 2  # Score when eliminated
                },
                ...
            ]
        """
        # Track each participant's progress
        participant_progress = {}

        # Parse all match results
        for session in sessions:
            if not session.game_results:
                continue

            try:
                match_data = json.loads(session.game_results)
            except (json.JSONDecodeError, TypeError):
                continue

            if match_data.get("match_format") != "HEAD_TO_HEAD":
                continue

            participants = match_data.get("participants", [])
            if len(participants) != 2:
                continue

            # Extract match result
            p1 = participants[0]
            p2 = participants[1]

            user_id_1 = p1["user_id"]
            user_id_2 = p2["user_id"]
            result_1 = p1["result"]  # "win", "loss"
            result_2 = p2["result"]
            score_1 = p1["score"]
            score_2 = p2["score"]

            # Determine round number (from game_results or infer from session metadata)
            round_number = match_data.get("round_number")
            if round_number is None:
                # Fallback: Try to infer from session metadata or assume Round 1
                round_number = 1

            # Update participant 1
            if user_id_1 not in participant_progress:
                participant_progress[user_id_1] = {
                    "user_id": user_id_1,
                    "round_reached": round_number,
                    "result": result_1,
                    "elimination_score": score_1 if result_1 == "loss" else None,
                    "elimination_round": round_number if result_1 == "loss" else None
                }
            else:
                # Update if progressed further
                if round_number > participant_progress[user_id_1]["round_reached"]:
                    participant_progress[user_id_1]["round_reached"] = round_number
                    participant_progress[user_id_1]["result"] = result_1
                    if result_1 == "loss":
                        participant_progress[user_id_1]["elimination_score"] = score_1
                        participant_progress[user_id_1]["elimination_round"] = round_number

            # Update participant 2
            if user_id_2 not in participant_progress:
                participant_progress[user_id_2] = {
                    "user_id": user_id_2,
                    "round_reached": round_number,
                    "result": result_2,
                    "elimination_score": score_2 if result_2 == "loss" else None,
                    "elimination_round": round_number if result_2 == "loss" else None
                }
            else:
                # Update if progressed further
                if round_number > participant_progress[user_id_2]["round_reached"]:
                    participant_progress[user_id_2]["round_reached"] = round_number
                    participant_progress[user_id_2]["result"] = result_2
                    if result_2 == "loss":
                        participant_progress[user_id_2]["elimination_score"] = score_2
                        participant_progress[user_id_2]["elimination_round"] = round_number

        # Convert to list
        participants_list = list(participant_progress.values())

        # Sort by:
        # 1. Round reached (DESC - higher round = better)
        # 2. Result (winner > runner_up > loss)
        # 3. Elimination score (DESC - higher score when eliminated = better)
        def sort_key(p):
            result_priority = {
                "win": 0,  # Best
                "runner_up": 1,
                "loss": 2
            }
            return (
                -p["round_reached"],  # Higher round = better
                result_priority.get(p["result"], 3),  # Winner > Runner-up > Loss
                -(p["elimination_score"] or 0)  # Higher score when eliminated = better
            )

        participants_list.sort(key=sort_key)

        # Assign ranks
        rankings = []
        current_rank = 1
        for idx, participant in enumerate(participants_list):
            # Check if tied with previous participant
            if idx > 0:
                prev = participants_list[idx - 1]
                if (
                    participant["round_reached"] == prev["round_reached"] and
                    participant["result"] == prev["result"] and
                    participant["elimination_score"] == prev["elimination_score"]
                ):
                    # Tied - same rank as previous
                    rank = rankings[-1]["rank"]
                else:
                    rank = current_rank
            else:
                rank = current_rank

            rankings.append({
                "user_id": participant["user_id"],
                "rank": rank,
                "round_reached": participant["round_reached"],
                "result": participant["result"],
                "elimination_score": participant["elimination_score"]
            })

            current_rank += 1

        return rankings
