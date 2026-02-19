-- Reseed production game presets from config/game_presets/*.json
-- Upserts by code — safe to run multiple times.
--
-- Run with:
--   psql -U postgres -d lfa_intern_system -f scripts/maintenance/reseed_game_presets.sql

-- ─── 1. GānFootvolley ────────────────────────────────────────────────────────
INSERT INTO game_presets (code, name, description, game_config, is_active, is_recommended, is_locked)
VALUES (
    'gan_footvolley',
    'GānFootvolley',
    'Advanced footvolley game testing multiple technical skills',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "general",
            "difficulty_level": "advanced",
            "recommended_player_count": {"min": 4, "max": 16}
        },
        "skill_config": {
            "skills_tested": [
                "ball_control","volleys","heading","positioning_off","positioning_def",
                "vision","reactions","composure","consistency","tactical_awareness",
                "acceleration","agility","stamina","balance"
            ],
            "skill_weights": {
                "ball_control": 0.5424764832912413,
                "volleys": 0.03660188133670072,
                "heading": 0.03660188133670072,
                "positioning_off": 0.03660188133670072,
                "positioning_def": 0.03660188133670072,
                "vision": 0.03660188133670072,
                "reactions": 0.03660188133670072,
                "composure": 0.03660188133670072,
                "consistency": 0.03660188133670072,
                "tactical_awareness": 0.03660188133670072,
                "acceleration": 0.03660188133670072,
                "agility": 0.03294169320303065,
                "stamina": 0.02196112880202043,
                "balance": 0.03660188133670072
            },
            "skill_impact_on_matches": true
        },
        "format_config": {
            "HEAD_TO_HEAD": {
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                },
                "match_simulation": {
                    "score_ranges": {
                        "win": {"loser_max": 2, "winner_max": 5},
                        "draw": {"max": 2, "min": 0}
                    },
                    "draw_probability": 0.15,
                    "away_win_probability": 0.4,
                    "home_win_probability": 0.45
                }
            }
        },
        "simulation_config": {
            "player_selection": {"mode": "skill_based", "use_ranking_weights": true},
            "ranking_distribution": {"mean": 0.5, "type": "normal", "std_dev": 0.2}
        }
    }'::jsonb,
    true, true, false
)
ON CONFLICT (code) DO UPDATE SET
    name        = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config,
    is_active   = EXCLUDED.is_active,
    is_recommended = EXCLUDED.is_recommended,
    updated_at  = NOW();


-- ─── 2. GanFoottennis ────────────────────────────────────────────────────────
INSERT INTO game_presets (code, name, description, game_config, is_active, is_recommended, is_locked)
VALUES (
    'gan_foottennis',
    'GanFoottennis',
    'Racquet sports style game testing ball control, agility and reactions',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "racquet_sports",
            "difficulty_level": "advanced",
            "recommended_player_count": {"min": 4, "max": 12}
        },
        "skill_config": {
            "skills_tested": ["ball_control", "agility", "reactions"],
            "skill_weights": {
                "ball_control": 0.40,
                "agility": 0.30,
                "reactions": 0.30
            },
            "skill_impact_on_matches": true
        },
        "format_config": {
            "HEAD_TO_HEAD": {
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                },
                "match_simulation": {
                    "score_ranges": {
                        "win": {"loser_max": 3, "winner_max": 4},
                        "draw": {"max": 1, "min": 0}
                    },
                    "draw_probability": 0.1,
                    "away_win_probability": 0.4,
                    "home_win_probability": 0.5
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "LOW"
        }
    }'::jsonb,
    true, false, false
)
ON CONFLICT (code) DO UPDATE SET
    name        = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config,
    is_active   = EXCLUDED.is_active,
    updated_at  = NOW();


-- ─── 3. Stole My Goal ────────────────────────────────────────────────────────
INSERT INTO game_presets (code, name, description, game_config, is_active, is_recommended, is_locked)
VALUES (
    'stole_my_goal',
    'Stole My Goal',
    'Small-sided game testing finishing, marking and stamina',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "small_sided_games",
            "difficulty_level": "beginner",
            "recommended_player_count": {"min": 6, "max": 20}
        },
        "skill_config": {
            "skills_tested": ["finishing", "marking", "stamina"],
            "skill_weights": {
                "finishing": 0.40,
                "marking":   0.35,
                "stamina":   0.25
            },
            "skill_impact_on_matches": true
        },
        "format_config": {
            "HEAD_TO_HEAD": {
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                },
                "match_simulation": {
                    "score_ranges": {
                        "win": {"loser_max": 5, "winner_max": 6},
                        "draw": {"max": 3, "min": 0}
                    },
                    "draw_probability": 0.25,
                    "away_win_probability": 0.35,
                    "home_win_probability": 0.40
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "HIGH"
        }
    }'::jsonb,
    true, false, false
)
ON CONFLICT (code) DO UPDATE SET
    name        = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config,
    is_active   = EXCLUDED.is_active,
    updated_at  = NOW();


-- ─── Verify ──────────────────────────────────────────────────────────────────
SELECT id, code, name, is_active, is_recommended,
       jsonb_array_length(game_config->'skill_config'->'skills_tested') AS skill_count
FROM game_presets
ORDER BY id;
