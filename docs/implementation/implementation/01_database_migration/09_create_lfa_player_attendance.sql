-- =====================================================
-- LFA PLAYER ATTENDANCE TABLE
-- =====================================================
-- Purpose: Tracks LFA Player attendance in sessions
-- Key Features:
--   - Tracks attendance status (PRESENT, ABSENT, LATE, EXCUSED)
--   - Links to enrollments (not directly to licenses)
--   - XP rewards for attendance
--   - Auto-cascade cleanup on enrollment/session deletion
--   - Audit trail (created_at, updated_at)
-- =====================================================

-- Drop existing table and triggers if they exist
DROP TRIGGER IF EXISTS trg_lfa_player_attendance_updated_at ON lfa_player_attendance CASCADE;
DROP FUNCTION IF EXISTS update_lfa_player_attendance_timestamp() CASCADE;
DROP TABLE IF EXISTS lfa_player_attendance CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE lfa_player_attendance (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    enrollment_id INTEGER NOT NULL REFERENCES lfa_player_enrollments(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Attendance Details
    status VARCHAR(20) NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')) DEFAULT 'ABSENT',
    checked_in_at TIMESTAMP WITH TIME ZONE,
    checked_in_by INTEGER REFERENCES users(id),  -- Admin/instructor who marked attendance

    -- Rewards/Penalties
    xp_earned INTEGER DEFAULT 0 CHECK (xp_earned >= 0),

    -- Notes
    notes TEXT,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_lfa_player_attendance_checkin CHECK (
        (status = 'PRESENT' AND checked_in_at IS NOT NULL) OR
        (status != 'PRESENT')
    )
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Unique attendance record per enrollment per session
CREATE UNIQUE INDEX idx_lfa_player_attendance_unique
ON lfa_player_attendance(enrollment_id, session_id);

-- Fast lookup by enrollment
CREATE INDEX idx_lfa_player_attendance_enrollment
ON lfa_player_attendance(enrollment_id);

-- Fast lookup by session
CREATE INDEX idx_lfa_player_attendance_session
ON lfa_player_attendance(session_id);

-- Fast lookup by status
CREATE INDEX idx_lfa_player_attendance_status
ON lfa_player_attendance(status);

-- Fast lookup of present attendances
CREATE INDEX idx_lfa_player_attendance_present
ON lfa_player_attendance(enrollment_id, status)
WHERE status = 'PRESENT';

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_lfa_player_attendance_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lfa_player_attendance_updated_at
BEFORE UPDATE ON lfa_player_attendance
FOR EACH ROW
EXECUTE FUNCTION update_lfa_player_attendance_timestamp();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE lfa_player_attendance IS 'LFA Player attendance records for sessions';
COMMENT ON COLUMN lfa_player_attendance.enrollment_id IS 'Foreign key to lfa_player_enrollments';
COMMENT ON COLUMN lfa_player_attendance.session_id IS 'Foreign key to sessions';
COMMENT ON COLUMN lfa_player_attendance.status IS 'Attendance status: PRESENT, ABSENT, LATE, EXCUSED';
COMMENT ON COLUMN lfa_player_attendance.checked_in_at IS 'Timestamp when player checked in (for PRESENT status)';
COMMENT ON COLUMN lfa_player_attendance.checked_in_by IS 'User ID of admin/instructor who marked attendance';
COMMENT ON COLUMN lfa_player_attendance.xp_earned IS 'XP points earned for attending (0 if absent)';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ lfa_player_attendance table created successfully!';
    RAISE NOTICE '   - UNIQUE constraint: One attendance record per enrollment per session';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on enrollment/session deletion';
    RAISE NOTICE '   - Trigger: Auto-update updated_at';
    RAISE NOTICE '   - Indexes: enrollment_id, session_id, status';
    RAISE NOTICE '   - CHECK: PRESENT status requires checked_in_at timestamp';
END $$;
