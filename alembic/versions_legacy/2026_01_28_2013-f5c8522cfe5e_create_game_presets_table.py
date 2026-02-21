"""create_game_presets_table

Revision ID: f5c8522cfe5e
Revises: 47ebca7dc3a8
Create Date: 2026-01-28 20:13:20.211257

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import json


# revision identifiers, used by Alembic.
revision = 'f5c8522cfe5e'
down_revision = '47ebca7dc3a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create game_presets table and update semesters table"""

    # Create game_presets table
    op.create_table(
        'game_presets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('game_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_game_presets_created_by'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_game_presets_code')
    )

    # Create indexes on game_presets
    op.create_index('ix_game_presets_code', 'game_presets', ['code'])
    op.create_index('ix_game_presets_active', 'game_presets', ['is_active'])
    op.create_index('ix_game_presets_config', 'game_presets', ['game_config'], postgresql_using='gin')

    # Add game_preset_id to semesters
    op.add_column(
        'semesters',
        sa.Column('game_preset_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_semesters_game_preset',
        'semesters',
        'game_presets',
        ['game_preset_id'],
        ['id']
    )
    op.create_index('ix_semesters_game_preset', 'semesters', ['game_preset_id'])

    # Add game_config_overrides to semesters
    op.add_column(
        'semesters',
        sa.Column('game_config_overrides', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_index('ix_semesters_overrides', 'semesters', ['game_config_overrides'], postgresql_using='gin')

    # Seed initial game presets
    game_presets_table = sa.table(
        'game_presets',
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('game_config', postgresql.JSONB),
        sa.column('is_active', sa.Boolean),
    )

    # Preset 1: GanFootvolley
    gan_footvolley_config = {
        "version": "1.0",
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {
                    "draw_probability": 0.15,
                    "home_win_probability": 0.45,
                    "away_win_probability": 0.40,
                    "score_ranges": {
                        "draw": {"min": 0, "max": 2},
                        "win": {"winner_max": 3, "loser_max": 2}
                    }
                },
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                }
            }
        },
        "skill_config": {
            "skills_tested": ["ball_control", "agility", "stamina"],
            "skill_weights": {
                "ball_control": 0.50,
                "agility": 0.30,
                "stamina": 0.20
            },
            "skill_impact_on_matches": True
        },
        "simulation_config": {
            "performance_variation": "MEDIUM",
            "ranking_distribution": "NORMAL",
            "player_selection": "auto"
        },
        "metadata": {
            "game_category": "beach_sports",
            "recommended_player_count": {"min": 4, "max": 16},
            "difficulty_level": "intermediate"
        }
    }

    # Preset 2: GanFoottennis
    gan_foottennis_config = {
        "version": "1.0",
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {
                    "draw_probability": 0.10,
                    "home_win_probability": 0.50,
                    "away_win_probability": 0.40,
                    "score_ranges": {
                        "draw": {"min": 0, "max": 1},
                        "win": {"winner_max": 4, "loser_max": 3}
                    }
                },
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                }
            }
        },
        "skill_config": {
            "skills_tested": ["technique", "agility", "game_sense"],
            "skill_weights": {
                "technique": 0.45,
                "agility": 0.35,
                "game_sense": 0.20
            },
            "skill_impact_on_matches": True
        },
        "simulation_config": {
            "performance_variation": "LOW",
            "ranking_distribution": "NORMAL",
            "player_selection": "auto"
        },
        "metadata": {
            "game_category": "racquet_sports",
            "recommended_player_count": {"min": 4, "max": 12},
            "difficulty_level": "advanced"
        }
    }

    # Preset 3: Stole My Goal
    stole_my_goal_config = {
        "version": "1.0",
        "format_config": {
            "HEAD_TO_HEAD": {
                "match_simulation": {
                    "draw_probability": 0.25,
                    "home_win_probability": 0.40,
                    "away_win_probability": 0.35,
                    "score_ranges": {
                        "draw": {"min": 0, "max": 3},
                        "win": {"winner_max": 6, "loser_max": 5}
                    }
                },
                "ranking_rules": {
                    "primary": "points",
                    "tiebreakers": ["goal_difference", "goals_for", "user_id"],
                    "points_system": {"win": 3, "draw": 1, "loss": 0}
                }
            }
        },
        "skill_config": {
            "skills_tested": ["finishing", "defending", "stamina"],
            "skill_weights": {
                "finishing": 0.40,
                "defending": 0.35,
                "stamina": 0.25
            },
            "skill_impact_on_matches": True
        },
        "simulation_config": {
            "performance_variation": "HIGH",
            "ranking_distribution": "NORMAL",
            "player_selection": "auto"
        },
        "metadata": {
            "game_category": "small_sided_games",
            "recommended_player_count": {"min": 6, "max": 20},
            "difficulty_level": "beginner"
        }
    }

    # Insert presets
    # NOTE: Pass dict directly, NOT json.dumps() - SQLAlchemy handles JSONB serialization
    op.bulk_insert(
        game_presets_table,
        [
            {
                'code': 'gan_footvolley',
                'name': 'GanFootvolley',
                'description': 'Beach volleyball with feet - emphasizes agility, stamina, and ball control',
                'game_config': gan_footvolley_config,  # Direct dict, no json.dumps
                'is_active': True,
            },
            {
                'code': 'gan_foottennis',
                'name': 'GanFoottennis',
                'description': 'Tennis with a football - emphasizes technique, agility, and game sense',
                'game_config': gan_foottennis_config,  # Direct dict, no json.dumps
                'is_active': True,
            },
            {
                'code': 'stole_my_goal',
                'name': 'Stole My Goal',
                'description': 'Small-sided game focusing on finishing and defensive skills',
                'game_config': stole_my_goal_config,  # Direct dict, no json.dumps
                'is_active': True,
            },
        ]
    )


def downgrade() -> None:
    """Drop game_presets table and revert semesters changes"""

    # Drop semesters columns and indexes
    op.drop_index('ix_semesters_overrides', table_name='semesters')
    op.drop_column('semesters', 'game_config_overrides')

    op.drop_index('ix_semesters_game_preset', table_name='semesters')
    op.drop_constraint('fk_semesters_game_preset', 'semesters', type_='foreignkey')
    op.drop_column('semesters', 'game_preset_id')

    # Drop game_presets table and indexes
    op.drop_index('ix_game_presets_config', table_name='game_presets')
    op.drop_index('ix_game_presets_active', table_name='game_presets')
    op.drop_index('ix_game_presets_code', table_name='game_presets')
    op.drop_table('game_presets')