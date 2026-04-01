-- =====================================================
-- GANCUJU ENROLLMENTS TABLE
-- =====================================================
-- Purpose: Links GānCuju licenses to semesters
-- Key Features:
--   - Payment verification tracking
--   - One active enrollment per license per semester
--   - Auto-cascade cleanup on license/semester deletion
--   - Audit trail (created_at, updated_at)
-- =====================================================

-- Drop existing table and triggers if they exist
DROP TRIGGER IF EXISTS trg_gancuju_enrollments_updated_at ON gancuju_enrollments CASCADE;
DROP FUNCTION IF EXISTS update_gancuju_enrollment_timestamp() CASCADE;
DROP TABLE IF EXISTS gancuju_enrollments CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE gancuju_enrollments (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    license_id INTEGER NOT NULL REFERENCES gancuju_licenses(id) ON DELETE CASCADE,
    semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,

    -- Payment Information
    payment_verified BOOLEAN DEFAULT FALSE,
    payment_proof_url TEXT,
    payment_reference_code VARCHAR(50),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_gancuju_enrollments_payment_proof CHECK (
        payment_proof_url IS NULL OR payment_proof_url ~ '^https?://'
    ),
    CONSTRAINT chk_gancuju_enrollments_payment_ref CHECK (
        payment_reference_code IS NULL OR LENGTH(payment_reference_code) >= 3
    )
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Unique active enrollment per license per semester
CREATE UNIQUE INDEX idx_gancuju_enrollments_unique_active
ON gancuju_enrollments(license_id, semester_id)
WHERE is_active = TRUE;

-- Fast lookup by license
CREATE INDEX idx_gancuju_enrollments_license
ON gancuju_enrollments(license_id);

-- Fast lookup by semester
CREATE INDEX idx_gancuju_enrollments_semester
ON gancuju_enrollments(semester_id);

-- Fast lookup of verified enrollments
CREATE INDEX idx_gancuju_enrollments_verified
ON gancuju_enrollments(payment_verified)
WHERE payment_verified = TRUE AND is_active = TRUE;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_gancuju_enrollment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gancuju_enrollments_updated_at
BEFORE UPDATE ON gancuju_enrollments
FOR EACH ROW
EXECUTE FUNCTION update_gancuju_enrollment_timestamp();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE gancuju_enrollments IS 'GānCuju enrollments in semesters';
COMMENT ON COLUMN gancuju_enrollments.license_id IS 'Foreign key to gancuju_licenses';
COMMENT ON COLUMN gancuju_enrollments.semester_id IS 'Foreign key to semesters';
COMMENT ON COLUMN gancuju_enrollments.payment_verified IS 'Whether payment has been verified by admin';
COMMENT ON COLUMN gancuju_enrollments.payment_proof_url IS 'URL to payment proof document/screenshot';
COMMENT ON COLUMN gancuju_enrollments.payment_reference_code IS 'Bank transfer reference code';
COMMENT ON COLUMN gancuju_enrollments.is_active IS 'Whether this enrollment is currently active';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ gancuju_enrollments table created successfully!';
    RAISE NOTICE '   - UNIQUE constraint: One active enrollment per license per semester';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on license/semester deletion';
    RAISE NOTICE '   - Trigger: Auto-update updated_at';
    RAISE NOTICE '   - Indexes: license_id, semester_id, payment_verified';
END $$;
