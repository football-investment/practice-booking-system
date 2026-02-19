"""create_tracks_modules_tables

Revision ID: f1934c4aa75e
Revises: 85bb524bc878
Create Date: 2025-11-17 21:11:02.667760

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid


# revision identifiers, used by Alembic.
revision = 'f1934c4aa75e'
down_revision = 'add_fk_constraints'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tracks table
    op.create_table('tracks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('duration_semesters', sa.Integer, default=1),
        sa.Column('prerequisites', JSON, default=dict),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_tracks_code', 'tracks', ['code'])
    op.create_index('ix_tracks_is_active', 'tracks', ['is_active'])

    # Create modules table (with INTEGER semester_id)
    op.create_table('modules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('track_id', UUID(as_uuid=True), sa.ForeignKey('tracks.id'), nullable=False),
        sa.Column('semester_id', sa.Integer, sa.ForeignKey('semesters.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order_in_track', sa.Integer, default=0),
        sa.Column('learning_objectives', JSON, default=list),
        sa.Column('estimated_hours', sa.Integer, default=0),
        sa.Column('is_mandatory', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_modules_track_id', 'modules', ['track_id'])
    op.create_index('ix_modules_semester_id', 'modules', ['semester_id'])
    op.create_index('ix_modules_order', 'modules', ['order_in_track'])

    # Create module_components table
    op.create_table('module_components',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('module_id', UUID(as_uuid=True), sa.ForeignKey('modules.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('order_in_module', sa.Integer, default=0),
        sa.Column('estimated_minutes', sa.Integer, default=0),
        sa.Column('is_mandatory', sa.Boolean, default=True),
        sa.Column('component_data', JSON, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_module_components_module_id', 'module_components', ['module_id'])
    op.create_index('ix_module_components_type', 'module_components', ['type'])
    op.create_index('ix_module_components_order', 'module_components', ['order_in_module'])

    # Create certificate_templates table
    op.create_table('certificate_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('track_id', UUID(as_uuid=True), sa.ForeignKey('tracks.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('design_template', sa.Text),
        sa.Column('validation_rules', JSON, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )

    # Create issued_certificates table (with INTEGER user_id)
    op.create_table('issued_certificates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('certificate_template_id', UUID(as_uuid=True), sa.ForeignKey('certificate_templates.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('unique_identifier', sa.String(100), nullable=False, unique=True),
        sa.Column('issue_date', sa.DateTime, default=sa.func.now()),
        sa.Column('completion_date', sa.DateTime),
        sa.Column('verification_hash', sa.String(256), nullable=False),
        sa.Column('cert_metadata', JSON, default=dict),
        sa.Column('is_revoked', sa.Boolean, default=False),
        sa.Column('revoked_at', sa.DateTime),
        sa.Column('revoked_reason', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_issued_certificates_user_id', 'issued_certificates', ['user_id'])
    op.create_index('ix_issued_certificates_unique_id', 'issued_certificates', ['unique_identifier'])

    # Create user_track_progresses table (with INTEGER user_id)
    op.create_table('user_track_progresses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('track_id', UUID(as_uuid=True), sa.ForeignKey('tracks.id'), nullable=False),
        sa.Column('enrollment_date', sa.DateTime, default=sa.func.now()),
        sa.Column('current_semester', sa.Integer, default=1),
        sa.Column('status', sa.String(50), default='ENROLLED'),
        sa.Column('completion_percentage', sa.Float, default=0.0),
        sa.Column('certificate_id', UUID(as_uuid=True), sa.ForeignKey('issued_certificates.id'), nullable=True),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_user_track_progresses_user_id', 'user_track_progresses', ['user_id'])
    op.create_index('ix_user_track_progresses_track_id', 'user_track_progresses', ['track_id'])

    # Create user_module_progresses table
    op.create_table('user_module_progresses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_track_progress_id', UUID(as_uuid=True), sa.ForeignKey('user_track_progresses.id'), nullable=False),
        sa.Column('module_id', UUID(as_uuid=True), sa.ForeignKey('modules.id'), nullable=False),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('grade', sa.Float),
        sa.Column('status', sa.String(50), default='NOT_STARTED'),
        sa.Column('attempts', sa.Integer, default=0),
        sa.Column('time_spent_minutes', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    op.create_index('ix_user_module_progresses_track_progress_id', 'user_module_progresses', ['user_track_progress_id'])
    op.create_index('ix_user_module_progresses_module_id', 'user_module_progresses', ['module_id'])


def downgrade() -> None:
    op.drop_table('user_module_progresses')
    op.drop_table('user_track_progresses')
    op.drop_table('issued_certificates')
    op.drop_table('certificate_templates')
    op.drop_table('module_components')
    op.drop_table('modules')
    op.drop_table('tracks')
