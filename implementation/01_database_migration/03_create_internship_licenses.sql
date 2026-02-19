-- ============================================================================
-- Internship Licenses Table
-- ============================================================================
-- Description: XP-based, 15-month expiry license for business internship program
-- Features:
--   - XP-based progression (22,500 total XP for L1-L8)
--   - Auto level-up when XP thresholds crossed
--   - 15-month mandatory expiry (NOT NULL expires_at)
--   - Credit system (credit_balance column)
--   - 5 semester structure with certificates
--   - Capstone project requirement for L8
-- ============================================================================

CREATE TABLE IF NOT EXISTS internship_licenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Credit system
    credit_balance INTEGER DEFAULT 0 CHECK (credit_balance >= 0),

    -- XP-based progression
    total_xp INTEGER DEFAULT 0 CHECK (total_xp >= 0),
    current_level INTEGER DEFAULT 1 CHECK (current_level BETWEEN 1 AND 8),
    max_achieved_level INTEGER DEFAULT 1 CHECK (max_achieved_level BETWEEN 1 AND 8),

    -- Activity tracking
    sessions_completed INTEGER DEFAULT 0 CHECK (sessions_completed >= 0),

    -- 15-month mandatory expiry
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_internship_licenses_user_id ON internship_licenses(user_id);
CREATE INDEX idx_internship_licenses_current_level ON internship_licenses(current_level DESC);
CREATE INDEX idx_internship_licenses_total_xp ON internship_licenses(total_xp DESC);
CREATE INDEX idx_internship_licenses_expires_at ON internship_licenses(expires_at);
CREATE INDEX idx_internship_licenses_is_active ON internship_licenses(is_active);

-- ============================================================================
-- Unique Constraint: One active license per user
-- ============================================================================

CREATE UNIQUE INDEX idx_internship_licenses_unique_active_user
ON internship_licenses(user_id)
WHERE is_active = TRUE;

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_internship_license_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_internship_licenses_updated_at
BEFORE UPDATE ON internship_licenses
FOR EACH ROW
EXECUTE FUNCTION update_internship_license_timestamp();

-- ============================================================================
-- Trigger: Auto-update max_achieved_level
-- ============================================================================

CREATE OR REPLACE FUNCTION update_internship_max_level()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure max_achieved_level is always >= current_level
    IF NEW.current_level > NEW.max_achieved_level THEN
        NEW.max_achieved_level = NEW.current_level;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_internship_licenses_max_level
BEFORE INSERT OR UPDATE ON internship_licenses
FOR EACH ROW
EXECUTE FUNCTION update_internship_max_level();

-- ============================================================================
-- Trigger: Auto level-up when XP thresholds crossed
-- ============================================================================

CREATE OR REPLACE FUNCTION auto_levelup_internship()
RETURNS TRIGGER AS $$
DECLARE
    xp_thresholds INTEGER[] := ARRAY[0, 1000, 2500, 4500, 7000, 10000, 13500, 17500, 22500];
    new_level INTEGER;
BEGIN
    -- Calculate new level based on total_xp
    new_level := 1;
    FOR i IN 2..8 LOOP
        IF NEW.total_xp >= xp_thresholds[i] THEN
            new_level := i;
        END IF;
    END LOOP;

    -- Update current_level if it changed
    IF new_level != NEW.current_level THEN
        NEW.current_level = new_level;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_internship_licenses_auto_levelup
BEFORE INSERT OR UPDATE OF total_xp ON internship_licenses
FOR EACH ROW
EXECUTE FUNCTION auto_levelup_internship();

-- ============================================================================
-- Trigger: Auto-deactivate expired licenses
-- ============================================================================

CREATE OR REPLACE FUNCTION check_internship_expiry()
RETURNS TRIGGER AS $$
BEGIN
    -- If license has expired, deactivate it
    IF NEW.expires_at < NOW() AND NEW.is_active = TRUE THEN
        NEW.is_active = FALSE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_internship_licenses_check_expiry
BEFORE INSERT OR UPDATE ON internship_licenses
FOR EACH ROW
EXECUTE FUNCTION check_internship_expiry();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE internship_licenses IS 'Spec-specific license table for business internship program with XP-based progression';
COMMENT ON COLUMN internship_licenses.total_xp IS 'Accumulated XP (22,500 total for L1-L8 completion)';
COMMENT ON COLUMN internship_licenses.current_level IS 'Current level (1-8), auto-computed from total_xp';
COMMENT ON COLUMN internship_licenses.expires_at IS 'Mandatory 15-month expiry date (NOT NULL)';
COMMENT ON COLUMN internship_licenses.credit_balance IS 'Available credits for semester enrollment';
