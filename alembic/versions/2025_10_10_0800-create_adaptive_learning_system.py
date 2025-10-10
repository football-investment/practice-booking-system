"""Create Adaptive Learning System

Revision ID: adaptive_learning_system
Revises: exercise_system
Create Date: 2025-10-10 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'adaptive_learning_system'
down_revision = 'exercise_system'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create adaptive learning system for personalized education.

    Tables:
    1. user_learning_profiles - Learning pace, preferences, metrics
    2. adaptive_recommendations - AI-generated learning suggestions
    3. user_learning_patterns - Time/day/session patterns
    4. performance_snapshots - Daily performance tracking
    """

    # ==========================================
    # 1. USER LEARNING PROFILES
    # ==========================================
    op.create_table('user_learning_profiles',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id'), nullable=True),

        # Learning Pace Analysis
        sa.Column('learning_pace', sa.String(50), default='MEDIUM'),  # SLOW, MEDIUM, FAST, ACCELERATED
        sa.Column('pace_score', sa.Numeric(5, 2), default=50.0),  # 0-100 scale

        # Content Preferences
        sa.Column('preferred_content_type', sa.String(50), default='MIXED'),  # VIDEO, TEXT, PRACTICE, INTERACTIVE, MIXED
        sa.Column('content_type_scores', JSONB, nullable=True),  # {"video": 85, "text": 60, "practice": 90}

        # Difficulty Adaptation
        sa.Column('difficulty_preference', sa.String(50), default='ADAPTIVE'),  # EASY, MEDIUM, HARD, ADAPTIVE
        sa.Column('current_difficulty_level', sa.Numeric(5, 2), default=50.0),  # 0-100 scale

        # Performance Metrics
        sa.Column('quiz_average_score', sa.Numeric(5, 2), default=0.0),
        sa.Column('quiz_completion_rate', sa.Numeric(5, 2), default=0.0),
        sa.Column('lesson_completion_rate', sa.Numeric(5, 2), default=0.0),
        sa.Column('exercise_success_rate', sa.Numeric(5, 2), default=0.0),

        # Time Metrics
        sa.Column('total_study_time_minutes', sa.Integer, default=0),
        sa.Column('average_time_per_module', sa.Numeric(8, 2), default=0.0),
        sa.Column('average_time_per_lesson', sa.Numeric(8, 2), default=0.0),
        sa.Column('study_sessions_count', sa.Integer, default=0),

        # Engagement Metrics
        sa.Column('days_active', sa.Integer, default=0),
        sa.Column('longest_streak_days', sa.Integer, default=0),
        sa.Column('current_streak_days', sa.Integer, default=0),
        sa.Column('last_activity_date', sa.Date, nullable=True),

        # AI Recommendations
        sa.Column('next_recommended_lesson_id', sa.Integer, sa.ForeignKey('lessons.id'), nullable=True),
        sa.Column('recommended_study_time_minutes', sa.Integer, default=30),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()'))
    )
    op.create_index('ix_user_learning_profiles_user', 'user_learning_profiles', ['user_id'])
    op.create_index('ix_user_learning_profiles_spec', 'user_learning_profiles', ['specialization_id'])

    # ==========================================
    # 2. ADAPTIVE RECOMMENDATIONS
    # ==========================================
    op.create_table('adaptive_recommendations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Recommendation Details
        sa.Column('recommendation_type', sa.String(50), nullable=False),
        # Types: REVIEW_LESSON, PRACTICE_MORE, TAKE_BREAK, ADVANCE_FASTER,
        #        SLOW_DOWN, FOCUS_ON_WEAKNESS, TRY_DIFFERENT_CONTENT, SCHEDULE_SESSION

        sa.Column('related_lesson_id', sa.Integer, sa.ForeignKey('lessons.id'), nullable=True),
        sa.Column('related_module_id', sa.Integer, sa.ForeignKey('lesson_modules.id'), nullable=True),

        # Priority & Reasoning
        sa.Column('priority', sa.Integer, default=2),  # 1=high, 2=medium, 3=low
        sa.Column('confidence_score', sa.Numeric(5, 2), default=80.0),  # AI confidence (0-100)
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('action_text', sa.Text, nullable=False),  # User-facing text

        # Metadata
        sa.Column('data', JSONB, nullable=True),  # Extra context

        # Status
        sa.Column('status', sa.String(50), default='ACTIVE'),  # ACTIVE, DISMISSED, COMPLETED, EXPIRED
        sa.Column('is_dismissed', sa.Boolean, default=False),
        sa.Column('dismissed_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_adaptive_recommendations_user', 'adaptive_recommendations', ['user_id'])
    op.create_index('ix_adaptive_recommendations_status', 'adaptive_recommendations', ['status'])
    op.create_index('ix_adaptive_recommendations_priority', 'adaptive_recommendations', ['priority'])

    # ==========================================
    # 3. USER LEARNING PATTERNS
    # ==========================================
    op.create_table('user_learning_patterns',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),

        # Time-of-Day Patterns
        sa.Column('preferred_study_hours', JSONB, nullable=True),  # {"morning": 0.3, "afternoon": 0.5, ...}
        sa.Column('most_productive_hour', sa.Integer, nullable=True),  # 0-23

        # Day-of-Week Patterns
        sa.Column('preferred_study_days', JSONB, nullable=True),  # {"monday": 0.8, ...}
        sa.Column('most_productive_day', sa.String(20), nullable=True),  # MONDAY, TUESDAY, etc.

        # Session Patterns
        sa.Column('average_session_length_minutes', sa.Numeric(8, 2), default=0.0),
        sa.Column('optimal_session_length_minutes', sa.Integer, default=45),
        sa.Column('sessions_per_week', sa.Numeric(5, 2), default=0.0),

        # Content Consumption
        sa.Column('modules_completed_per_session', sa.Numeric(5, 2), default=0.0),
        sa.Column('quiz_attempts_per_quiz', sa.Numeric(5, 2), default=1.0),

        # Break Patterns
        sa.Column('needs_break_indicator', sa.Boolean, default=False),
        sa.Column('last_break_suggestion', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()'))
    )

    # ==========================================
    # 4. PERFORMANCE SNAPSHOTS
    # ==========================================
    op.create_table('performance_snapshots',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id'), nullable=True),

        sa.Column('snapshot_date', sa.Date, nullable=False),

        # Scores at this point in time
        sa.Column('quiz_average', sa.Numeric(5, 2), nullable=True),
        sa.Column('quiz_count', sa.Integer, nullable=True),
        sa.Column('lessons_completed', sa.Integer, nullable=True),
        sa.Column('modules_completed', sa.Integer, nullable=True),
        sa.Column('exercises_submitted', sa.Integer, nullable=True),
        sa.Column('total_xp', sa.Integer, nullable=True),
        sa.Column('current_level', sa.Integer, nullable=True),

        # Study time
        sa.Column('total_minutes_studied', sa.Integer, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),

        sa.UniqueConstraint('user_id', 'snapshot_date', name='uq_user_snapshot_date')
    )
    op.create_index('ix_performance_snapshots_user', 'performance_snapshots', ['user_id'])
    op.create_index('ix_performance_snapshots_date', 'performance_snapshots', ['snapshot_date'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_performance_snapshots_date', table_name='performance_snapshots')
    op.drop_index('ix_performance_snapshots_user', table_name='performance_snapshots')
    op.drop_table('performance_snapshots')

    op.drop_table('user_learning_patterns')

    op.drop_index('ix_adaptive_recommendations_priority', table_name='adaptive_recommendations')
    op.drop_index('ix_adaptive_recommendations_status', table_name='adaptive_recommendations')
    op.drop_index('ix_adaptive_recommendations_user', table_name='adaptive_recommendations')
    op.drop_table('adaptive_recommendations')

    op.drop_index('ix_user_learning_profiles_spec', table_name='user_learning_profiles')
    op.drop_index('ix_user_learning_profiles_user', table_name='user_learning_profiles')
    op.drop_table('user_learning_profiles')
