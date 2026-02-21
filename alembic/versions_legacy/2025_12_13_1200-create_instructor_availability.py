"""create_instructor_specialization_availability_table

Revision ID: 4da8caa1e3d0
Revises: ff330f866c45
Create Date: 2025-12-13 12:00:00.000000

Allows instructors (especially Grandmasters) to choose:
- Which time periods they want to work (Q1, Q2, Q3, Q4 or M01-M12)
- Which age groups they want to teach (PRE, YOUTH, AMATEUR, PRO)

Example use case:
- Grandmaster has licenses for all 4 age groups
- But only wants to teach PRE and YOUTH in Q3
- Can deactivate AMATEUR and PRO for Q3 period
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4da8caa1e3d0'
down_revision = 'ff330f866c45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create instructor_specialization_availability table
    op.create_table(
        'instructor_specialization_availability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False, comment='Instructor who sets this availability preference'),
        sa.Column('specialization_type', sa.String(length=50), nullable=False, comment='LFA_PLAYER_PRE, LFA_PLAYER_YOUTH, LFA_PLAYER_AMATEUR, LFA_PLAYER_PRO'),
        sa.Column('time_period_code', sa.String(length=10), nullable=False, comment='Q1-Q4 for quarterly, M01-M12 for monthly'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Year for which this availability applies (e.g., 2025)'),
        sa.Column('location_city', sa.String(length=100), nullable=True, comment='City where this availability applies (e.g., Budapest, Budaörs)'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true', comment='True if instructor is available for this specialization in this time period'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True, comment='Optional notes from instructor about this availability'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),

        # Unique constraint: prevent duplicate entries
        sa.UniqueConstraint(
            'instructor_id', 'specialization_type', 'time_period_code', 'year', 'location_city',
            name='uix_instructor_spec_period_year_location'
        ),

        # Check constraints
        sa.CheckConstraint(
            "time_period_code ~ '^(Q[1-4]|M(0[1-9]|1[0-2]))$'",
            name='check_time_period_code_format'
        ),
        sa.CheckConstraint(
            "year >= 2024 AND year <= 2100",
            name='check_year_range'
        )
    )

    # Create indexes for common queries
    op.create_index('ix_instructor_avail_instructor_id', 'instructor_specialization_availability', ['instructor_id'])
    op.create_index('ix_instructor_avail_year', 'instructor_specialization_availability', ['year'])
    op.create_index('ix_instructor_avail_spec_type', 'instructor_specialization_availability', ['specialization_type'])
    op.create_index('ix_instructor_avail_location', 'instructor_specialization_availability', ['location_city'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_instructor_avail_location', table_name='instructor_specialization_availability')
    op.drop_index('ix_instructor_avail_spec_type', table_name='instructor_specialization_availability')
    op.drop_index('ix_instructor_avail_year', table_name='instructor_specialization_availability')
    op.drop_index('ix_instructor_avail_instructor_id', table_name='instructor_specialization_availability')

    # Drop table
    op.drop_table('instructor_specialization_availability')
