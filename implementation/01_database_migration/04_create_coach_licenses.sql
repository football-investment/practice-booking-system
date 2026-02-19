-- ============================================================================
-- Coach Licenses Table
-- ============================================================================
-- Description: Certification-based, 2-year renewable license for LFA coaches
-- Features:
--   - 8 certification levels (PRE_ASSISTANT → PRO_HEAD)
--   - 2-year mandatory expiry with renewal (NOT NULL expires_at)
--   - Auto-computed is_expired flag
--   - Theory + Practice hours tracking
--   - NO credit system (coaches don't buy credits)
--   - NO attendance table (coaches TEACH, not attend)
-- ============================================================================

CREATE TABLE IF NOT EXISTS coach_licenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Certification progression (1-8 levels)
    -- L1-L2: PRE (5-8 years), L3-L4: YOUTH (9-14), L5-L6: AMATEUR (14+), L7-L8: PRO (16+)
    current_level INTEGER DEFAULT 1 CHECK (current_level BETWEEN 1 AND 8),
    max_achieved_level INTEGER DEFAULT 1 CHECK (max_achieved_level BETWEEN 1 AND 8),

    -- Teaching hours tracking
    theory_hours INTEGER DEFAULT 0 CHECK (theory_hours >= 0),
    practice_hours INTEGER DEFAULT 0 CHECK (practice_hours >= 0),

    -- 2-year mandatory expiry (renewable)
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Expiry status (updated by trigger)
    is_expired BOOLEAN DEFAULT FALSE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_coach_licenses_user_id ON coach_licenses(user_id);
CREATE INDEX idx_coach_licenses_current_level ON coach_licenses(current_level DESC);
CREATE INDEX idx_coach_licenses_expires_at ON coach_licenses(expires_at);
CREATE INDEX idx_coach_licenses_is_expired ON coach_licenses(is_expired);
CREATE INDEX idx_coach_licenses_is_active ON coach_licenses(is_active);

-- ============================================================================
-- Unique Constraint: One active license per user
-- ============================================================================

CREATE UNIQUE INDEX idx_coach_licenses_unique_active_user
ON coach_licenses(user_id)
WHERE is_active = TRUE;

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_coach_license_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coach_licenses_updated_at
BEFORE UPDATE ON coach_licenses
FOR EACH ROW
EXECUTE FUNCTION update_coach_license_timestamp();

-- ============================================================================
-- Trigger: Auto-update max_achieved_level
-- ============================================================================

CREATE OR REPLACE FUNCTION update_coach_max_level()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure max_achieved_level is always >= current_level
    IF NEW.current_level > NEW.max_achieved_level THEN
        NEW.max_achieved_level = NEW.current_level;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coach_licenses_max_level
BEFORE INSERT OR UPDATE ON coach_licenses
FOR EACH ROW
EXECUTE FUNCTION update_coach_max_level();

-- ============================================================================
-- Trigger: Update is_expired flag and auto-deactivate expired licenses
-- ============================================================================

CREATE OR REPLACE FUNCTION check_coach_expiry()
RETURNS TRIGGER AS $$
BEGIN
    -- Update is_expired flag
    IF NEW.expires_at < NOW() THEN
        NEW.is_expired = TRUE;
        -- Also deactivate if active
        IF NEW.is_active = TRUE THEN
            NEW.is_active = FALSE;
        END IF;
    ELSE
        NEW.is_expired = FALSE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coach_licenses_check_expiry
BEFORE INSERT OR UPDATE ON coach_licenses
FOR EACH ROW
EXECUTE FUNCTION check_coach_expiry();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE coach_licenses IS 'Spec-specific license table for LFA coaches with certification-based progression';
COMMENT ON COLUMN coach_licenses.current_level IS 'Current certification level (1=PRE_ASSISTANT, 8=PRO_HEAD)';
COMMENT ON COLUMN coach_licenses.max_achieved_level IS 'Highest certification level ever achieved';
COMMENT ON COLUMN coach_licenses.expires_at IS 'Mandatory 2-year expiry date (renewable)';
COMMENT ON COLUMN coach_licenses.is_expired IS 'Auto-computed expiry status (GENERATED ALWAYS AS expires_at < NOW())';
COMMENT ON COLUMN coach_licenses.theory_hours IS 'Accumulated theory training hours';
COMMENT ON COLUMN coach_licenses.practice_hours IS 'Accumulated practical coaching hours';
