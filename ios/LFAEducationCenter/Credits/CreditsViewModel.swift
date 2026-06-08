import Foundation

// ViewModel for CreditsView.
//
// Credit balance comes from DashboardViewModel.profile.creditBalance (already loaded —
// no extra network call needed for the balance display).
//
// Transaction history: GET /api/v1/lfa-player/credits/transactions
//   Returns 404 if the user has no LFA Player license — handled gracefully
//   (empty list, no error shown to user).
@MainActor
final class CreditsViewModel: ObservableObject {

    enum LoadState {
        case idle
        case loading
        case loaded([CreditTransaction])
        case error(String)
    }

    @Published private(set) var loadState: LoadState = .idle

    var transactions: [CreditTransaction] {
        if case .loaded(let txs) = loadState { return txs }
        return []
    }

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
            let txs: [CreditTransaction] = try await authManager.authenticatedGet(
                path: "/api/v1/lfa-player/credits/transactions?limit=50"
            )
            loadState = .loaded(txs)
        } catch APIError.httpError(let code, _) where code == 404 {
            // No LFA Player license → empty history is fine (not an error)
            loadState = .loaded([])
        } catch {
            loadState = .error("Could not load transaction history.")
        }
    }
}
