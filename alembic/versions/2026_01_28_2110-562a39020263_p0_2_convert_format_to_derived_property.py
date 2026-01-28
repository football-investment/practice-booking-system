"""p0_2_convert_format_to_derived_property

Revision ID: 562a39020263
Revises: cac420a0d9b1
Create Date: 2026-01-28 21:10:48.785163

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '562a39020263'
down_revision = 'cac420a0d9b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    P0.2: Convert format from stored column to derived property

    Format is now derived from tournament_type.format (FK relationship).
    This eliminates redundancy and ensures single source of truth.

    Data safety: All format values are consistent with tournament_type.format.
    Verified 63 records, 0 mismatches.
    """
    # Drop format column (will become @property in Semester model)
    op.drop_column('semesters', 'format')


def downgrade() -> None:
    """
    Restore format column and re-populate from tournament_type.format
    """
    # Add format column back
    op.add_column('semesters', sa.Column('format', sa.String(50), nullable=False, server_default='INDIVIDUAL_RANKING'))

    # Re-populate format from tournament_type (for existing records with FK)
    op.execute("""
        UPDATE semesters s
        SET format = tt.format
        FROM tournament_types tt
        WHERE s.tournament_type_id = tt.id
    """)