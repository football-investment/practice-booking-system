import Foundation

// Decoded from GET /api/v1/users/me.
//
// Backend sends "name" (full name, single field) — NOT "first_name"/"last_name".
// credit_balance is Int on the backend (not Float/Double).
// xp_balance added for Phase E display.
struct UserProfile: Decodable {
    let id:                  Int?
    let name:                String
    let email:               String
    let role:                String?       // "STUDENT", "INSTRUCTOR", "ADMIN"
    let creditBalance:       Int?          // credit_balance
    let xpBalance:           Int?          // xp_balance — Phase E stat display
    let onboardingCompleted: Bool?
    let position:            String?       // football position
    let licenses:            [UserLicenseBrief]?  // embedded from response

    // displayName maps directly to name — no first/last split in the backend schema.
    var displayName: String { name }

    enum CodingKeys: String, CodingKey {
        case id, name, email, role, position
        case creditBalance       = "credit_balance"
        case xpBalance           = "xp_balance"
        case onboardingCompleted = "onboarding_completed"
        case licenses
    }
}

// Embedded license summary inside GET /api/v1/users/me response.
// Full LFA Player license data: use LFAPlayerLicense from /api/v1/lfa-player/licenses/me.
struct UserLicenseBrief: Decodable, Identifiable {
    let id:                  Int
    let specializationType:  String
    let isActive:            Bool
    let paymentVerified:     Bool?
    let onboardingCompleted: Bool?

    enum CodingKeys: String, CodingKey {
        case id
        case specializationType  = "specialization_type"
        case isActive            = "is_active"
        case paymentVerified     = "payment_verified"
        case onboardingCompleted = "onboarding_completed"
    }
}
