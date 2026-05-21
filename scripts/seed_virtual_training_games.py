"""Seed Virtual Training game presets (Phase 1 — all inactive).

Safe to run multiple times: uses ON CONFLICT DO NOTHING on the unique code column.
All presets are seeded with is_active=False. A future admin toggle activates them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.virtual_training import VirtualTrainingGame

_GAMES = [
    {
        "code": "color_reaction",
        "name": "Color Reaction",
        "description": (
            "A colour-stimulus reaction-time trainer. A coloured circle "
            "appears at a random position; tap/click as fast as possible. "
            "Trains raw reaction speed and visual attention."
        ),
        "game_type": "reaction_time",
        "is_active": False,
        "base_xp": 15,
        "max_daily_attempts": 5,
        "skill_targets": {
            "reactions": 0.55,
            "concentration": 0.25,
            "anticipation": 0.20,
        },
        "config": {
            "stimulus_count": 10,
            "min_delay_ms": 600,
            "max_delay_ms": 2500,
            "colours": ["#e74c3c", "#2ecc71", "#3498db", "#f39c12"],
        },
    },
    {
        "code": "stroop_challenge",
        "name": "Stroop Challenge",
        "description": (
            "A cognitive inhibition task based on the Stroop effect. "
            "A colour word is displayed in an incongruent ink colour; "
            "respond to the ink colour, not the word. "
            "Trains decision-making under interference and concentration."
        ),
        "game_type": "cognitive_inhibition",
        "is_active": False,
        "base_xp": 12,
        "max_daily_attempts": 5,
        "skill_targets": {
            "decisions": 0.50,
            "concentration": 0.30,
            "composure": 0.20,
        },
        "config": {
            "trial_count": 12,
            "response_window_ms": 3000,
            "words": ["RED", "GREEN", "BLUE", "YELLOW"],
            "colours": ["#e74c3c", "#2ecc71", "#3498db", "#f1c40f"],
        },
    },
    {
        "code": "go_no_go",
        "name": "Go / No-Go",
        "description": (
            "An impulse control task. Respond quickly to a target stimulus "
            "(Go) but withhold the response to a distractor (No-Go). "
            "Trains composure, concentration and quick decision-making."
        ),
        "game_type": "go_no_go",
        "is_active": False,
        "base_xp": 12,
        "max_daily_attempts": 5,
        "skill_targets": {
            "composure": 0.40,
            "concentration": 0.35,
            "decisions": 0.25,
        },
        "config": {
            "trial_count": 20,
            "go_ratio": 0.75,
            "stimulus_duration_ms": 800,
            "inter_trial_ms": 1000,
        },
    },
]


def seed_virtual_training_games() -> None:
    db = SessionLocal()
    try:
        inserted = 0
        for data in _GAMES:
            existing = (
                db.query(VirtualTrainingGame)
                .filter(VirtualTrainingGame.code == data["code"])
                .first()
            )
            if existing:
                print(f"  skip  {data['code']} (already exists, id={existing.id})")
                continue
            game = VirtualTrainingGame(**data)
            db.add(game)
            inserted += 1
            print(f"  +     {data['code']} (is_active={data['is_active']})")

        db.commit()
        print(f"\nDone. {inserted} game(s) inserted, {len(_GAMES) - inserted} skipped.")
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_virtual_training_games()
