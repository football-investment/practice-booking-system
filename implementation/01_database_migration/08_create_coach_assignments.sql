-- =====================================================
-- COACH ASSIGNMENTS TABLE
-- =====================================================
-- Purpose: Links Coach licenses to semesters (as instructors)
-- Key Features:
--   - Tracks which coaches are assigned to teach in which semesters
--   - One active assignment per license per semester
--   - Auto-cascade cleanup on license/semester deletion
--   - NO payment fields (coaches get paid, not charge)
--   - Audit trail (created_at, updated_at)
-- =====================================================

-- Drop existing table and triggers if they exist
DROP TRIGGER IF EXISTS trg_coach_assignments_updated_at ON coach_assignments CASCADE;
DROP FUNCTION IF EXISTS update_coach_assignment_timestamp() CASCADE;
DROP TABLE IF EXISTS coach_assignments CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE coach_assignments (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    license_id INTEGER NOT NULL REFERENCES coach_licenses(id) ON DELETE CASCADE,
    semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,

    -- Assignment Details
    assignment_role VARCHAR(50) DEFAULT 'INSTRUCTOR' CHECK (assignment_role IN ('INSTRUCTOR', 'ASSISTANT', 'MENTOR')),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Unique active assignment per license per semester
CREATE UNIQUE INDEX idx_coach_assignments_unique_active
ON coach_assignments(license_id, semester_id)
WHERE is_active = TRUE;

-- Fast lookup by license
CREATE INDEX idx_coach_assignments_license
ON coach_assignments(license_id);

-- Fast lookup by semester
CREATE INDEX idx_coach_assignments_semester
ON coach_assignments(semester_id);

-- Fast lookup by role
CREATE INDEX idx_coach_assignments_role
ON coach_assignments(assignment_role)
WHERE is_active = TRUE;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_coach_assignment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coach_assignments_updated_at
BEFORE UPDATE ON coach_assignments
FOR EACH ROW
EXECUTE FUNCTION update_coach_assignment_timestamp();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE coach_assignments IS 'Coach teaching assignments for semesters';
COMMENT ON COLUMN coach_assignments.license_id IS 'Foreign key to coach_licenses';
COMMENT ON COLUMN coach_assignments.semester_id IS 'Foreign key to semesters';
COMMENT ON COLUMN coach_assignments.assignment_role IS 'Role: INSTRUCTOR (main teacher), ASSISTANT (helper), MENTOR (advisor)';
COMMENT ON COLUMN coach_assignments.is_active IS 'Whether this assignment is currently active';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ coach_assignments table created successfully!';
    RAISE NOTICE '   - UNIQUE constraint: One active assignment per license per semester';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on license/semester deletion';
    RAISE NOTICE '   - Trigger: Auto-update updated_at';
    RAISE NOTICE '   - Indexes: license_id, semester_id, assignment_role';
    RAISE NOTICE '   - NOTE: NO payment fields (coaches get paid, not charge)';
END $$;
