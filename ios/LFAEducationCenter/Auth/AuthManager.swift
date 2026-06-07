import Foundation

// Central auth state for the app.
// Owns login/logout flow and token lifecycle.
// All @Published mutations run on the main actor.
@MainActor
final class AuthManager: ObservableObject {

    @Published private(set) var isLoggedIn:   Bool    = false
    @Published private(set) var isLoading:    Bool    = false
    @Published              var errorMessage: String? = nil

    init() {
        // Restore session from Keychain on app launch.
        isLoggedIn = KeychainService.load(account: KeychainService.accessTokenKey) != nil
    }

    // MARK: — Login

    func login(email: String, password: String) async {
        isLoading    = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response: AuthResponse = try await APIClient.post(
                path: "/api/v1/auth/login",
                body: LoginRequest(email: email, password: password)
            )
            // Rotating refresh token: always save both after a successful auth.
            KeychainService.save(response.accessToken,  account: KeychainService.accessTokenKey)
            KeychainService.save(response.refreshToken, account: KeychainService.refreshTokenKey)
            isLoggedIn = true

        } catch APIError.httpError(let code, _) {
            // 401 = wrong credentials; 422 = validation error (malformed body)
            errorMessage = (code == 401 || code == 422)
                ? "Invalid email or password."
                : "Server error (\(code)). Please try again."

        } catch APIError.networkError {
            errorMessage = "Network error. Check your connection and try again."

        } catch {
            errorMessage = "Something went wrong. Please try again."
        }
    }

    // MARK: — Logout

    func logout() {
        KeychainService.clearAll()
        isLoggedIn = false
    }

    // MARK: — Token accessors (Phase C+)

    var accessToken: String? {
        KeychainService.load(account: KeychainService.accessTokenKey)
    }

    var refreshToken: String? {
        KeychainService.load(account: KeychainService.refreshTokenKey)
    }
}
