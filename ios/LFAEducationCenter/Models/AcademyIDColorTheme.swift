import Foundation

// Decoded from GET /api/v1/users/me/academy-id/colors.
//
// Phase 1: three free colours (official / ivory / charcoal).
// All Phase-1 colours have is_premium=false, credit_cost=0, is_owned=true.
// Phase 2 will add premium colours; the schema is forward-compatible.

struct AcademyIDColorTheme: Decodable, Identifiable {
    let id:         String
    let label:      String
    let dotColor:   String   // hex — used in the swatch picker circle
    let isPremium:  Bool
    let creditCost: Int
    let isOwned:    Bool
    let sortOrder:  Int

    enum CodingKeys: String, CodingKey {
        case id, label
        case dotColor   = "dot_color"
        case isPremium  = "is_premium"
        case creditCost = "credit_cost"
        case isOwned    = "is_owned"
        case sortOrder  = "sort_order"
    }
}

struct AcademyIDColorsResponse: Decodable {
    let activeColorId: String
    let colors:        [AcademyIDColorTheme]

    enum CodingKeys: String, CodingKey {
        case activeColorId = "active_color_id"
        case colors
    }
}
