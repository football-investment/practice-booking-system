"""Create Curriculum System for LMS

Revision ID: curriculum_system
Revises: spec_level_system
Create Date: 2025-10-09 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'curriculum_system'
down_revision = 'add_spec_achievements'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create complete curriculum/lesson management system for LMS platform.

    Tables created:
    1. curriculum_tracks - Master curriculum definition per specialization
    2. lessons - Individual lessons within a curriculum
    3. lesson_modules - Modules within a lesson (theory, practice, video, quiz, etc.)
    4. lesson_content - Granular content items within modules
    5. user_lesson_progress - Student progress tracking for lessons
    6. user_module_progress - Student progress tracking for modules
    """

    # 1. CURRICULUM TRACKS
    op.create_table('curriculum_tracks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('specialization_id', sa.String(50), sa.ForeignKey('specializations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('total_lessons', sa.Integer, default=0),
        sa.Column('total_hours', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    op.create_index('ix_curriculum_tracks_specialization', 'curriculum_tracks', ['specialization_id'])

    # 2. LESSONS
    op.create_table('lessons',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('curriculum_track_id', sa.Integer, sa.ForeignKey('curriculum_tracks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level_id', sa.Integer, nullable=True),  # Unlocks at this level
        sa.Column('order_number', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('estimated_hours', sa.Numeric(4, 2), default=0),
        sa.Column('xp_reward', sa.Integer, default=0),
        sa.Column('is_mandatory', sa.Boolean, default=True),
        sa.Column('prerequisites', JSONB, default='[]'),  # List of lesson IDs required before this
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    op.create_index('ix_lessons_curriculum', 'lessons', ['curriculum_track_id'])
    op.create_index('ix_lessons_level', 'lessons', ['level_id'])
    op.create_index('ix_lessons_order', 'lessons', ['order_number'])

    # 3. LESSON MODULES
    op.create_table('lesson_modules',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.Integer, sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_number', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('module_type', sa.String(50), nullable=False),  # THEORY, PRACTICE, VIDEO, EXERCISE, QUIZ, INTERACTIVE
        sa.Column('content', sa.Text),  # HTML/Markdown content
        sa.Column('content_data', JSONB),  # Flexible JSON storage for video URLs, quiz IDs, etc.
        sa.Column('estimated_minutes', sa.Integer, default=0),
        sa.Column('xp_reward', sa.Integer, default=0),
        sa.Column('is_mandatory', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    op.create_index('ix_lesson_modules_lesson', 'lesson_modules', ['lesson_id'])
    op.create_index('ix_lesson_modules_type', 'lesson_modules', ['module_type'])
    op.create_index('ix_lesson_modules_order', 'lesson_modules', ['order_number'])

    # 4. LESSON CONTENT (granular content items)
    op.create_table('lesson_content',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('lesson_module_id', sa.Integer, sa.ForeignKey('lesson_modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),  # TEXT, VIDEO, IMAGE, PDF, INTERACTIVE, EMBED
        sa.Column('content_data', JSONB, nullable=False),  # Flexible storage: {"url": "...", "duration": 300, "transcript": "..."}
        sa.Column('order_number', sa.Integer, nullable=False),
        sa.Column('is_required', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow)
    )
    op.create_index('ix_lesson_content_module', 'lesson_content', ['lesson_module_id'])
    op.create_index('ix_lesson_content_type', 'lesson_content', ['content_type'])

    # 5. USER LESSON PROGRESS
    op.create_table('user_lesson_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lesson_id', sa.Integer, sa.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), default='LOCKED'),  # LOCKED, UNLOCKED, IN_PROGRESS, COMPLETED
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('completion_percentage', sa.Integer, default=0),
        sa.Column('time_spent_minutes', sa.Integer, default=0),
        sa.Column('last_accessed', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson')
    )
    op.create_index('ix_user_lesson_progress_user', 'user_lesson_progress', ['user_id'])
    op.create_index('ix_user_lesson_progress_lesson', 'user_lesson_progress', ['lesson_id'])
    op.create_index('ix_user_lesson_progress_status', 'user_lesson_progress', ['status'])

    # 6. USER MODULE PROGRESS
    op.create_table('user_module_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lesson_module_id', sa.Integer, sa.ForeignKey('lesson_modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), default='LOCKED'),  # LOCKED, UNLOCKED, IN_PROGRESS, COMPLETED
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('time_spent_minutes', sa.Integer, default=0),
        sa.Column('last_accessed', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.UniqueConstraint('user_id', 'lesson_module_id', name='uq_user_module')
    )
    op.create_index('ix_user_module_progress_user', 'user_module_progress', ['user_id'])
    op.create_index('ix_user_module_progress_module', 'user_module_progress', ['lesson_module_id'])
    op.create_index('ix_user_module_progress_status', 'user_module_progress', ['status'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_user_module_progress_status', table_name='user_module_progress')
    op.drop_index('ix_user_module_progress_module', table_name='user_module_progress')
    op.drop_index('ix_user_module_progress_user', table_name='user_module_progress')
    op.drop_table('user_module_progress')

    op.drop_index('ix_user_lesson_progress_status', table_name='user_lesson_progress')
    op.drop_index('ix_user_lesson_progress_lesson', table_name='user_lesson_progress')
    op.drop_index('ix_user_lesson_progress_user', table_name='user_lesson_progress')
    op.drop_table('user_lesson_progress')

    op.drop_index('ix_lesson_content_type', table_name='lesson_content')
    op.drop_index('ix_lesson_content_module', table_name='lesson_content')
    op.drop_table('lesson_content')

    op.drop_index('ix_lesson_modules_order', table_name='lesson_modules')
    op.drop_index('ix_lesson_modules_type', table_name='lesson_modules')
    op.drop_index('ix_lesson_modules_lesson', table_name='lesson_modules')
    op.drop_table('lesson_modules')

    op.drop_index('ix_lessons_order', table_name='lessons')
    op.drop_index('ix_lessons_level', table_name='lessons')
    op.drop_index('ix_lessons_curriculum', table_name='lessons')
    op.drop_table('lessons')

    op.drop_index('ix_curriculum_tracks_specialization', table_name='curriculum_tracks')
    op.drop_table('curriculum_tracks')
