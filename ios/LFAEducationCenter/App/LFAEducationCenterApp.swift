import SwiftUI

@main
struct LFAEducationCenterApp: App {
    @StateObject private var authManager = AuthManager()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authManager)
                // Validate existing session on every cold launch.
                // AuthManager.init() sets isLoggedIn optimistically from Keychain;
                // validateSession() corrects it if tokens are expired or revoked.
                // .task { } is iOS 15+; Task { } inside onAppear is iOS 13+ compatible.
                .onAppear {
                    Task { await authManager.validateSession() }
                }
        }
    }
}
