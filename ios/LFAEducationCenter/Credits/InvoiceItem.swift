import Foundation

// Decoded from GET /api/v1/invoices/my-invoices (Bearer auth).
// Represents one invoice request created by the current user.
struct InvoiceItem: Decodable, Identifiable {
    let id:               Int
    let paymentReference: String
    let amountEur:        Double
    let creditAmount:     Int
    let status:           String   // "pending" | "paid" | "verified" | "cancelled"
    let createdAt:        String?
    let verifiedAt:       String?

    enum CodingKeys: String, CodingKey {
        case id, status
        case paymentReference = "payment_reference"
        case amountEur        = "amount_eur"
        case creditAmount     = "credit_amount"
        case createdAt        = "created_at"
        case verifiedAt       = "verified_at"
    }

    var isPending:    Bool   { status.lowercased() == "pending" }
    var isVerified:   Bool   { status.lowercased() == "verified" }
    var statusLabel:  String { status.capitalized }
    var priceLabel:   String { String(format: "€%.0f", amountEur) }
    var creditsLabel: String { "\(creditAmount) CR" }

    func formattedDate(_ iso: String?) -> String {
        guard let iso else { return "" }
        for opts: ISO8601DateFormatter.Options in [
            [.withInternetDateTime, .withFractionalSeconds],
            [.withInternetDateTime]
        ] {
            let f = ISO8601DateFormatter()
            f.formatOptions = opts
            if let date = f.date(from: iso) {
                let out = DateFormatter()
                out.dateStyle = .medium
                out.timeStyle = .none
                return out.string(from: date)
            }
        }
        return String(iso.prefix(10))
    }

    var createdAtFormatted:  String { formattedDate(createdAt) }
    var verifiedAtFormatted: String { formattedDate(verifiedAt) }
}
