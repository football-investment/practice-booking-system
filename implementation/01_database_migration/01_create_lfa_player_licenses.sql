-- ============================================================================
-- LFA Player Licenses Table
-- ============================================================================
-- Description: Skill-based, lifetime license for LFA football players
-- Features:
--   - 6 skill dimensions (heading, shooting, crossing, passing, dribbling, ball_control)
--   - Auto-computed overall_avg via GENERATED ALWAYS AS
--   - Credit system (credit_balance column)
--   - Age-based categorization (PRE, YOUTH, AMATEUR, PRO)
--   - Lifetime license (NO expires_at column)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lfa_player_licenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Age group classification
    age_group VARCHAR(20) NOT NULL CHECK (age_group IN ('PRE', 'YOUTH', 'AMATEUR', 'PRO')),

    -- Credit system
    credit_balance INTEGER DEFAULT 0 CHECK (credit_balance >= 0),

    -- 6 Skill dimensions (0-100 scale)
    heading_avg DECIMAL(5,2) DEFAULT 0 CHECK (heading_avg BETWEEN 0 AND 100),
    shooting_avg DECIMAL(5,2) DEFAULT 0 CHECK (shooting_avg BETWEEN 0 AND 100),
    crossing_avg DECIMAL(5,2) DEFAULT 0 CHECK (crossing_avg BETWEEN 0 AND 100),
    passing_avg DECIMAL(5,2) DEFAULT 0 CHECK (passing_avg BETWEEN 0 AND 100),
    dribbling_avg DECIMAL(5,2) DEFAULT 0 CHECK (dribbling_avg BETWEEN 0 AND 100),
    ball_control_avg DECIMAL(5,2) DEFAULT 0 CHECK (ball_control_avg BETWEEN 0 AND 100),

    -- Auto-computed overall average (GENERATED ALWAYS AS)
    overall_avg DECIMAL(5,2) GENERATED ALWAYS AS (
        (heading_avg + shooting_avg + crossing_avg + passing_avg + dribbling_avg + ball_control_avg) / 6.0
    ) STORED,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_lfa_player_licenses_user_id ON lfa_player_licenses(user_id);
CREATE INDEX idx_lfa_player_licenses_age_group ON lfa_player_licenses(age_group);
CREATE INDEX idx_lfa_player_licenses_is_active ON lfa_player_licenses(is_active);
CREATE INDEX idx_lfa_player_licenses_overall_avg ON lfa_player_licenses(overall_avg DESC);

-- ============================================================================
-- Unique Constraint: One active license per user
-- ============================================================================

CREATE UNIQUE INDEX idx_lfa_player_licenses_unique_active_user
ON lfa_player_licenses(user_id)
WHERE is_active = TRUE;

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_lfa_player_license_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lfa_player_licenses_updated_at
BEFORE UPDATE ON lfa_player_licenses
FOR EACH ROW
EXECUTE FUNCTION update_lfa_player_license_timestamp();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE lfa_player_licenses IS 'Spec-specific license table for LFA football players with skill-based progression';
COMMENT ON COLUMN lfa_player_licenses.age_group IS 'Age category: PRE (5-8), YOUTH (9-14), AMATEUR (14+), PRO (16+)';
COMMENT ON COLUMN lfa_player_licenses.credit_balance IS 'Available credits for semester enrollment';
COMMENT ON COLUMN lfa_player_licenses.overall_avg IS 'Auto-computed average of 6 skill dimensions (GENERATED ALWAYS AS)';
