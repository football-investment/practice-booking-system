-- add_user_specialization_column.sql
-- 🎓 Add specialization column to users table
-- ⚠️ CRITICAL: Must be nullable for backward compatibility with existing users

-- Add specialization column (nullable for backward compatibility)
ALTER TABLE users ADD COLUMN specialization specializationtype;

-- Add helpful comment
COMMENT ON COLUMN users.specialization IS 'User chosen specialization track (Player/Coach). NULL = not yet selected for backward compatibility';