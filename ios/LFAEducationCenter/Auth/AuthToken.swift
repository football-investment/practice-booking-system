import Foundation

struct LoginRequest: Encodable {
    let email:    String
    let password: String
}

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
