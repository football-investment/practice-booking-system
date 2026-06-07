import Foundation

// Decoded from GET /api/v1/lfa-player/licenses/me.
//
// This replaces the old GET /api/v1/licenses/me for LFA Player flow.
// The old /licenses/me returns GānCuju COACH/PLAYER/INTERNSHIP licenses
// with a different schema (specialization_type, current_level etc.) —
// that system is separate from the LFA Football Player license.
struct LFAPlayerLicense: Decodable {
    let id:                  Int
    let userId:              Int
    let specializationType:  String   // "LFA_FOOTBALL_PLAYER"
    let currentLevel:        Int
    let isActive:            Bool
    let onboardingCompleted: Bool
    let startedAt:           String?

    enum CodingKeys: String, CodingKey {
        case id
        case userId              = "user_id"
        case specializationType  = "specialization_type"
        case currentLevel        = "current_level"
        case isActive            = "is_active"
        case onboardingCompleted = "onboarding_completed"
        case startedAt           = "started_at"
    }
}
