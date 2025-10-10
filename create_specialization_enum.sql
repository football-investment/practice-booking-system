-- create_specialization_enum.sql
-- 🎓 Create specialization enum for Player/Coach tracks
-- ⚠️ CRITICAL: This creates the foundational enum for specialization system

-- Create enum directly (will fail gracefully if exists)
CREATE TYPE specializationtype AS ENUM ('PLAYER', 'COACH');