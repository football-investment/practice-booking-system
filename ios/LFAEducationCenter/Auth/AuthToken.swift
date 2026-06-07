import Foundation

struct LoginRequest: Encodable {
    let email:    String
    let password: String
}

// POST /api/v1/auth/refresh request body.
// Backend expects { "refresh_token": "..." } in JSON body (not Authorization header).
struct RefreshRequest: Encodable {
    let refreshToken: String
    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

// Shared response for login and refresh — both endpoints return the same shape.
struct AuthResponse: Decodable {
    let accessToken:  String
    let refreshToken: String
    let tokenType:    String

    enum CodingKeys: String, CodingKey {
        case accessToken  = "access_token"
        case refreshToken = "refresh_token"
        case tokenType    = "token_type"
    }
}
