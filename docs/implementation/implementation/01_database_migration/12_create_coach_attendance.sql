-- =====================================================
-- COACH ATTENDANCE TABLE
-- =====================================================
-- Purpose: Tracks COACH TRAINING attendance in sessions
--
-- IMPORTANT: COACH = TRAINING PROGRAM FOR COACHING CERTIFICATION!
-- - 8 levels: PRE Assistant → PRE Head → YOUTH Assistant → ... → PRO Head Coach
-- - Total duration: ~6 years (72 months)
-- - Coaches ATTEND sessions to complete their certification requirements
-- - Theory + Practice hours must be completed to advance levels
--
-- Key Features:
--   - Tracks attendance status (PRESENT, ABSENT, LATE, EXCUSED)
--   - Links to enrollments (coach enrollments in training semesters)
--   - Theory/Practice hours tracking
--   - Auto-cascade cleanup on enrollment/session deletion
--   - Audit trail (created_at, updated_at)
-- =====================================================

-- Drop existing table and triggers if they exist
DROP TRIGGER IF EXISTS trg_coach_attendance_updated_at ON coach_attendance CASCADE;
DROP FUNCTION IF EXISTS update_coach_attendance_timestamp() CASCADE;
DROP TABLE IF EXISTS coach_attendance CASCADE;

-- =====================================================
-- TABLE DEFINITION
-- =====================================================

CREATE TABLE coach_attendance (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    enrollment_id INTEGER NOT NULL REFERENCES coach_assignments(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Attendance Details
    status VARCHAR(20) NOT NULL CHECK (status IN ('PRESENT', 'ABSENT', 'LATE', 'EXCUSED')) DEFAULT 'ABSENT',
    checked_in_at TIMESTAMP WITH TIME ZONE,
    checked_in_by INTEGER REFERENCES users(id),  -- Admin/supervisor who marked attendance

    -- Training Hours (CRITICAL for Coach certification advancement)
    theory_hours_earned DECIMAL(5,2) DEFAULT 0 CHECK (theory_hours_earned >= 0),
    practice_hours_earned DECIMAL(5,2) DEFAULT 0 CHECK (practice_hours_earned >= 0),

    -- Notes
    notes TEXT,

    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_coach_attendance_checkin CHECK (
        (status = 'PRESENT' AND checked_in_at IS NOT NULL) OR
        (status != 'PRESENT')
    ),
    CONSTRAINT chk_coach_attendance_hours CHECK (
        (status = 'PRESENT' AND (theory_hours_earned > 0 OR practice_hours_earned > 0)) OR
        (status != 'PRESENT' AND theory_hours_earned = 0 AND practice_hours_earned = 0)
    )
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Unique attendance record per enrollment per session
CREATE UNIQUE INDEX idx_coach_attendance_unique
ON coach_attendance(enrollment_id, session_id);

-- Fast lookup by enrollment
CREATE INDEX idx_coach_attendance_enrollment
ON coach_attendance(enrollment_id);

-- Fast lookup by session
CREATE INDEX idx_coach_attendance_session
ON coach_attendance(session_id);

-- Fast lookup by status
CREATE INDEX idx_coach_attendance_status
ON coach_attendance(status);

-- Fast lookup of present attendances
CREATE INDEX idx_coach_attendance_present
ON coach_attendance(enrollment_id, status)
WHERE status = 'PRESENT';

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_coach_attendance_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coach_attendance_updated_at
BEFORE UPDATE ON coach_attendance
FOR EACH ROW
EXECUTE FUNCTION update_coach_attendance_timestamp();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE coach_attendance IS '⚠️ COACH TRAINING attendance records - Coaches ATTEND sessions to complete certification requirements (~6 year program)';
COMMENT ON COLUMN coach_attendance.enrollment_id IS 'Foreign key to coach_assignments (coach enrollments in training semesters)';
COMMENT ON COLUMN coach_attendance.session_id IS 'Foreign key to sessions';
COMMENT ON COLUMN coach_attendance.status IS 'Attendance status: PRESENT, ABSENT, LATE, EXCUSED';
COMMENT ON COLUMN coach_attendance.checked_in_at IS 'Timestamp when coach trainee checked in (for PRESENT status)';
COMMENT ON COLUMN coach_attendance.checked_in_by IS 'User ID of admin/supervisor who marked attendance';
COMMENT ON COLUMN coach_attendance.theory_hours_earned IS 'Theory hours earned in this session (accumulates toward certification)';
COMMENT ON COLUMN coach_attendance.practice_hours_earned IS 'Practice hours earned in this session (accumulates toward certification)';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ coach_attendance table created successfully!';
    RAISE NOTICE '   ⚠️  COACH = TRAINING PROGRAM (not instructors teaching!)';
    RAISE NOTICE '   - Coaches ATTEND sessions to complete ~6 year certification';
    RAISE NOTICE '   - 8 levels: PRE Assistant → PRE Head → ... → PRO Head Coach';
    RAISE NOTICE '   - UNIQUE constraint: One attendance record per enrollment per session';
    RAISE NOTICE '   - CASCADE DELETE: Auto-cleanup on enrollment/session deletion';
    RAISE NOTICE '   - Trigger: Auto-update updated_at';
    RAISE NOTICE '   - Indexes: enrollment_id, session_id, status';
    RAISE NOTICE '   - CHECK: PRESENT status requires checked_in_at + hours earned';
    RAISE NOTICE '   - Theory + Practice hours accumulate toward certification requirements';
END $$;
