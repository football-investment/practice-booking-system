-- add_session_specialization_columns.sql
-- 🎓 Add specialization support to sessions table
-- ⚠️ CRITICAL: Enables session filtering by specialization

-- Add target_specialization column (nullable = open to all)
ALTER TABLE sessions ADD COLUMN target_specialization specializationtype;

-- Add mixed_specialization flag for sessions open to both specializations
ALTER TABLE sessions ADD COLUMN mixed_specialization boolean DEFAULT false;

-- Add helpful comments
COMMENT ON COLUMN sessions.target_specialization IS 'Target specialization for this session. NULL = accessible to all specializations';
COMMENT ON COLUMN sessions.mixed_specialization IS 'Whether this session welcomes both Player and Coach specializations together';