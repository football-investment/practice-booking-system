import Foundation

// Fetches the user's invoice list from GET /api/v1/invoices/my-invoices (Bearer).
// Filters to pending invoices for display in the CreditsView Pending Invoices section.
//
// The section only renders if pendingInvoices is non-empty — no empty state shown
// (absence of pending invoices is the normal/happy state).
@MainActor
final class PendingInvoicesViewModel: ObservableObject {

    enum LoadState {
        case idle
        case loading
        case loaded([InvoiceItem])
        case error(String)
    }

    @Published private(set) var loadState: LoadState = .idle

    var pendingInvoices: [InvoiceItem] {
        if case .loaded(let items) = loadState {
            return items.filter { $0.isPending }
        }
        return []
    }

    var hasPending: Bool { !pendingInvoices.isEmpty }

    // MARK: — Load (guarded)

    func load(using authManager: AuthManager) async {
        guard case .idle = loadState else { return }
        await fetch(using: authManager)
    }

    func reload(using authManager: AuthManager) async {
        loadState = .idle
        await fetch(using: authManager)
    }

    // MARK: — Private

    private func fetch(using authManager: AuthManager) async {
        loadState = .loading
        do {
            let items: [InvoiceItem] = try await authManager.authenticatedGet(
                path: "/api/v1/invoices/my-invoices"
            )
            loadState = .loaded(items)
        } catch {
            // Error is silent — pending invoices section simply stays hidden
            loadState = .loaded([])
        }
    }
}
