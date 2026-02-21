"""Integrate Quizzes with Curriculum

Revision ID: quiz_curriculum_link
Revises: curriculum_system
Create Date: 2025-10-09 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'quiz_curriculum_link'
down_revision = 'curriculum_system'
branch_labels = None
depends_on = None


def upgrade():
    """
    Integrate existing quiz system with new curriculum structure.

    Changes:
    1. Add LESSON to QuizCategory enum
    2. Add curriculum fields to quizzes table
    3. Create lesson_quizzes link table
    4. Add unlock logic fields
    """

    # 0. ADD 'LESSON' TO QuizCategory ENUM (uppercase to match existing enum pattern)
    op.execute("ALTER TYPE quizcategory ADD VALUE IF NOT EXISTS 'LESSON'")

    # 1. ADD CURRICULUM FIELDS TO QUIZZES (skip already existing fields)
    op.add_column('quizzes', sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id'), nullable=True))
    op.add_column('quizzes', sa.Column('level_id', sa.Integer, nullable=True))
    op.add_column('quizzes', sa.Column('lesson_id', sa.Integer, sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=True))
    # passing_score and xp_reward already exist!
    op.add_column('quizzes', sa.Column('unlock_next_lesson', sa.Boolean, default=False))

    # Create indexes
    op.create_index('ix_quizzes_specialization', 'quizzes', ['specialization_id'])
    op.create_index('ix_quizzes_lesson', 'quizzes', ['lesson_id'])
    op.create_index('ix_quizzes_level', 'quizzes', ['level_id'])

    # 2. CREATE LESSON_QUIZZES LINK TABLE
    op.create_table('lesson_quizzes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.Integer, sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quiz_id', sa.Integer, sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_prerequisite', sa.Boolean, default=True),  # Must pass to complete lesson
        sa.Column('order_number', sa.Integer, default=1),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('lesson_id', 'quiz_id', name='uq_lesson_quiz')
    )
    op.create_index('ix_lesson_quizzes_lesson', 'lesson_quizzes', ['lesson_id'])
    op.create_index('ix_lesson_quizzes_quiz', 'lesson_quizzes', ['quiz_id'])


def downgrade():
    # Drop lesson_quizzes
    op.drop_index('ix_lesson_quizzes_quiz', table_name='lesson_quizzes')
    op.drop_index('ix_lesson_quizzes_lesson', table_name='lesson_quizzes')
    op.drop_table('lesson_quizzes')

    # Drop quiz columns
    op.drop_index('ix_quizzes_level', table_name='quizzes')
    op.drop_index('ix_quizzes_lesson', table_name='quizzes')
    op.drop_index('ix_quizzes_specialization', table_name='quizzes')

    op.drop_column('quizzes', 'unlock_next_lesson')
    # xp_reward and passing_score existed before - don't drop
    op.drop_column('quizzes', 'lesson_id')
    op.drop_column('quizzes', 'level_id')
    op.drop_column('quizzes', 'specialization_id')
