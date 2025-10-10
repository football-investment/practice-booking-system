"""add_adaptive_learning_models

Revision ID: 267beadbb5bf
Revises: a5ce34a0b659
Create Date: 2025-09-16 20:51:02.792220

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '267beadbb5bf'
down_revision = 'a5ce34a0b659'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend QuestionType enum
    op.execute("ALTER TYPE questiontype ADD VALUE 'matching'")
    op.execute("ALTER TYPE questiontype ADD VALUE 'short_answer'")
    op.execute("ALTER TYPE questiontype ADD VALUE 'long_answer'")
    op.execute("ALTER TYPE questiontype ADD VALUE 'calculation'")
    op.execute("ALTER TYPE questiontype ADD VALUE 'scenario_based'")
    
    # Create user_question_performance table
    op.create_table('user_question_performance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('total_attempts', sa.Integer(), nullable=True),
        sa.Column('correct_attempts', sa.Integer(), nullable=True),
        sa.Column('last_attempt_correct', sa.Boolean(), nullable=True),
        sa.Column('last_attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('difficulty_weight', sa.Float(), nullable=True),
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mastery_level', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'question_id', name='unique_user_question')
    )
    op.create_index(op.f('ix_user_question_performance_id'), 'user_question_performance', ['id'], unique=False)
    
    # Create adaptive_learning_sessions table
    op.create_table('adaptive_learning_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('GENERAL', 'PROGRAMMING', 'MATHEMATICS', 'SCIENCE', 'LANGUAGE', name='quizcategory', create_type=False), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('questions_presented', sa.Integer(), nullable=True),
        sa.Column('questions_correct', sa.Integer(), nullable=True),
        sa.Column('xp_earned', sa.Integer(), nullable=True),
        sa.Column('target_difficulty', sa.Float(), nullable=True),
        sa.Column('performance_trend', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_adaptive_learning_sessions_id'), 'adaptive_learning_sessions', ['id'], unique=False)
    
    # Create question_metadata table
    op.create_table('question_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('estimated_difficulty', sa.Float(), nullable=True),
        sa.Column('cognitive_load', sa.Float(), nullable=True),
        sa.Column('concept_tags', sa.String(length=500), nullable=True),
        sa.Column('prerequisite_concepts', sa.String(length=500), nullable=True),
        sa.Column('average_time_seconds', sa.Float(), nullable=True),
        sa.Column('global_success_rate', sa.Float(), nullable=True),
        sa.Column('last_analytics_update', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', name='unique_question_metadata')
    )
    op.create_index(op.f('ix_question_metadata_id'), 'question_metadata', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_question_metadata_id'), table_name='question_metadata')
    op.drop_table('question_metadata')
    op.drop_index(op.f('ix_adaptive_learning_sessions_id'), table_name='adaptive_learning_sessions')
    op.drop_table('adaptive_learning_sessions')
    op.drop_index(op.f('ix_user_question_performance_id'), table_name='user_question_performance')
    op.drop_table('user_question_performance')