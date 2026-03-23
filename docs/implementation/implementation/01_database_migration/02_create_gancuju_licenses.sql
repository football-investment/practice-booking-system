-- ============================================================================
-- GānCuju Licenses Table
-- ============================================================================
-- Description: Belt-based, lifetime license for GānCuju traditional football players
-- Features:
--   - 8 belt levels (BAMBOO_DISCIPLE → DRAGON_WISDOM)
--   - Competition tracking with auto-computed win_rate
--   - Teaching hours tracking (required for L5+ belt promotion)
--   - NO credit system (no credit_balance column)
--   - Lifetime license (NO expires_at column)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gancuju_licenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Belt progression (1-8 levels)
    current_level INTEGER DEFAULT 1 CHECK (current_level BETWEEN 1 AND 8),
    max_achieved_level INTEGER DEFAULT 1 CHECK (max_achieved_level BETWEEN 1 AND 8),

    -- Activity tracking
    sessions_attended INTEGER DEFAULT 0 CHECK (sessions_attended >= 0),

    -- Competition tracking
    competitions_entered INTEGER DEFAULT 0 CHECK (competitions_entered >= 0),
    competitions_won INTEGER DEFAULT 0 CHECK (competitions_won >= 0),

    -- Auto-computed win rate (GENERATED ALWAYS AS)
    win_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE
            WHEN competitions_entered = 0 THEN 0
            ELSE (competitions_won::DECIMAL / competitions_entered::DECIMAL * 100)
        END
    ) STORED,

    -- Teaching hours (required for L5+ belt promotion)
    teaching_hours INTEGER DEFAULT 0 CHECK (teaching_hours >= 0),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_gancuju_licenses_user_id ON gancuju_licenses(user_id);
CREATE INDEX idx_gancuju_licenses_current_level ON gancuju_licenses(current_level DESC);
CREATE INDEX idx_gancuju_licenses_is_active ON gancuju_licenses(is_active);
CREATE INDEX idx_gancuju_licenses_win_rate ON gancuju_licenses(win_rate DESC);

-- ============================================================================
-- Unique Constraint: One active license per user
-- ============================================================================

CREATE UNIQUE INDEX idx_gancuju_licenses_unique_active_user
ON gancuju_licenses(user_id)
WHERE is_active = TRUE;

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_gancuju_license_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gancuju_licenses_updated_at
BEFORE UPDATE ON gancuju_licenses
FOR EACH ROW
EXECUTE FUNCTION update_gancuju_license_timestamp();

-- ============================================================================
-- Trigger: Auto-update max_achieved_level
-- ============================================================================

CREATE OR REPLACE FUNCTION update_gancuju_max_level()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure max_achieved_level is always >= current_level
    IF NEW.current_level > NEW.max_achieved_level THEN
        NEW.max_achieved_level = NEW.current_level;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_gancuju_licenses_max_level
BEFORE INSERT OR UPDATE ON gancuju_licenses
FOR EACH ROW
EXECUTE FUNCTION update_gancuju_max_level();

-- ============================================================================
-- Constraint: competitions_won cannot exceed competitions_entered
-- ============================================================================

ALTER TABLE gancuju_licenses
ADD CONSTRAINT chk_gancuju_competitions_logic
CHECK (competitions_won <= competitions_entered);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE gancuju_licenses IS 'Spec-specific license table for GānCuju traditional football players with belt-based progression';
COMMENT ON COLUMN gancuju_licenses.current_level IS 'Current belt level (1=BAMBOO_DISCIPLE, 8=DRAGON_WISDOM)';
COMMENT ON COLUMN gancuju_licenses.max_achieved_level IS 'Highest belt level ever achieved (cannot decrease)';
COMMENT ON COLUMN gancuju_licenses.win_rate IS 'Auto-computed competition win percentage (GENERATED ALWAYS AS)';
COMMENT ON COLUMN gancuju_licenses.teaching_hours IS 'Required for L5+ belt promotion (STRONG_ROOT and above)';
