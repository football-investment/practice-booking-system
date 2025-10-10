-- Add position field to users table for football positions
-- This supports the improved StudentProfile.js component

ALTER TABLE users 
ADD COLUMN position VARCHAR;

COMMENT ON COLUMN users.position IS 'Football position: goalkeeper, defender, midfielder, forward, coach';

-- Update existing users with default positions based on role
UPDATE users 
SET position = 'midfielder' 
WHERE role = 'STUDENT' AND position IS NULL;

UPDATE users 
SET position = 'coach' 
WHERE role = 'INSTRUCTOR' AND position IS NULL;