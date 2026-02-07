"""
HEAD_TO_HEAD League (Round Robin) Ranking Strategy

Calculates rankings for league tournaments based on:
1. Total points (Win = 3, Tie = 1, Loss = 0)
2. Head-to-head record (if tied on points)
3. Goal difference (if still tied)
4. Goals scored (if still tied)
"""
from typing import Dict, List, Tuple
from collections import defaultdict
import json


class HeadToHeadLeagueRankingStrategy:
    """
    Ranking strategy for HEAD_TO_HEAD League (Round Robin) tournaments

    Point system:
    - Win: 3 points
    - Tie: 1 point
    - Loss: 0 points

    Tiebreakers:
    1. Head-to-head record between tied participants
    2. Goal difference (goals scored - goals conceded)
    3. Total goals scored
    """

    def calculate_rankings(
        self,
        sessions: List,
        db_session
    ) -> List[Dict]:
        """
        Calculate league rankings from all match results

        Args:
            sessions: List of Session objects with game_results populated
            db_session: SQLAlchemy database session

        Returns:
            List of ranking dicts:
            [
                {
                    "user_id": 4,
                    "rank": 1,
                    "points": 9,
                    "wins": 3,
                    "ties": 0,
                    "losses": 0,
                    "goals_scored": 12,
                    "goals_conceded": 3,
                    "goal_difference": 9
                },
                ...
            ]
        """
        # Aggregate match results per participant
        participant_stats = defaultdict(lambda: {
            "points": 0,
            "wins": 0,
            "ties": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "matches": []  # Track individual match results for head-to-head tiebreaker
        })

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
            score_1 = p1["score"]
            score_2 = p2["score"]
            result_1 = p1["result"]  # "win", "tie", "loss"
            result_2 = p2["result"]

            # Update participant 1 stats
            participant_stats[user_id_1]["goals_scored"] += score_1
            participant_stats[user_id_1]["goals_conceded"] += score_2
            participant_stats[user_id_1]["matches"].append({
                "opponent_id": user_id_2,
                "goals_for": score_1,
                "goals_against": score_2,
                "result": result_1
            })

            if result_1 == "win":
                participant_stats[user_id_1]["points"] += 3
                participant_stats[user_id_1]["wins"] += 1
            elif result_1 == "tie":
                participant_stats[user_id_1]["points"] += 1
                participant_stats[user_id_1]["ties"] += 1
            else:  # loss
                participant_stats[user_id_1]["losses"] += 1

            # Update participant 2 stats
            participant_stats[user_id_2]["goals_scored"] += score_2
            participant_stats[user_id_2]["goals_conceded"] += score_1
            participant_stats[user_id_2]["matches"].append({
                "opponent_id": user_id_1,
                "goals_for": score_2,
                "goals_against": score_1,
                "result": result_2
            })

            if result_2 == "win":
                participant_stats[user_id_2]["points"] += 3
                participant_stats[user_id_2]["wins"] += 1
            elif result_2 == "tie":
                participant_stats[user_id_2]["points"] += 1
                participant_stats[user_id_2]["ties"] += 1
            else:  # loss
                participant_stats[user_id_2]["losses"] += 1

        # Convert to list and add goal difference
        participants_list = []
        for user_id, stats in participant_stats.items():
            stats["user_id"] = user_id
            stats["goal_difference"] = stats["goals_scored"] - stats["goals_conceded"]
            participants_list.append(stats)

        # Sort by points (DESC), then goal difference (DESC), then goals scored (DESC)
        participants_list.sort(
            key=lambda x: (
                -x["points"],  # Higher points = better
                -x["goal_difference"],  # Higher goal difference = better
                -x["goals_scored"]  # Higher goals scored = better (tiebreaker)
            )
        )

        # Assign ranks (handle ties)
        rankings = []
        current_rank = 1
        for idx, participant in enumerate(participants_list):
            # Check if tied with previous participant
            if idx > 0:
                prev = participants_list[idx - 1]
                if (
                    participant["points"] == prev["points"] and
                    participant["goal_difference"] == prev["goal_difference"] and
                    participant["goals_scored"] == prev["goals_scored"]
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
                "points": participant["points"],
                "wins": participant["wins"],
                "ties": participant["ties"],
                "losses": participant["losses"],
                "goals_scored": participant["goals_scored"],
                "goals_conceded": participant["goals_conceded"],
                "goal_difference": participant["goal_difference"]
            })

            current_rank += 1

        return rankings
