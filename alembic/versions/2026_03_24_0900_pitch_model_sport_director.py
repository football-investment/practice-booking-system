"""Pitch model, Sport Director role, campus-level master instructor

Revision ID: 2026_03_24_0900
Revises: 2026_03_23_1100
Create Date: 2026-03-24 09:00:00.000000

Changes:
- CREATE TABLE pitches (id, campus_id, pitch_number, name, capacity, is_active, created_at)
- UNIQUE INDEX uq_campus_pitch_number ON pitches(campus_id, pitch_number)
- ALTER TABLE sessions ADD COLUMN pitch_id INT REFERENCES pitches(id)
- CREATE INDEX ix_sessions_pitch_id
- ALTER TABLE location_master_instructors ADD COLUMN campus_id INT REFERENCES campuses(id)
- CREATE UNIQUE INDEX uq_campus_master_active (partial: is_active + campus_id NOT NULL)
- ALTER TABLE instructor_positions ADD COLUMN pitch_id INT REFERENCES pitches(id)
- CREATE TABLE sport_director_assignments
- ALTER TYPE userrole ADD VALUE 'sport_director'
- CREATE TABLE pitch_instructor_assignments
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '2026_03_24_0900'
down_revision = '2026_03_23_1100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend userrole enum ──────────────────────────────────────────────
    # PostgreSQL: ADD VALUE is idempotent with IF NOT EXISTS (PostgreSQL ≥ 9.6)
    # SQLAlchemy stores enum member NAMES (uppercase: ADMIN, INSTRUCTOR, STUDENT)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SPORT_DIRECTOR'")
    # Also add lowercase alias for safety (some setups use values_callable)
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'sport_director'")

    # ── 2. Create pitches table ──────────────────────────────────────────────
    op.create_table(
        'pitches',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column('campus_id', sa.Integer(),
                  sa.ForeignKey('campuses.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('pitch_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_pitches_campus_id', 'pitches', ['campus_id'])
    op.create_unique_constraint('uq_campus_pitch_number', 'pitches',
                                ['campus_id', 'pitch_number'])

    # ── 3. sessions.pitch_id ─────────────────────────────────────────────────
    op.add_column('sessions',
        sa.Column('pitch_id', sa.Integer(),
                  sa.ForeignKey('pitches.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.create_index('ix_sessions_pitch_id', 'sessions', ['pitch_id'])

    # ── 4. location_master_instructors.campus_id ─────────────────────────────
    op.add_column('location_master_instructors',
        sa.Column('campus_id', sa.Integer(),
                  sa.ForeignKey('campuses.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.create_index('ix_location_master_instructors_campus_id',
                    'location_master_instructors', ['campus_id'])
    # Partial unique: only 1 active master per campus (NULLs excluded)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_campus_master_active
        ON location_master_instructors(campus_id)
        WHERE is_active = true AND campus_id IS NOT NULL
        """
    )

    # ── 5. instructor_positions.pitch_id ─────────────────────────────────────
    op.add_column('instructor_positions',
        sa.Column('pitch_id', sa.Integer(),
                  sa.ForeignKey('pitches.id', ondelete='SET NULL'),
                  nullable=True)
    )
    op.create_index('ix_instructor_positions_pitch_id',
                    'instructor_positions', ['pitch_id'])

    # ── 6. sport_director_assignments table ──────────────────────────────────
    op.create_table(
        'sport_director_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('location_id', sa.Integer(),
                  sa.ForeignKey('locations.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_by', sa.Integer(),
                  sa.ForeignKey('users.id'),
                  nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_sport_director_assignments_user_id',
                    'sport_director_assignments', ['user_id'])
    op.create_index('ix_sport_director_assignments_location_id',
                    'sport_director_assignments', ['location_id'])
    # 1 active sport director per location
    op.execute(
        """
        CREATE UNIQUE INDEX uq_sport_director_per_location
        ON sport_director_assignments(location_id)
        WHERE is_active = true
        """
    )

    # ── 7. pitch_instructor_assignments table ─────────────────────────────────
    op.create_table(
        'pitch_instructor_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column('pitch_id', sa.Integer(),
                  sa.ForeignKey('pitches.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('instructor_id', sa.Integer(),
                  sa.ForeignKey('users.id'),
                  nullable=False),
        sa.Column('semester_id', sa.Integer(),
                  sa.ForeignKey('semesters.id'),
                  nullable=True),
        sa.Column('is_master', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('assignment_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('required_license_type', sa.String(50), nullable=True),
        sa.Column('required_age_group', sa.String(20), nullable=True),
        sa.Column('assigned_by', sa.Integer(),
                  sa.ForeignKey('users.id'),
                  nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_pitch_instructor_assignments_pitch_id',
                    'pitch_instructor_assignments', ['pitch_id'])
    op.create_index('ix_pitch_instructor_assignments_instructor_id',
                    'pitch_instructor_assignments', ['instructor_id'])
    op.create_index('ix_pitch_instructor_assignments_semester_id',
                    'pitch_instructor_assignments', ['semester_id'])
    op.create_index('ix_pitch_instructor_assignments_status',
                    'pitch_instructor_assignments', ['status'])
    # 1 active master per pitch per semester
    op.execute(
        """
        CREATE UNIQUE INDEX uq_pitch_master_per_semester
        ON pitch_instructor_assignments(pitch_id, semester_id)
        WHERE is_master = true AND status = 'ACTIVE'
        """
    )


def downgrade() -> None:
    # Drop pitch_instructor_assignments
    op.drop_index('uq_pitch_master_per_semester', table_name='pitch_instructor_assignments')
    op.drop_index('ix_pitch_instructor_assignments_status', table_name='pitch_instructor_assignments')
    op.drop_index('ix_pitch_instructor_assignments_semester_id', table_name='pitch_instructor_assignments')
    op.drop_index('ix_pitch_instructor_assignments_instructor_id', table_name='pitch_instructor_assignments')
    op.drop_index('ix_pitch_instructor_assignments_pitch_id', table_name='pitch_instructor_assignments')
    op.drop_table('pitch_instructor_assignments')

    # Drop sport_director_assignments
    op.drop_index('uq_sport_director_per_location', table_name='sport_director_assignments')
    op.drop_index('ix_sport_director_assignments_location_id', table_name='sport_director_assignments')
    op.drop_index('ix_sport_director_assignments_user_id', table_name='sport_director_assignments')
    op.drop_table('sport_director_assignments')

    # Remove instructor_positions.pitch_id
    op.drop_index('ix_instructor_positions_pitch_id', table_name='instructor_positions')
    op.drop_column('instructor_positions', 'pitch_id')

    # Remove location_master_instructors.campus_id
    op.execute('DROP INDEX IF EXISTS uq_campus_master_active')
    op.drop_index('ix_location_master_instructors_campus_id',
                  table_name='location_master_instructors')
    op.drop_column('location_master_instructors', 'campus_id')

    # Remove sessions.pitch_id
    op.drop_index('ix_sessions_pitch_id', table_name='sessions')
    op.drop_column('sessions', 'pitch_id')

    # Drop pitches table
    op.drop_constraint('uq_campus_pitch_number', 'pitches', type_='unique')
    op.drop_index('ix_pitches_campus_id', table_name='pitches')
    op.drop_table('pitches')

    # Note: PostgreSQL does not support removing enum values.
    # The 'sport_director' value stays in the userrole enum after downgrade.
