import Foundation

// ViewModel for the Academy ID card colour picker.
//
// Loads the colour palette from GET /api/v1/users/me/academy-id/colors.
// Persists the active selection via POST /api/v1/users/me/academy-id/colors/select.
//
// Optimistic update: activeColorId switches immediately on tap; if the API
// call fails the previous colour is restored and errorMessage is set.
//
// Phase 1: three free colours — no credit deduction, no ownership checks.
// Phase 2 will add unlock logic before calling select.

@MainActor
final class AcademyIDColorViewModel: ObservableObject {

    @Published private(set) var colors:        [AcademyIDColorTheme] = []
    @Published private(set) var activeColorId: String                = "official"
    @Published private(set) var isLoading:     Bool                  = false
    @Published           var errorMessage:     String?               = nil

    // MARK: — Load colour list (no-op if already loaded)

    func load(using authManager: AuthManager) async {
        guard colors.isEmpty else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            let response: AcademyIDColorsResponse = try await authManager.authenticatedGet(
                path: "/api/v1/users/me/academy-id/colors"
            )
            colors        = response.colors.sorted { $0.sortOrder < $1.sortOrder }
            activeColorId = response.activeColorId
        } catch {
            // Non-fatal: colour picker falls back to "official" appearance if unavailable.
            errorMessage = "Could not load card styles."
        }
    }

    // MARK: — Select a colour (optimistic + rollback)

    func select(colorId: String, using authManager: AuthManager) async {
        guard colorId != activeColorId else { return }

        let previous      = activeColorId
        activeColorId     = colorId   // optimistic update
        errorMessage      = nil

        do {
            struct Payload:  Encodable  { let colorId: String
                enum CodingKeys: String, CodingKey { case colorId = "color_id" } }
            struct Response: Decodable  { let ok: Bool; let activeColorId: String
                enum CodingKeys: String, CodingKey { case ok; case activeColorId = "active_color_id" } }

            let _: Response = try await authManager.authenticatedPost(
                path: "/api/v1/users/me/academy-id/colors/select",
                body: Payload(colorId: colorId)
            )
        } catch {
            activeColorId = previous   // rollback
            errorMessage  = "Could not apply style. Check your connection."
        }
    }
}
