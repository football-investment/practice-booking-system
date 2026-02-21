"""create_invoice_requests_table

Revision ID: f9b40d8e300b
Revises: a3fb1e8db7c8
Create Date: 2025-12-03 18:46:50.739814

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9b40d8e300b'
down_revision = 'a3fb1e8db7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create invoice_request_status enum (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoicerequeststatus') THEN
                CREATE TYPE invoicerequeststatus AS ENUM ('pending', 'paid', 'verified', 'cancelled');
            END IF;
        END
        $$;
    """)

    # Create invoice_requests table
    op.execute("""
        CREATE TABLE invoice_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            payment_reference VARCHAR(100) NOT NULL UNIQUE,
            amount_eur FLOAT NOT NULL,
            credit_amount INTEGER NOT NULL,
            specialization VARCHAR(50),
            status invoicerequeststatus NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            paid_at TIMESTAMPTZ,
            verified_at TIMESTAMPTZ
        );

        COMMENT ON COLUMN invoice_requests.payment_reference IS 'Unique payment reference: INV-YYYYMMDD-HHMMSS-ID-HASH';
        COMMENT ON COLUMN invoice_requests.amount_eur IS 'Amount in EUR';
        COMMENT ON COLUMN invoice_requests.credit_amount IS 'Credit amount';
        COMMENT ON COLUMN invoice_requests.specialization IS 'Specialization type';
        COMMENT ON COLUMN invoice_requests.paid_at IS 'When payment was made';
        COMMENT ON COLUMN invoice_requests.verified_at IS 'When admin verified payment';
    """)

    # Create indexes
    op.create_index('ix_invoice_requests_id', 'invoice_requests', ['id'], unique=False)
    op.create_index('ix_invoice_requests_payment_reference', 'invoice_requests', ['payment_reference'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_invoice_requests_payment_reference', table_name='invoice_requests')
    op.drop_index('ix_invoice_requests_id', table_name='invoice_requests')

    # Drop table
    op.drop_table('invoice_requests')

    # Drop enum
    op.execute("DROP TYPE invoicerequeststatus;")