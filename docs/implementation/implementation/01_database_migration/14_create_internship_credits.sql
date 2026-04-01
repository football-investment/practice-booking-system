-- =====================================================
-- INTERNSHIP CREDIT TRANSACTIONS TABLE
-- =====================================================
-- Purpose: Tracks credit purchases and usage for Interns
-- Key Features:
--   - Transaction types: PURCHASE, SPENT, REFUND
--   - Tracks credit amount changes (+/-)
--   - Links to license (not directly to user)
--   - References to enrollments when credits are spent
--   - Payment verification for purchases
--   - Audit trail (created_at)
-- =====================================================

-- Drop existing table if exists
DROP TABLE IF EXISTS internship_credit_transactions CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE internship_credit_transactions (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    license_id INTEGER NOT NULL REFERENCES internship_licenses(id) ON DELETE CASCADE,
    enrollment_id INTEGER REFERENCES internship_enrollments(id) ON DELETE SET NULL,  -- NULL for purchases

    -- Transaction Details
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('PURCHASE', 'SPENT', 'REFUND')),
    amount INTEGER NOT NULL CHECK (amount != 0),  -- Positive for PURCHASE/REFUND, negative for SPENT

    -- Payment Information (for PURCHASE transactions)
    payment_verified BOOLEAN DEFAULT FALSE,
    payment_proof_url TEXT,
    payment_reference_code VARCHAR(50),

    -- Description
    description TEXT,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_internship_credits_purchase_amount CHECK (
        (transaction_type = 'PURCHASE' AND amount > 0) OR
        (transaction_type = 'SPENT' AND amount < 0) OR
        (transaction_type = 'REFUND' AND amount > 0)
    ),
    CONSTRAINT chk_internship_credits_spent_enrollment CHECK (
        (transaction_type = 'SPENT' AND enrollment_id IS NOT NULL) OR
        (transaction_type != 'SPENT')
    ),
    CONSTRAINT chk_internship_credits_payment_proof CHECK (
        payment_proof_url IS NULL OR payment_proof_url ~ '^https?://'
    )
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Fast lookup by license
CREATE INDEX idx_internship_credits_license
ON internship_credit_transactions(license_id);

-- Fast lookup by enrollment
CREATE INDEX idx_internship_credits_enrollment
ON internship_credit_transactions(enrollment_id)
WHERE enrollment_id IS NOT NULL;

-- Fast lookup by transaction type
CREATE INDEX idx_internship_credits_type
ON internship_credit_transactions(transaction_type);

-- Fast lookup by date
CREATE INDEX idx_internship_credits_date
ON internship_credit_transactions(created_at DESC);

-- Fast lookup of purchases awaiting verification
CREATE INDEX idx_internship_credits_pending_verification
ON internship_credit_transactions(payment_verified, created_at)
WHERE transaction_type = 'PURCHASE' AND payment_verified = FALSE;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE internship_credit_transactions IS 'Credit transaction history for Interns';
COMMENT ON COLUMN internship_credit_transactions.license_id IS 'Foreign key to internship_licenses';
COMMENT ON COLUMN internship_credit_transactions.enrollment_id IS 'Foreign key to internship_enrollments (for SPENT transactions)';
COMMENT ON COLUMN internship_credit_transactions.transaction_type IS 'PURCHASE (buy credits), SPENT (use credits), REFUND (return credits)';
COMMENT ON COLUMN internship_credit_transactions.amount IS 'Credit amount: positive for PURCHASE/REFUND, negative for SPENT';
COMMENT ON COLUMN internship_credit_transactions.payment_verified IS 'Whether payment has been verified by admin (for PURCHASE)';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ internship_credit_transactions table created successfully!';
    RAISE NOTICE '   - Transaction types: PURCHASE (buy), SPENT (use), REFUND (return)';
    RAISE NOTICE '   - Amount: positive for PURCHASE/REFUND, negative for SPENT';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on license deletion';
    RAISE NOTICE '   - SET NULL: enrollment_id preserved even if enrollment deleted';
    RAISE NOTICE '   - Indexes: license_id, enrollment_id, transaction_type, created_at';
    RAISE NOTICE '   - CHECK: SPENT transactions require enrollment_id';
END $$;
