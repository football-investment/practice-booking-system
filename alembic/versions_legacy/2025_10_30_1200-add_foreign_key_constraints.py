"""Add foreign key constraints for data integrity

Revision ID: add_fk_constraints
Revises: fix_internship_levels
Create Date: 2025-10-30 12:00:00.000000

P1 TASK: Add foreign key constraints to prevent orphan records

Tables affected:
- specialization_progress: FK to users and specializations
- user_licenses: FK to users and specializations

Constraints:
- ON DELETE RESTRICT: Prevents deletion of referenced records
- Ensures referential integrity
- No orphan progress/license records possible

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_fk_constraints'
down_revision = 'fix_internship_levels'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add foreign key constraints for referential integrity.

    This prevents:
    - Progress records for deleted users
    - Progress records for non-existent specializations
    - License records for deleted users
    - License records for non-existent specializations
    """

    # specialization_progress.student_id → users.id
    # Check if constraint already exists (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('specialization_progress')]

    if 'fk_specialization_progress_user' not in existing_fks:
        op.create_foreign_key(
            'fk_specialization_progress_user',
            'specialization_progress',
            'users',
            ['student_id'],
            ['id'],
            ondelete='RESTRICT'  # Prevent user deletion if they have progress
        )

    # specialization_progress.specialization_id → specializations.id
    if 'fk_specialization_progress_spec' not in existing_fks:
        op.create_foreign_key(
            'fk_specialization_progress_spec',
            'specialization_progress',
            'specializations',
            ['specialization_id'],
            ['id'],
            ondelete='RESTRICT'  # Prevent specialization deletion if in use
        )

    # user_licenses.user_id → users.id
    existing_license_fks = [fk['name'] for fk in inspector.get_foreign_keys('user_licenses')]

    if 'fk_user_licenses_user' not in existing_license_fks:
        op.create_foreign_key(
            'fk_user_licenses_user',
            'user_licenses',
            'users',
            ['user_id'],
            ['id'],
            ondelete='RESTRICT'  # Prevent user deletion if they have licenses
        )

    # user_licenses.specialization_type → specializations.id
    if 'fk_user_licenses_spec' not in existing_license_fks:
        op.create_foreign_key(
            'fk_user_licenses_spec',
            'user_licenses',
            'specializations',
            ['specialization_type'],
            ['id'],
            ondelete='RESTRICT'  # Prevent specialization deletion if licensed
        )

    # Add table comments for clarity
    op.execute("""
        COMMENT ON TABLE specialization_progress IS
        'Student progress tracking with FK constraints.
         Cannot delete users or specializations with active progress.
         P1: Added referential integrity constraints.';
    """)

    op.execute("""
        COMMENT ON TABLE user_licenses IS
        'User license records with FK constraints.
         Cannot delete users or specializations with active licenses.
         P1: Added referential integrity constraints.';
    """)


def downgrade():
    """
    Remove foreign key constraints.

    WARNING: This reduces data integrity protection!
    Only use for rollback purposes.
    """

    op.drop_constraint('fk_user_licenses_spec', 'user_licenses', type_='foreignkey')
    op.drop_constraint('fk_user_licenses_user', 'user_licenses', type_='foreignkey')
    op.drop_constraint('fk_specialization_progress_spec', 'specialization_progress', type_='foreignkey')
    op.drop_constraint('fk_specialization_progress_user', 'specialization_progress', type_='foreignkey')

    # Remove comments
    op.execute("COMMENT ON TABLE specialization_progress IS NULL;")
    op.execute("COMMENT ON TABLE user_licenses IS NULL;")
