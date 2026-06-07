import Foundation

// Minimal user profile — returned by GET /api/v1/users/me.
// Used for session validation on app launch.
// Phase D extends this with creditBalance, role, dateOfBirth, etc.
struct UserProfile: Decodable {
    let email:     String
    let firstName: String
    let lastName:  String

    enum CodingKeys: String, CodingKey {
        case email
        case firstName = "first_name"
        case lastName  = "last_name"
    }
}
