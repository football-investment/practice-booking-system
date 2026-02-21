"""Create Exercise System

Revision ID: exercise_system
Revises: quiz_curriculum_link
Create Date: 2025-10-10 07:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'exercise_system'
down_revision = 'quiz_curriculum_link'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create exercise system for practical assignments in curriculum.

    Changes:
    1. Create exercises table
    2. Create user_exercise_submissions table
    3. Create exercise_feedback table
    """

    # 1. CREATE EXERCISES TABLE
    op.create_table('exercises',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.Integer, sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Exercise content and instructions
        sa.Column('exercise_type', sa.String(50), nullable=False),  # VIDEO_UPLOAD, DOCUMENT, PRACTICAL_DEMO, REFLECTION, PROJECT
        sa.Column('instructions', sa.Text, nullable=False),
        sa.Column('requirements', JSONB, nullable=True),  # Detailed requirements (file format, duration, criteria, etc.)

        # Grading
        sa.Column('max_points', sa.Integer, default=100),
        sa.Column('passing_score', sa.Float, default=70.0),
        sa.Column('xp_reward', sa.Integer, default=100),

        # Metadata
        sa.Column('order_number', sa.Integer, default=1),
        sa.Column('estimated_time_minutes', sa.Integer, nullable=True),
        sa.Column('is_mandatory', sa.Boolean, default=True),
        sa.Column('allow_resubmission', sa.Boolean, default=True),
        sa.Column('deadline_days', sa.Integer, nullable=True),  # Days after lesson unlock

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()'))
    )
    op.create_index('ix_exercises_lesson', 'exercises', ['lesson_id'])

    # 2. CREATE USER_EXERCISE_SUBMISSIONS TABLE
    op.create_table('user_exercise_submissions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exercise_id', sa.Integer, sa.ForeignKey('exercises.id', ondelete='CASCADE'), nullable=False),

        # Submission data
        sa.Column('submission_type', sa.String(50), nullable=False),  # VIDEO, DOCUMENT, TEXT, FILE
        sa.Column('submission_url', sa.String(500), nullable=True),  # S3 URL or external link
        sa.Column('submission_text', sa.Text, nullable=True),  # Text-based submissions
        sa.Column('submission_data', JSONB, nullable=True),  # Additional metadata

        # Status and grading
        sa.Column('status', sa.String(50), default='DRAFT', nullable=False),  # DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, REVISION_REQUESTED
        sa.Column('score', sa.Float, nullable=True),
        sa.Column('passed', sa.Boolean, nullable=True),
        sa.Column('xp_awarded', sa.Integer, default=0),

        # Feedback
        sa.Column('instructor_feedback', sa.Text, nullable=True),
        sa.Column('reviewed_by', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, onupdate=sa.text('NOW()'))
    )
    op.create_index('ix_submissions_user', 'user_exercise_submissions', ['user_id'])
    op.create_index('ix_submissions_exercise', 'user_exercise_submissions', ['exercise_id'])
    op.create_index('ix_submissions_status', 'user_exercise_submissions', ['status'])

    # 3. CREATE EXERCISE_FEEDBACK TABLE (for detailed rubric-based feedback)
    op.create_table('exercise_feedback',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('submission_id', sa.Integer, sa.ForeignKey('user_exercise_submissions.id', ondelete='CASCADE'), nullable=False),

        # Rubric item
        sa.Column('criterion', sa.String(255), nullable=False),  # e.g., "Technical Execution"
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('max_score', sa.Float, nullable=False),
        sa.Column('feedback', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_feedback_submission', 'exercise_feedback', ['submission_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_feedback_submission', table_name='exercise_feedback')
    op.drop_table('exercise_feedback')

    op.drop_index('ix_submissions_status', table_name='user_exercise_submissions')
    op.drop_index('ix_submissions_exercise', table_name='user_exercise_submissions')
    op.drop_index('ix_submissions_user', table_name='user_exercise_submissions')
    op.drop_table('user_exercise_submissions')

    op.drop_index('ix_exercises_lesson', table_name='exercises')
    op.drop_table('exercises')
