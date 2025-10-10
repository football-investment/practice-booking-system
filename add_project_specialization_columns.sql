-- add_project_specialization_columns.sql
-- 🎓 Add specialization support to projects table
-- ⚠️ CRITICAL: Enables project enrollment filtering by specialization

-- Add target_specialization column (nullable = open to all)
ALTER TABLE projects ADD COLUMN target_specialization specializationtype;

-- Add mixed_specialization flag for projects welcoming both specializations
ALTER TABLE projects ADD COLUMN mixed_specialization boolean DEFAULT false;

-- Add helpful comments
COMMENT ON COLUMN projects.target_specialization IS 'Target specialization for this project. NULL = accessible to all specializations';
COMMENT ON COLUMN projects.mixed_specialization IS 'Whether this project encourages collaboration between Player and Coach specializations';