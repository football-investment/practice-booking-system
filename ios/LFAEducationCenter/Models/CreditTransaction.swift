import Foundation

// Decoded from GET /api/v1/users/me/credit-transactions (user-level, all transactions).
// Also backward-compatible with GET /api/v1/lfa-player/credits/transactions (flat array).
struct CreditTransaction: Decodable, Identifiable {
    let id:                   Int
    let transactionType:      String   // e.g. "SPECIALIZATION_UNLOCK", "INVITATION_BONUS"
    let amount:               Int      // positive = credit in, negative = credit out
    let balanceAfter:         Int?     // present in user-level endpoint; nil in license-level
    let description:          String?
    let createdAt:            String?

    enum CodingKeys: String, CodingKey {
        case id
        case transactionType      = "transaction_type"
        case amount
        case balanceAfter         = "balance_after"
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
        case "invitation_bonus":        return "Invitation Bonus"
        case "specialization_unlock":   return "Specialization Unlock"
        case "enrollment":              return "Enrollment"
        case "refund":                  return "Refund"
        case "admin_grant":             return "Admin Grant"
        case "admin_adjustment":        return "Credit Adjustment"
        case "purchase":                return "Credit Purchase"
        case "tournament_reward":       return "Tournament Reward"
        default:
            return transactionType
                .replacingOccurrences(of: "_", with: " ")
                .capitalized
        }
    }
}

// Wrapper decoded from GET /api/v1/users/me/credit-transactions
// Returns {"transactions": [...], "total_count": int, "credit_balance": int}
struct CreditTransactionPage: Decodable {
    let transactions:  [CreditTransaction]
    let totalCount:    Int
    let creditBalance: Int

    enum CodingKeys: String, CodingKey {
        case transactions
        case totalCount    = "total_count"
        case creditBalance = "credit_balance"
    }
}
