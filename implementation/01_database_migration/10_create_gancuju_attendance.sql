-- =====================================================
-- GANCUJU ATTENDANCE TABLE
-- =====================================================
-- Purpose: Tracks GānCuju attendance in sessions
-- Key Features:
--   - Tracks attendance status (PRESENT, ABSENT, LATE, EXCUSED)
--   - Links to enrollments (not directly to licenses)
--   - Auto-cascade cleanup on enrollment/session deletion
--   - Audit trail (created_at, updated_at)
-- =====================================================

-- Drop existing table and triggers if they exist
DROP TRIGGER IF EXISTS trg_gancuju_attendance_updated_at ON gancuju_attendance CASCADE;
DROP FUNCTION IF EXISTS update_gancuju_attendance_timestamp() CASCADE;
DROP TABLE IF EXISTS gancuju_attendance CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE gancuju_attendance (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    enrollment_id INTEGER NOT NULL REFERENCES gancuju_enrollments(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Attendance Details
    status VARCHAR(20) NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')) DEFAULT 'ABSENT',
    checked_in_at TIMESTAMP WITH TIME ZONE,
    checked_in_by INTEGER REFERENCES users(id),  -- Admin/instructor who marked attendance

    -- Notes
    notes TEXT,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_gancuju_attendance_checkin CHECK (
        (status = 'PRESENT' AND checked_in_at IS NOT NULL) OR
        (status != 'PRESENT')
    )
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Unique attendance record per enrollment per session
CREATE UNIQUE INDEX idx_gancuju_attendance_unique
ON gancuju_attendance(enrollment_id, session_id);

-- Fast lookup by enrollment
CREATE INDEX idx_gancuju_attendance_enrollment
ON gancuju_attendance(enrollment_id);

-- Fast lookup by session
CREATE INDEX idx_gancuju_attendance_session
ON gancuju_attendance(session_id);

-- Fast lookup by status
CREATE INDEX idx_gancuju_attendance_status
ON gancuju_attendance(status);

-- Fast lookup of present attendances
CREATE INDEX idx_gancuju_attendance_present
ON gancuju_attendance(enrollment_id, status)
WHERE status = 'PRESENT';

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_gancuju_attendance_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gancuju_attendance_updated_at
BEFORE UPDATE ON gancuju_attendance
FOR EACH ROW
EXECUTE FUNCTION update_gancuju_attendance_timestamp();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE gancuju_attendance IS 'GānCuju attendance records for sessions';
COMMENT ON COLUMN gancuju_attendance.enrollment_id IS 'Foreign key to gancuju_enrollments';
COMMENT ON COLUMN gancuju_attendance.session_id IS 'Foreign key to sessions';
COMMENT ON COLUMN gancuju_attendance.status IS 'Attendance status: PRESENT, ABSENT, LATE, EXCUSED';
COMMENT ON COLUMN gancuju_attendance.checked_in_at IS 'Timestamp when participant checked in (for PRESENT status)';
COMMENT ON COLUMN gancuju_attendance.checked_in_by IS 'User ID of admin/instructor who marked attendance';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ gancuju_attendance table created successfully!';
    RAISE NOTICE '   - UNIQUE constraint: One attendance record per enrollment per session';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on enrollment/session deletion';
    RAISE NOTICE '   - Trigger: Auto-update updated_at';
    RAISE NOTICE '   - Indexes: enrollment_id, session_id, status';
    RAISE NOTICE '   - CHECK: PRESENT status requires checked_in_at timestamp';
END $$;
