"""add_tournament_explicit_attributes

Revision ID: 78502c79192c
Revises: 71aab5034cd9
Create Date: 2026-01-12 09:36:02.677471

DOMAIN GAP RESOLUTION - Phase 1: Database Schema
================================================

Adds explicit business attributes to tournaments (semesters table):
1. assignment_type - Tournament instructor assignment strategy (OPEN_ASSIGNMENT | APPLICATION_BASED)
2. max_players - Explicit tournament player capacity (independent of session capacity)

Business Impact:
- Enables auditable assignment strategy decisions
- Enables explicit capacity management
- Unblocks waitlist feature development
- Enables strategy-specific validation rules

See: docs/architecture/TOURNAMENT_DOMAIN_GAP.md
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78502c79192c'
down_revision = '71aab5034cd9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================================
    # Add assignment_type column
    # ========================================================================
    op.add_column(
        'semesters',
        sa.Column(
            'assignment_type',
            sa.String(length=30),
            nullable=True,  # Initially nullable for backfill
            comment='Tournament instructor assignment strategy'
        )
    )

    # Add CHECK constraint for valid assignment types
    op.create_check_constraint(
        'valid_assignment_type',
        'semesters',
        "assignment_type IN ('OPEN_ASSIGNMENT', 'APPLICATION_BASED') OR assignment_type IS NULL"
    )

    # ========================================================================
    # Backfill assignment_type based on master_instructor_id
    # ========================================================================
    # OPEN_ASSIGNMENT: Instructor was directly assigned (master_instructor_id NOT NULL)
    # APPLICATION_BASED: Instructor applies (master_instructor_id NULL initially)

    # Only backfill for tournaments (specialization_type contains 'PLAYER')
    op.execute("""
        UPDATE semesters
        SET assignment_type = CASE
            WHEN master_instructor_id IS NOT NULL THEN 'OPEN_ASSIGNMENT'
            ELSE 'APPLICATION_BASED'
        END
        WHERE specialization_type LIKE '%PLAYER%'
          AND tournament_status IS NOT NULL
    """)

    # ========================================================================
    # Add max_players column
    # ========================================================================
    op.add_column(
        'semesters',
        sa.Column(
            'max_players',
            sa.Integer(),
            nullable=True,  # Initially nullable for backfill
            comment='Maximum tournament participants (explicit capacity)'
        )
    )

    # Add CHECK constraint for positive max_players
    op.create_check_constraint(
        'positive_max_players',
        'semesters',
        'max_players > 0 OR max_players IS NULL'
    )

    # ========================================================================
    # Backfill max_players from session capacity sum
    # ========================================================================
    # For existing tournaments, calculate max_players as SUM(session.capacity)
    op.execute("""
        UPDATE semesters
        SET max_players = (
            SELECT COALESCE(SUM(capacity), 20)
            FROM sessions
            WHERE sessions.semester_id = semesters.id
        )
        WHERE specialization_type LIKE '%PLAYER%'
          AND tournament_status IS NOT NULL
    """)

    # ========================================================================
    # Add constraint: assignment_type + instructor_id consistency
    # ========================================================================
    # OPEN_ASSIGNMENT requires instructor, APPLICATION_BASED does not
    op.create_check_constraint(
        'valid_assignment_type_instructor',
        'semesters',
        """
        (assignment_type IS NULL) OR
        (assignment_type = 'OPEN_ASSIGNMENT' AND master_instructor_id IS NOT NULL) OR
        (assignment_type = 'APPLICATION_BASED' AND (
            master_instructor_id IS NULL OR
            tournament_status IN ('PENDING_INSTRUCTOR_ACCEPTANCE', 'READY_FOR_ENROLLMENT', 'OPEN_FOR_ENROLLMENT', 'CLOSED', 'COMPLETED')
        ))
        """
    )

    # ========================================================================
    # Make columns NOT NULL after backfill (for tournaments only)
    # ========================================================================
    # Note: We keep them nullable for non-tournament semesters
    # Future constraint: assignment_type required when creating tournaments


def downgrade() -> None:
    # Remove constraints first
    op.drop_constraint('valid_assignment_type_instructor', 'semesters', type_='check')
    op.drop_constraint('positive_max_players', 'semesters', type_='check')
    op.drop_constraint('valid_assignment_type', 'semesters', type_='check')

    # Remove columns
    op.drop_column('semesters', 'max_players')
    op.drop_column('semesters', 'assignment_type')