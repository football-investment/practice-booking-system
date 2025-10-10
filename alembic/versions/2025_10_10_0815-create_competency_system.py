"""Create Competency System

Revision ID: competency_system
Revises: adaptive_learning_system
Create Date: 2025-10-10 08:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'competency_system'
down_revision = 'adaptive_learning_system'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create competency tracking and assessment system.

    Tables:
    1. competency_categories - Main competency areas (Technical, Tactical, etc.)
    2. competency_skills - Sub-skills within categories
    3. user_competency_scores - User scores per category
    4. user_skill_scores - User scores per skill
    5. competency_assessments - Assessment history
    6. competency_milestones - Achievement levels
    7. user_competency_milestones - User milestone achievements
    """

    # ==========================================
    # 1. COMPETENCY CATEGORIES
    # ==========================================
    op.create_table('competency_categories',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('max_score', sa.Integer, default=100),
        sa.Column('weight', sa.Numeric(5, 2), default=1.0),  # Weight in overall competency
        sa.Column('display_order', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_competency_categories_spec', 'competency_categories', ['specialization_id'])

    # ==========================================
    # 2. COMPETENCY SKILLS (sub-categories)
    # ==========================================
    op.create_table('competency_skills',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competency_category_id', sa.Integer, sa.ForeignKey('competency_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('max_score', sa.Integer, default=100),
        sa.Column('display_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )

    # ==========================================
    # 3. USER COMPETENCY SCORES
    # ==========================================
    op.create_table('user_competency_scores',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_category_id', sa.Integer, sa.ForeignKey('competency_categories.id', ondelete='CASCADE'), nullable=False),

        # Scores
        sa.Column('current_score', sa.Integer, default=0),
        sa.Column('max_score', sa.Integer, default=100),
        sa.Column('percentage', sa.Numeric(5, 2), default=0.0),  # current_score / max_score * 100

        # Level within this competency
        sa.Column('competency_level', sa.Integer, default=1),  # 1=Beginner, 2=Developing, 3=Competent, 4=Proficient, 5=Expert

        # History
        sa.Column('previous_score', sa.Integer, default=0),
        sa.Column('score_change', sa.Integer, default=0),  # current - previous
        sa.Column('last_assessed', sa.DateTime, nullable=True),
        sa.Column('assessment_count', sa.Integer, default=0),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()')),

        sa.UniqueConstraint('user_id', 'competency_category_id', name='uq_user_competency_category')
    )
    op.create_index('ix_user_competency_scores_user', 'user_competency_scores', ['user_id'])
    op.create_index('ix_user_competency_scores_category', 'user_competency_scores', ['competency_category_id'])

    # ==========================================
    # 4. USER SKILL SCORES (detailed breakdown)
    # ==========================================
    op.create_table('user_skill_scores',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_skill_id', sa.Integer, sa.ForeignKey('competency_skills.id', ondelete='CASCADE'), nullable=False),

        sa.Column('current_score', sa.Integer, default=0),
        sa.Column('max_score', sa.Integer, default=100),
        sa.Column('percentage', sa.Numeric(5, 2), default=0.0),

        sa.Column('last_assessed', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()')),

        sa.UniqueConstraint('user_id', 'competency_skill_id', name='uq_user_competency_skill')
    )

    # ==========================================
    # 5. COMPETENCY ASSESSMENTS
    # ==========================================
    op.create_table('competency_assessments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_category_id', sa.Integer, sa.ForeignKey('competency_categories.id'), nullable=True),
        sa.Column('competency_skill_id', sa.Integer, sa.ForeignKey('competency_skills.id'), nullable=True),

        # Assessment details
        sa.Column('assessment_type', sa.String(50), nullable=False),
        # QUIZ, EXERCISE, PEER_REVIEW, INSTRUCTOR_REVIEW, SELF_ASSESSMENT

        sa.Column('source_id', sa.Integer, nullable=True),  # ID of quiz/exercise/review
        sa.Column('score', sa.Integer, nullable=False),
        sa.Column('max_score', sa.Integer, default=100),

        # Feedback
        sa.Column('feedback', sa.Text, nullable=True),
        sa.Column('strengths', sa.Text, nullable=True),
        sa.Column('improvements', sa.Text, nullable=True),

        # Assessor
        sa.Column('assessor_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),  # NULL if auto-assessed
        sa.Column('assessor_type', sa.String(50), nullable=True),  # SYSTEM, INSTRUCTOR, PEER, SELF

        sa.Column('assessed_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_competency_assessments_user', 'competency_assessments', ['user_id'])
    op.create_index('ix_competency_assessments_date', 'competency_assessments', ['assessed_at'])

    # ==========================================
    # 6. COMPETENCY MILESTONES
    # ==========================================
    op.create_table('competency_milestones',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('competency_category_id', sa.Integer, sa.ForeignKey('competency_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level', sa.Integer, nullable=False),  # 1-5
        sa.Column('level_name', sa.String(50), nullable=False),  # Beginner, Developing, etc.
        sa.Column('required_score', sa.Integer, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('badge_icon', sa.String(100), nullable=True),
        sa.Column('xp_reward', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )

    # ==========================================
    # 7. USER COMPETENCY MILESTONE ACHIEVEMENTS
    # ==========================================
    op.create_table('user_competency_milestones',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('competency_milestone_id', sa.Integer, sa.ForeignKey('competency_milestones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('achieved_at', sa.DateTime, server_default=sa.text('NOW()')),

        sa.UniqueConstraint('user_id', 'competency_milestone_id', name='uq_user_milestone')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('user_competency_milestones')
    op.drop_table('competency_milestones')

    op.drop_index('ix_competency_assessments_date', table_name='competency_assessments')
    op.drop_index('ix_competency_assessments_user', table_name='competency_assessments')
    op.drop_table('competency_assessments')

    op.drop_table('user_skill_scores')

    op.drop_index('ix_user_competency_scores_category', table_name='user_competency_scores')
    op.drop_index('ix_user_competency_scores_user', table_name='user_competency_scores')
    op.drop_table('user_competency_scores')

    op.drop_table('competency_skills')

    op.drop_index('ix_competency_categories_spec', table_name='competency_categories')
    op.drop_table('competency_categories')
