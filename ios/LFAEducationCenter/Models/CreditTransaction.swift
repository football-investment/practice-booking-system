import Foundation

// Decoded from GET /api/v1/lfa-player/credits/transactions
// Returns 404 if no LFA Player license exists — callers handle gracefully.
struct CreditTransaction: Decodable, Identifiable {
    let id:                   Int
    let transactionType:      String   // e.g. "SPECIALIZATION_UNLOCK", "INVITATION_BONUS"
    let amount:               Int      // positive = credit in, negative = credit out
    let description:          String?
    let createdAt:            String?

    enum CodingKeys: String, CodingKey {
        case id
        case transactionType      = "transaction_type"
        case amount
        case description
        case createdAt            = "created_at"
    }

    // Signed display: "+150 CR" or "-100 CR"
    var amountDisplay: String {
        amount >= 0 ? "+\(amount) CR" : "\(amount) CR"
    }

    var isCredit: Bool { amount >= 0 }

    // Human-readable type label
    var typeLabel: String {
        switch transactionType.lowercased() {
        case "invitation_bonus":        return "Registration Bonus"
        case "specialization_unlock":   return "Specialization Unlock"
        case "enrollment":              return "Enrollment"
        case "refund":                  return "Refund"
        case "admin_grant":             return "Admin Grant"
        default:
            return transactionType
                .replacingOccurrences(of: "_", with: " ")
                .capitalized
        }
    }
}
