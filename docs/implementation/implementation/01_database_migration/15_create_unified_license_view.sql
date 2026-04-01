-- =====================================================
-- UNIFIED LICENSE VIEW
-- =====================================================
-- Purpose: Combines all 4 license types into a single queryable view
-- Key Features:
--   - Shows ALL active licenses across specializations
--   - Includes user info (email, name)
--   - Shows specialization-specific progress metrics
--   - Nullable columns for specialization-specific fields
--   - Fast queries with proper indexing on underlying tables
-- =====================================================

-- Drop existing view if exists
DROP VIEW IF EXISTS v_all_active_licenses CASCADE;

-- =====================================================
-- VIEW DEFINITION
-- =====================================================

CREATE OR REPLACE VIEW v_all_active_licenses AS

-- LFA Player Licenses
SELECT
    'LFA_PLAYER' AS specialization_type,
    lpl.id AS license_id,
    lpl.user_id,
    u.email,
    u.name,
    lpl.is_active,
    lpl.created_at,
    lpl.updated_at,

    -- LFA Player specific fields
    lpl.age_group AS lfa_age_group,
    lpl.credit_balance AS credit_balance,
    lpl.overall_avg AS skill_overall_avg,
    lpl.heading_avg,
    lpl.shooting_avg,
    lpl.crossing_avg,
    lpl.passing_avg,
    lpl.dribbling_avg,
    lpl.ball_control_avg,

    -- Nullable fields for other specializations
    NULL::INTEGER AS current_level,
    NULL::INTEGER AS max_achieved_level,
    NULL::INTEGER AS total_xp,
    NULL::TIMESTAMP WITH TIME ZONE AS expires_at,
    NULL::BOOLEAN AS is_expired,
    NULL::INTEGER AS sessions_attended,
    NULL::INTEGER AS competitions_entered,
    NULL::INTEGER AS competitions_won,
    NULL::DECIMAL(5,2) AS win_rate,
    NULL::INTEGER AS teaching_hours,
    NULL::INTEGER AS theory_hours,
    NULL::INTEGER AS practice_hours

FROM lfa_player_licenses lpl
JOIN users u ON lpl.user_id = u.id
WHERE lpl.is_active = TRUE

UNION ALL

-- GānCuju Licenses
SELECT
    'GANCUJU' AS specialization_type,
    gl.id AS license_id,
    gl.user_id,
    u.email,
    u.name,
    gl.is_active,
    gl.created_at,
    gl.updated_at,

    -- Nullable LFA Player fields
    NULL::VARCHAR(20) AS lfa_age_group,
    NULL::INTEGER AS credit_balance,
    NULL::DECIMAL(5,2) AS skill_overall_avg,
    NULL::DECIMAL(5,2) AS heading_avg,
    NULL::DECIMAL(5,2) AS shooting_avg,
    NULL::DECIMAL(5,2) AS crossing_avg,
    NULL::DECIMAL(5,2) AS passing_avg,
    NULL::DECIMAL(5,2) AS dribbling_avg,
    NULL::DECIMAL(5,2) AS ball_control_avg,

    -- GānCuju specific fields
    gl.current_level,
    gl.max_achieved_level,
    NULL::INTEGER AS total_xp,
    NULL::TIMESTAMP WITH TIME ZONE AS expires_at,
    NULL::BOOLEAN AS is_expired,
    gl.sessions_attended,
    gl.competitions_entered,
    gl.competitions_won,
    gl.win_rate,
    gl.teaching_hours,
    NULL::INTEGER AS theory_hours,
    NULL::INTEGER AS practice_hours

FROM gancuju_licenses gl
JOIN users u ON gl.user_id = u.id
WHERE gl.is_active = TRUE

UNION ALL

-- Internship Licenses
SELECT
    'INTERNSHIP' AS specialization_type,
    il.id AS license_id,
    il.user_id,
    u.email,
    u.name,
    il.is_active,
    il.created_at,
    il.updated_at,

    -- Nullable LFA Player fields
    NULL::VARCHAR(20) AS lfa_age_group,
    il.credit_balance,
    NULL::DECIMAL(5,2) AS skill_overall_avg,
    NULL::DECIMAL(5,2) AS heading_avg,
    NULL::DECIMAL(5,2) AS shooting_avg,
    NULL::DECIMAL(5,2) AS crossing_avg,
    NULL::DECIMAL(5,2) AS passing_avg,
    NULL::DECIMAL(5,2) AS dribbling_avg,
    NULL::DECIMAL(5,2) AS ball_control_avg,

    -- Internship specific fields
    il.current_level,
    il.max_achieved_level,
    il.total_xp,
    il.expires_at,
    NULL::BOOLEAN AS is_expired,
    il.sessions_completed AS sessions_attended,
    NULL::INTEGER AS competitions_entered,
    NULL::INTEGER AS competitions_won,
    NULL::DECIMAL(5,2) AS win_rate,
    NULL::INTEGER AS teaching_hours,
    NULL::INTEGER AS theory_hours,
    NULL::INTEGER AS practice_hours

FROM internship_licenses il
JOIN users u ON il.user_id = u.id
WHERE il.is_active = TRUE

UNION ALL

-- Coach Licenses
SELECT
    'COACH' AS specialization_type,
    cl.id AS license_id,
    cl.user_id,
    u.email,
    u.name,
    cl.is_active,
    cl.created_at,
    cl.updated_at,

    -- Nullable LFA Player fields
    NULL::VARCHAR(20) AS lfa_age_group,
    NULL::INTEGER AS credit_balance,
    NULL::DECIMAL(5,2) AS skill_overall_avg,
    NULL::DECIMAL(5,2) AS heading_avg,
    NULL::DECIMAL(5,2) AS shooting_avg,
    NULL::DECIMAL(5,2) AS crossing_avg,
    NULL::DECIMAL(5,2) AS passing_avg,
    NULL::DECIMAL(5,2) AS dribbling_avg,
    NULL::DECIMAL(5,2) AS ball_control_avg,

    -- Coach specific fields
    cl.current_level,
    cl.max_achieved_level,
    NULL::INTEGER AS total_xp,
    cl.expires_at,
    cl.is_expired,
    NULL::INTEGER AS sessions_attended,
    NULL::INTEGER AS competitions_entered,
    NULL::INTEGER AS competitions_won,
    NULL::DECIMAL(5,2) AS win_rate,
    NULL::INTEGER AS teaching_hours,
    cl.theory_hours,
    cl.practice_hours

FROM coach_licenses cl
JOIN users u ON cl.user_id = u.id
WHERE cl.is_active = TRUE;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON VIEW v_all_active_licenses IS 'Unified view of all active licenses across all 4 specializations';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ v_all_active_licenses view created successfully!';
    RAISE NOTICE '   - Combines 4 license types: LFA_PLAYER, GANCUJU, INTERNSHIP, COACH';
    RAISE NOTICE '   - Shows only active licenses (is_active = TRUE)';
    RAISE NOTICE '   - Includes user info (email, name)';
    RAISE NOTICE '   - Specialization-specific columns are NULL for other types';
    RAISE NOTICE '   - Use: SELECT * FROM v_all_active_licenses WHERE user_id = ?';
END $$;
