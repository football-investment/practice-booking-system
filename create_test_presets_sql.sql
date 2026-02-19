-- Quick SQL workaround to create test presets directly in database
-- Run with: PGDATABASE=lfa_intern_system psql -U postgres -h localhost -f create_test_presets_sql.sql

-- 1. High Intensity Training (stamina + speed focus)
INSERT INTO game_presets (
    code, name, description, game_config, is_active, is_recommended, is_locked
) VALUES (
    'high_intensity_training',
    'High Intensity Training',
    'Endurance and speed focused training with high stamina requirements',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "fitness",
            "difficulty_level": "advanced",
            "recommended_player_count": {"min": 8, "max": 20}
        },
        "skill_config": {
            "skills_tested": ["stamina", "sprint_speed", "acceleration", "agility"],
            "skill_weights": {
                "stamina": 1.2,
                "sprint_speed": 0.8,
                "acceleration": 0.6,
                "agility": 0.4
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
                        "win": {"loser_max": 4, "winner_max": 6},
                        "draw": {"max": 3, "min": 0}
                    },
                    "draw_probability": 0.2,
                    "away_win_probability": 0.35,
                    "home_win_probability": 0.45
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "HIGH"
        }
    }'::jsonb,
    true,
    false,
    false
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config;

-- 2. Technical Mastery (ball control + passing focus)
INSERT INTO game_presets (
    code, name, description, game_config, is_active, is_recommended, is_locked
) VALUES (
    'technical_mastery',
    'Technical Mastery',
    'Advanced technical skills with focus on ball control and passing accuracy',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "technical",
            "difficulty_level": "advanced",
            "recommended_player_count": {"min": 6, "max": 16}
        },
        "skill_config": {
            "skills_tested": ["ball_control", "passing", "first_touch", "dribbling", "vision"],
            "skill_weights": {
                "ball_control": 1.5,
                "passing": 1.0,
                "first_touch": 0.8,
                "dribbling": 0.6,
                "vision": 0.5
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
                        "win": {"loser_max": 2, "winner_max": 4},
                        "draw": {"max": 2, "min": 0}
                    },
                    "draw_probability": 0.3,
                    "away_win_probability": 0.35,
                    "home_win_probability": 0.35
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "LOW"
        }
    }'::jsonb,
    true,
    false,
    false
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config;

-- 3. Goal Scoring Specialist (finishing focus)
INSERT INTO game_presets (
    code, name, description, game_config, is_active, is_recommended, is_locked
) VALUES (
    'goal_scoring_specialist',
    'Goal Scoring Specialist',
    'Offensive focused game testing finishing and shooting abilities',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "offensive",
            "difficulty_level": "intermediate",
            "recommended_player_count": {"min": 8, "max": 20}
        },
        "skill_config": {
            "skills_tested": ["finishing", "shot_power", "long_shots", "volleys", "positioning_off"],
            "skill_weights": {
                "finishing": 1.8,
                "shot_power": 1.0,
                "long_shots": 0.7,
                "volleys": 0.6,
                "positioning_off": 0.5
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
                        "win": {"loser_max": 3, "winner_max": 7},
                        "draw": {"max": 4, "min": 1}
                    },
                    "draw_probability": 0.15,
                    "away_win_probability": 0.4,
                    "home_win_probability": 0.45
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "MEDIUM"
        }
    }'::jsonb,
    true,
    false,
    false
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config;

-- 4. Defensive Masterclass (defensive skills focus)
INSERT INTO game_presets (
    code, name, description, game_config, is_active, is_recommended, is_locked
) VALUES (
    'defensive_masterclass',
    'Defensive Masterclass',
    'Defensive focused training testing marking, tackling and positioning',
    '{
        "version": "1.0",
        "metadata": {
            "game_category": "defensive",
            "difficulty_level": "intermediate",
            "recommended_player_count": {"min": 8, "max": 16}
        },
        "skill_config": {
            "skills_tested": ["marking", "tackling", "positioning_def", "strength", "aggression", "interceptions"],
            "skill_weights": {
                "marking": 1.5,
                "tackling": 1.2,
                "positioning_def": 1.0,
                "strength": 0.6,
                "aggression": 0.4,
                "interceptions": 0.8
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
                        "win": {"loser_max": 1, "winner_max": 3},
                        "draw": {"max": 1, "min": 0}
                    },
                    "draw_probability": 0.4,
                    "away_win_probability": 0.3,
                    "home_win_probability": 0.3
                }
            }
        },
        "simulation_config": {
            "player_selection": "auto",
            "ranking_distribution": "NORMAL",
            "performance_variation": "LOW"
        }
    }'::jsonb,
    true,
    false,
    false
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    game_config = EXCLUDED.game_config;

-- Verify created presets
SELECT id, code, name, is_active
FROM game_presets
WHERE code IN (
    'high_intensity_training',
    'technical_mastery',
    'goal_scoring_specialist',
    'defensive_masterclass'
)
ORDER BY id;
