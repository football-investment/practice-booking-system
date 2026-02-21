"""add master hiring pathways

Revision ID: 2025_12_23_1900
Revises: 2025_12_21_1600
Create Date: 2025-12-23 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_12_23_1900'
down_revision = '7a8b9c0d1e2f'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create MasterOfferStatus enum
    master_offer_status = postgresql.ENUM(
        'OFFERED', 'ACCEPTED', 'DECLINED', 'EXPIRED',
        name='masterofferstatus',
        create_type=True
    )
    master_offer_status.create(op.get_bind(), checkfirst=True)

    # 2. Add fields to location_master_instructors table
    op.add_column('location_master_instructors',
        sa.Column('offer_status',
                  sa.Enum('OFFERED', 'ACCEPTED', 'DECLINED', 'EXPIRED',
                         name='masterofferstatus'),
                  nullable=True,
                  comment='Offer workflow status: NULL=legacy, OFFERED=pending, ACCEPTED=active, DECLINED/EXPIRED=rejected'))

    op.add_column('location_master_instructors',
        sa.Column('offered_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When offer was sent to instructor'))

    op.add_column('location_master_instructors',
        sa.Column('offer_deadline', sa.DateTime(timezone=True), nullable=True,
                  comment='Deadline for instructor to accept/decline offer'))

    op.add_column('location_master_instructors',
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When instructor accepted the offer'))

    op.add_column('location_master_instructors',
        sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True,
                  comment='When instructor declined or offer expired'))

    op.add_column('location_master_instructors',
        sa.Column('hiring_pathway', sa.String(20), nullable=False,
                  server_default='DIRECT',
                  comment='Hiring method: DIRECT or JOB_POSTING'))

    op.add_column('location_master_instructors',
        sa.Column('source_position_id', sa.Integer(), nullable=True,
                  comment='Links to job posting if hired via JOB_POSTING pathway'))

    op.add_column('location_master_instructors',
        sa.Column('availability_override', sa.Boolean(), nullable=False,
                  server_default='false',
                  comment='True if admin sent offer despite availability mismatch'))

    # 3. Add foreign key for source_position_id
    op.create_foreign_key(
        'fk_master_source_position',
        'location_master_instructors',
        'instructor_positions',
        ['source_position_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 4. Add is_master_position to instructor_positions table
    op.add_column('instructor_positions',
        sa.Column('is_master_position', sa.Boolean(), nullable=False,
                  server_default='false',
                  comment='True if this is a master instructor opening, False for assistant positions'))

    # 5. Create indexes for performance
    op.create_index(
        'idx_offers_pending',
        'location_master_instructors',
        ['offer_status'],
        unique=False,
        postgresql_where=sa.text("offer_status = 'OFFERED'")
    )

    op.create_index(
        'idx_positions_master',
        'instructor_positions',
        ['is_master_position'],
        unique=False
    )

    # 6. Data migration: Existing contracts remain as legacy (offer_status=NULL, is_active=True)
    # No action needed - NULL offer_status indicates legacy immediate-active contracts


def downgrade():
    # Remove in reverse order
    op.drop_index('idx_positions_master', table_name='instructor_positions')
    op.drop_index('idx_offers_pending', table_name='location_master_instructors')

    op.drop_column('instructor_positions', 'is_master_position')

    op.drop_constraint('fk_master_source_position', 'location_master_instructors', type_='foreignkey')

    op.drop_column('location_master_instructors', 'availability_override')
    op.drop_column('location_master_instructors', 'source_position_id')
    op.drop_column('location_master_instructors', 'hiring_pathway')
    op.drop_column('location_master_instructors', 'declined_at')
    op.drop_column('location_master_instructors', 'accepted_at')
    op.drop_column('location_master_instructors', 'offer_deadline')
    op.drop_column('location_master_instructors', 'offered_at')
    op.drop_column('location_master_instructors', 'offer_status')

    # Drop enum type
    sa.Enum(name='masterofferstatus').drop(op.get_bind(), checkfirst=True)
