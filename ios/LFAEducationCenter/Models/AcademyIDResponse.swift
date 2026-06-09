import Foundation

// Decoded from GET /api/v1/users/me/academy-id.
//
// Backend lazy-assigns lfa_academy_id + public_token on first call.
// qr_data is the absolute URL to encode in the QR code:
//   {VERIFY_BASE_URL}/verify/{public_token}
struct AcademyIDResponse: Decodable {
    let lfaAcademyId:   String
    let publicToken:    String
    let qrUrl:          String   // relative: /verify/{token}
    let qrData:         String   // absolute: https://lfa.hu/verify/{token}
    let specialization: String?  // display-ready label, e.g. "LFA Football Player"; nil = no active licence

    enum CodingKeys: String, CodingKey {
        case lfaAcademyId   = "lfa_academy_id"
        case publicToken    = "public_token"
        case qrUrl          = "qr_url"
        case qrData         = "qr_data"
        case specialization = "specialization"
    }
}
