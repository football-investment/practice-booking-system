"""create semester enrollments table

Revision ID: create_semester_enrollments
Revises: add_onboarding_motivation
Create Date: 2025-11-28 10:30:00.000000

🎯 PURPOSE:
- Track which specializations a student is enrolled in per semester
- Enable payment verification per-semester-per-specialization
- Allow students to have different specialization portfolios across semesters
- Preserve UserLicense data even when not actively enrolled

📊 BUSINESS LOGIC:
Example: Student Journey
- Semester 1: Enrolled in 4 specs (GANCUJU_PLAYER, LFA_PLAYER, LFA_COACH, INTERNSHIP) → 4 enrollments
- Semester 2: Only paid for 2 specs (GANCUJU_PLAYER, INTERNSHIP) → 2 new enrollments
- Semester 3: Paid for 3 specs (GANCUJU_PLAYER, LFA_PLAYER, LFA_COACH) → 3 new enrollments
- UserLicense data remains intact across all semesters
- Student can always switch between specs, but booking/session access requires active enrollment

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_semester_enrollments'
down_revision = 'add_onboarding_motivation'
branch_labels = None
depends_on = None


def upgrade():
    """Create semester_enrollments table"""

    op.create_table(
        'semester_enrollments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='Student who is enrolled'),
        sa.Column('semester_id', sa.Integer(), nullable=False, comment='Semester for this enrollment'),
        sa.Column('user_license_id', sa.Integer(), nullable=False, comment='Link to the UserLicense (tracks progress/levels)'),

        # Payment tracking (per-semester-per-specialization)
        sa.Column('payment_verified', sa.Boolean(), nullable=False, default=False,
                  comment='Whether student paid for THIS specialization in THIS semester'),
        sa.Column('payment_verified_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When payment was verified'),
        sa.Column('payment_verified_by', sa.Integer(), nullable=True,
                  comment='Admin user who verified payment'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True,
                  comment='Whether this enrollment is currently active'),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP'),
                  comment='When student enrolled in this spec for this semester'),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When enrollment was deactivated (if applicable)'),

        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),

        # Primary Key
        sa.PrimaryKeyConstraint('id'),

        # Foreign Keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_semester_enrollments_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], name='fk_semester_enrollments_semester_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_license_id'], ['user_licenses.id'], name='fk_semester_enrollments_user_license_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_verified_by'], ['users.id'], name='fk_semester_enrollments_payment_verified_by', ondelete='SET NULL'),

        # Indexes for performance
        sa.Index('ix_semester_enrollments_user_id', 'user_id'),
        sa.Index('ix_semester_enrollments_semester_id', 'semester_id'),
        sa.Index('ix_semester_enrollments_user_license_id', 'user_license_id'),
        sa.Index('ix_semester_enrollments_payment_verified', 'payment_verified'),
        sa.Index('ix_semester_enrollments_is_active', 'is_active'),

        # Unique constraint: One enrollment per user per semester per user_license
        sa.UniqueConstraint('user_id', 'semester_id', 'user_license_id',
                           name='uq_semester_enrollments_user_semester_license')
    )

    print("✅ Created semester_enrollments table")


def downgrade():
    """Drop semester_enrollments table"""
    op.drop_table('semester_enrollments')
    print("❌ Dropped semester_enrollments table")
