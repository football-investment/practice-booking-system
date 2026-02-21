"""cleanup specializations table for hybrid architecture

Revision ID: cleanup_spec_hybrid
Revises: 2025_11_18_1240
Create Date: 2025-11-18 14:36:00

HYBRID ARCHITECTURE CLEANUP:
- Remove redundant columns: name, description, icon, max_levels
- Keep only: id (PK), is_active, created_at
- JSON configs are now Source of Truth for content
- DB maintains only referential integrity

SAFE TO RUN:
✅ Service layer uses JSON (not DB columns)
✅ API uses service layer (not direct DB)
✅ All tests passing (9/9)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'cleanup_spec_hybrid'
down_revision = 'rename_specializations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Remove redundant columns from specializations table.

    HYBRID ARCHITECTURE:
    - DB: id (PK), is_active (availability), created_at (audit)
    - JSON: name, description, icon, levels, features (content)
    """

    # Ensure is_active has proper default and NOT NULL
    op.execute("UPDATE specializations SET is_active = TRUE WHERE is_active IS NULL")
    op.alter_column('specializations', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default='true')

    # Ensure created_at has values
    op.execute(f"UPDATE specializations SET created_at = '{datetime.utcnow()}' WHERE created_at IS NULL")
    op.alter_column('specializations', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))

    # Drop redundant columns (JSON is Source of Truth)
    op.drop_column('specializations', 'max_levels')
    op.drop_column('specializations', 'description')
    op.drop_column('specializations', 'icon')
    op.drop_column('specializations', 'name')


def downgrade() -> None:
    """
    Restore columns from JSON configs.

    ROLLBACK STRATEGY:
    - Re-add columns
    - Populate from JSON configs via SpecializationConfigLoader
    """
    from app.models.specialization import SpecializationType
    from app.services.specialization_config_loader import SpecializationConfigLoader

    # Re-add columns
    op.add_column('specializations', sa.Column('name', sa.String(100), nullable=True))
    op.add_column('specializations', sa.Column('icon', sa.String(10), nullable=True))
    op.add_column('specializations', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('specializations', sa.Column('max_levels', sa.Integer(), nullable=True))

    # Populate from JSON configs
    loader = SpecializationConfigLoader()

    for spec_enum in SpecializationType:
        spec_id = spec_enum.value

        try:
            # Load display info and max level from JSON
            display_info = loader.get_display_info(spec_enum)
            max_level = loader.get_max_level(spec_enum)

            # Update DB with JSON data
            op.execute(f"""
                UPDATE specializations
                SET
                    name = '{display_info.get('name', spec_id)}',
                    icon = '{display_info.get('icon', '🎯')}',
                    description = '{display_info.get('description', '').replace("'", "''")}',
                    max_levels = {max_level}
                WHERE id = '{spec_id}'
            """)
        except Exception as e:
            print(f"Warning: Could not populate {spec_id} from JSON: {e}")
            # Set defaults if JSON load fails
            op.execute(f"""
                UPDATE specializations
                SET
                    name = '{spec_id}',
                    icon = '🎯',
                    description = '',
                    max_levels = 8
                WHERE id = '{spec_id}'
            """)

    # Make columns NOT NULL after populating
    op.alter_column('specializations', 'name', nullable=False)
    op.alter_column('specializations', 'max_levels', nullable=False)
