"""Root initial schema - all base tables

Revision ID: w3mg03uvao74
Revises:
Create Date: 2025-08-01 00:00:00.000000

This is the TRUE ROOT migration that creates all foundational tables.
Previous root (e61ff656196a) incorrectly tried to ALTER tables before creating them.

This migration consolidates all base table creation to ensure a clean migration
chain that can be run on fresh databases without errors.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'w3mg03uvao74'
down_revision = None  # This is the TRUE ROOT
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### Base tables creation ###

    # Core system tables
    op.create_table('quizzes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category', sa.Enum('GENERAL', 'MARKETING', 'ECONOMICS', 'INFORMATICS', 'SPORTS_PHYSIOLOGY', 'NUTRITION', name='quizcategory'), nullable=False),
    sa.Column('difficulty', sa.Enum('EASY', 'MEDIUM', 'HARD', name='quizdifficulty'), nullable=False),
    sa.Column('time_limit_minutes', sa.Integer(), nullable=False),
    sa.Column('xp_reward', sa.Integer(), nullable=False),
    sa.Column('passing_score', sa.Float(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_id'), 'quizzes', ['id'], unique=False)

    op.create_table('semesters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_semesters_code'), 'semesters', ['code'], unique=True)
    op.create_index(op.f('ix_semesters_id'), 'semesters', ['id'], unique=False)

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('nickname', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.Enum('ADMIN', 'INSTRUCTOR', 'STUDENT', name='userrole'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('onboarding_completed', sa.Boolean(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('emergency_contact', sa.String(), nullable=True),
    sa.Column('emergency_phone', sa.String(), nullable=True),
    sa.Column('date_of_birth', sa.DateTime(), nullable=True),
    sa.Column('medical_notes', sa.String(), nullable=True),
    sa.Column('interests', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Tables with FK to base tables
    op.create_table('groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('semester_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)

    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=False),
    sa.Column('recipient_id', sa.Integer(), nullable=False),
    sa.Column('subject', sa.String(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'URGENT', name='messagepriority'), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('is_edited', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('edited_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)

    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('semester_id', sa.Integer(), nullable=False),
    sa.Column('instructor_id', sa.Integer(), nullable=True),
    sa.Column('max_participants', sa.Integer(), nullable=True),
    sa.Column('required_sessions', sa.Integer(), nullable=True),
    sa.Column('xp_reward', sa.Integer(), nullable=True),
    sa.Column('deadline', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('difficulty', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)

    op.create_table('quiz_attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('quiz_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('time_spent_minutes', sa.Float(), nullable=True),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('total_questions', sa.Integer(), nullable=False),
    sa.Column('correct_answers', sa.Integer(), nullable=False),
    sa.Column('xp_awarded', sa.Integer(), nullable=False),
    sa.Column('passed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_attempts_id'), 'quiz_attempts', ['id'], unique=False)

    op.create_table('quiz_questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('quiz_id', sa.Integer(), nullable=False),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('question_type', sa.Enum('MULTIPLE_CHOICE', 'TRUE_FALSE', 'FILL_IN_BLANK', name='questiontype'), nullable=False),
    sa.Column('points', sa.Integer(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_id'), 'quiz_questions', ['id'], unique=False)

    op.create_table('user_achievements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('badge_type', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('icon', sa.String(), nullable=True),
    sa.Column('earned_at', sa.DateTime(), nullable=True),
    sa.Column('semester_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_achievements_id'), 'user_achievements', ['id'], unique=False)

    op.create_table('user_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('semesters_participated', sa.Integer(), nullable=True),
    sa.Column('first_semester_date', sa.DateTime(), nullable=True),
    sa.Column('current_streak', sa.Integer(), nullable=True),
    sa.Column('total_bookings', sa.Integer(), nullable=True),
    sa.Column('total_attended', sa.Integer(), nullable=True),
    sa.Column('total_cancelled', sa.Integer(), nullable=True),
    sa.Column('attendance_rate', sa.Float(), nullable=True),
    sa.Column('feedback_given', sa.Integer(), nullable=True),
    sa.Column('average_rating_given', sa.Float(), nullable=True),
    sa.Column('punctuality_score', sa.Float(), nullable=True),
    sa.Column('total_xp', sa.Integer(), nullable=True),
    sa.Column('level', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_stats_id'), 'user_stats', ['id'], unique=False)

    op.create_table('group_users',
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('group_id', 'user_id')
    )

    op.create_table('project_enrollment_quizzes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('quiz_attempt_id', sa.Integer(), nullable=False),
    sa.Column('enrollment_priority', sa.Integer(), nullable=True),
    sa.Column('enrollment_confirmed', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['quiz_attempt_id'], ['quiz_attempts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'user_id', name='unique_project_user_enrollment_quiz')
    )
    op.create_index(op.f('ix_project_enrollment_quizzes_id'), 'project_enrollment_quizzes', ['id'], unique=False)

    op.create_table('project_enrollments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('enrolled_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('progress_status', sa.String(length=20), nullable=True),
    sa.Column('completion_percentage', sa.Float(), nullable=True),
    sa.Column('instructor_approved', sa.Boolean(), nullable=True),
    sa.Column('instructor_feedback', sa.Text(), nullable=True),
    sa.Column('enrollment_status', sa.String(length=20), nullable=True),
    sa.Column('quiz_passed', sa.Boolean(), nullable=True),
    sa.Column('final_grade', sa.String(length=5), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'user_id', name='unique_project_user')
    )
    op.create_index(op.f('ix_project_enrollments_id'), 'project_enrollments', ['id'], unique=False)

    op.create_table('project_milestones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('required_sessions', sa.Integer(), nullable=True),
    sa.Column('xp_reward', sa.Integer(), nullable=True),
    sa.Column('deadline', sa.Date(), nullable=True),
    sa.Column('is_required', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_milestones_id'), 'project_milestones', ['id'], unique=False)

    op.create_table('quiz_answer_options',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('option_text', sa.String(length=500), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_answer_options_id'), 'quiz_answer_options', ['id'], unique=False)

    # CRITICAL: sessions table creation - this was missing from root before!
    op.create_table('sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('date_start', sa.DateTime(), nullable=False),
    sa.Column('date_end', sa.DateTime(), nullable=False),
    sa.Column('mode', sa.Enum('ONLINE', 'OFFLINE', 'HYBRID', name='sessionmode'), nullable=True),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('meeting_link', sa.String(), nullable=True),
    sa.Column('sport_type', sa.String(), nullable=True),
    sa.Column('level', sa.String(), nullable=True),
    sa.Column('instructor_name', sa.String(), nullable=True),
    sa.Column('semester_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=True),  # IMPORTANT: nullable from the start!
    sa.Column('instructor_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
    sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)

    # Tables depending on sessions
    op.create_table('bookings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'CONFIRMED', 'CANCELLED', 'WAITLISTED', name='bookingstatus'), nullable=True),
    sa.Column('waitlist_position', sa.Integer(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.Column('attended_status', sa.String(length=20), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)

    op.create_table('feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Float(), nullable=False),
    sa.Column('instructor_rating', sa.Float(), nullable=True),
    sa.Column('session_quality', sa.Float(), nullable=True),
    sa.Column('would_recommend', sa.Boolean(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('is_anonymous', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('instructor_rating IS NULL OR (instructor_rating >= 1.0 AND instructor_rating <= 5.0)', name='instructor_rating_range'),
    sa.CheckConstraint('rating >= 1.0 AND rating <= 5.0', name='rating_range'),
    sa.CheckConstraint('session_quality IS NULL OR (session_quality >= 1.0 AND session_quality <= 5.0)', name='session_quality_range'),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)

    op.create_table('project_milestone_progress',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('enrollment_id', sa.Integer(), nullable=False),
    sa.Column('milestone_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('instructor_feedback', sa.Text(), nullable=True),
    sa.Column('instructor_approved_at', sa.DateTime(), nullable=True),
    sa.Column('sessions_completed', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['enrollment_id'], ['project_enrollments.id'], ),
    sa.ForeignKeyConstraint(['milestone_id'], ['project_milestones.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('enrollment_id', 'milestone_id', name='unique_enrollment_milestone')
    )
    op.create_index(op.f('ix_project_milestone_progress_id'), 'project_milestone_progress', ['id'], unique=False)

    op.create_table('project_quizzes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('quiz_id', sa.Integer(), nullable=False),
    sa.Column('milestone_id', sa.Integer(), nullable=True),
    sa.Column('quiz_type', sa.String(length=50), nullable=False),
    sa.Column('is_required', sa.Boolean(), nullable=True),
    sa.Column('minimum_score', sa.Float(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['milestone_id'], ['project_milestones.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'quiz_id', 'quiz_type', name='unique_project_quiz_type')
    )
    op.create_index(op.f('ix_project_quizzes_id'), 'project_quizzes', ['id'], unique=False)

    op.create_table('project_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('milestone_id', sa.Integer(), nullable=True),
    sa.Column('is_required', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['milestone_id'], ['project_milestones.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'session_id', name='unique_project_session')
    )
    op.create_index(op.f('ix_project_sessions_id'), 'project_sessions', ['id'], unique=False)

    op.create_table('quiz_user_answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('selected_option_id', sa.Integer(), nullable=True),
    sa.Column('answer_text', sa.String(length=1000), nullable=True),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['attempt_id'], ['quiz_attempts.id'], ),
    sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ),
    sa.ForeignKeyConstraint(['selected_option_id'], ['quiz_answer_options.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_user_answers_id'), 'quiz_user_answers', ['id'], unique=False)

    op.create_table('attendance',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('booking_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PRESENT', 'ABSENT', 'LATE', 'EXCUSED', name='attendancestatus'), nullable=True),
    sa.Column('check_in_time', sa.DateTime(), nullable=True),
    sa.Column('check_out_time', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.Column('marked_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ),
    sa.ForeignKeyConstraint(['marked_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendance_id'), 'attendance', ['id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('type', sa.Enum('BOOKING_CONFIRMED', 'BOOKING_CANCELLED', 'SESSION_REMINDER', 'SESSION_CANCELLED', 'WAITLIST_PROMOTED', 'GENERAL', name='notificationtype'), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('related_session_id', sa.Integer(), nullable=True),
    sa.Column('related_booking_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['related_booking_id'], ['bookings.id'], ),
    sa.ForeignKeyConstraint(['related_session_id'], ['sessions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### Reverse order - drop child tables first ###
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_attendance_id'), table_name='attendance')
    op.drop_table('attendance')
    op.drop_index(op.f('ix_quiz_user_answers_id'), table_name='quiz_user_answers')
    op.drop_table('quiz_user_answers')
    op.drop_index(op.f('ix_project_sessions_id'), table_name='project_sessions')
    op.drop_table('project_sessions')
    op.drop_index(op.f('ix_project_quizzes_id'), table_name='project_quizzes')
    op.drop_table('project_quizzes')
    op.drop_index(op.f('ix_project_milestone_progress_id'), table_name='project_milestone_progress')
    op.drop_table('project_milestone_progress')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')
    op.drop_index(op.f('ix_bookings_id'), table_name='bookings')
    op.drop_table('bookings')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_quiz_answer_options_id'), table_name='quiz_answer_options')
    op.drop_table('quiz_answer_options')
    op.drop_index(op.f('ix_project_milestones_id'), table_name='project_milestones')
    op.drop_table('project_milestones')
    op.drop_index(op.f('ix_project_enrollments_id'), table_name='project_enrollments')
    op.drop_table('project_enrollments')
    op.drop_index(op.f('ix_project_enrollment_quizzes_id'), table_name='project_enrollment_quizzes')
    op.drop_table('project_enrollment_quizzes')
    op.drop_table('group_users')
    op.drop_index(op.f('ix_user_stats_id'), table_name='user_stats')
    op.drop_table('user_stats')
    op.drop_index(op.f('ix_user_achievements_id'), table_name='user_achievements')
    op.drop_table('user_achievements')
    op.drop_index(op.f('ix_quiz_questions_id'), table_name='quiz_questions')
    op.drop_table('quiz_questions')
    op.drop_index(op.f('ix_quiz_attempts_id'), table_name='quiz_attempts')
    op.drop_table('quiz_attempts')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_groups_id'), table_name='groups')
    op.drop_table('groups')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_semesters_id'), table_name='semesters')
    op.drop_index(op.f('ix_semesters_code'), table_name='semesters')
    op.drop_table('semesters')
    op.drop_index(op.f('ix_quizzes_id'), table_name='quizzes')
    op.drop_table('quizzes')
    # ### end Alembic commands ###
