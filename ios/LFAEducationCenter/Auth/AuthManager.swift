import Foundation

// Central auth state and session lifecycle.
//
// Token flow:
//   login()              → save access_token + refresh_token → isLoggedIn = true
//   validateSession()    → GET /users/me; on 401: refresh; on refresh 401: logout
//   authenticatedGet/Post → inject Bearer; on 401: single refresh + retry; no infinite loop
//   performRefresh()     → POST /auth/refresh; rotating: save both tokens;
//                          on 401: logout(); on network error: preserve tokens
//   logout()             → clearAll Keychain → isLoggedIn = false
//
// All @Published mutations run on the main actor.
// isRefreshing prevents concurrent refresh attempts (works because the class is @MainActor).
@MainActor
final class AuthManager: ObservableObject {

    @Published private(set) var isLoggedIn:   Bool    = false
    @Published private(set) var isLoading:    Bool    = false
    @Published              var errorMessage: String? = nil

    // Prevents concurrent refresh attempts. @MainActor ensures no data race.
    private var isRefreshing = false

    init() {
        // Optimistic: if tokens exist, show MainTabView immediately.
        // validateSession() (called from app .task) will verify and correct if needed.
        isLoggedIn = KeychainService.load(account: KeychainService.accessTokenKey) != nil
    }

    // MARK: — Session restore (call once on app launch)

    // Validates the stored session against the backend.
    // Strategy:
    //   1. No tokens → stay logged out.
    //   2. Has access_token → GET /users/me to verify.
    //   3. 401 on /users/me → try refresh.
    //   4. Refresh 401 → logout (tokens invalid/expired beyond recovery).
    //   5. Network error at any step → stay logged in (offline tolerance).
    func validateSession() async {
        guard let token = accessToken else {
            isLoggedIn = false
            return
        }

        do {
            let _: UserProfile = try await APIClient.get(
                path: "/api/v1/users/me",
                token: token
            )
            isLoggedIn = true   // token still valid

        } catch APIError.httpError(401, _) {
            // Access token expired — try refresh before giving up.
            let refreshed = await performRefresh()
            // If refreshed: Keychain updated, isLoggedIn stays true.
            // If not refreshed due to 401: logout() already called → isLoggedIn = false.
            // If not refreshed due to network: tokens preserved, isLoggedIn stays true.
            if refreshed { isLoggedIn = true }

        } catch {
            // Network error on launch — remain optimistically logged in.
            // The next protected API call will handle re-auth if needed.
        }
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
            saveTokens(response)
            isLoggedIn = true

        } catch APIError.httpError(let code, _) {
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

    // MARK: — Protected request wrappers (Phase D+ views call these)

    // GET with automatic Bearer inject, single 401 refresh + retry, logout on refresh failure.
    func authenticatedGet<T: Decodable>(path: String) async throws -> T {
        guard let token = accessToken else { logout(); throw APIError.unauthorized }

        do {
            return try await APIClient.get(path: path, token: token)
        } catch APIError.httpError(401, _) {
            let refreshed = await performRefresh()
            guard refreshed, let newToken = accessToken else { throw APIError.unauthorized }
            // Single retry — if this 401s again it propagates without another refresh.
            return try await APIClient.get(path: path, token: newToken)
        }
    }

    // POST with automatic Bearer inject, single 401 refresh + retry, logout on refresh failure.
    func authenticatedPost<B: Encodable, T: Decodable>(path: String, body: B) async throws -> T {
        guard let token = accessToken else { logout(); throw APIError.unauthorized }

        do {
            return try await APIClient.post(path: path, body: body, token: token)
        } catch APIError.httpError(401, _) {
            let refreshed = await performRefresh()
            guard refreshed, let newToken = accessToken else { throw APIError.unauthorized }
            return try await APIClient.post(path: path, body: body, token: newToken)
        }
    }

    // MARK: — Token accessors

    var accessToken: String? {
        KeychainService.load(account: KeychainService.accessTokenKey)
    }

    var refreshToken: String? {
        KeychainService.load(account: KeychainService.refreshTokenKey)
    }

    // MARK: — Private

    // Performs a single token refresh. Returns true on success.
    // On 401: calls logout() (tokens invalid) and returns false.
    // On network error: preserves existing tokens and returns false.
    // isRefreshing prevents concurrent refresh attempts.
    @discardableResult
    private func performRefresh() async -> Bool {
        guard !isRefreshing else { return false }
        guard let rt = refreshToken else { logout(); return false }

        isRefreshing = true
        defer { isRefreshing = false }

        do {
            let response: AuthResponse = try await APIClient.post(
                path: "/api/v1/auth/refresh",
                body: RefreshRequest(refreshToken: rt)
            )
            // Rotating refresh: backend issues a new refresh_token every time.
            // Always save BOTH tokens after a successful refresh.
            saveTokens(response)
            return true

        } catch APIError.httpError(401, _) {
            // Refresh token expired or revoked — session is unrecoverable.
            logout()
            return false

        } catch {
            // Network error — preserve existing tokens, let caller decide.
            return false
        }
    }

    private func saveTokens(_ response: AuthResponse) {
        KeychainService.save(response.accessToken,  account: KeychainService.accessTokenKey)
        KeychainService.save(response.refreshToken, account: KeychainService.refreshTokenKey)
    }
}
