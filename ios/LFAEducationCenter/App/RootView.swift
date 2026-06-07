import SwiftUI

// Auth-gated root: shows LoginView until isLoggedIn, then MainTabView.
// Phase C adds: token refresh on 401, session expiry handling.
struct RootView: View {
    @EnvironmentObject var authManager: AuthManager

    var body: some View {
        if authManager.isLoggedIn {
            MainTabView()
        } else {
            LoginView()
        }
    }
}

// MARK: — Main tab navigation

struct MainTabView: View {
    var body: some View {
        TabView {
            PlaceholderScreen(title: "Dashboard",
                              subtitle: "Native dashboard — Phase D",
                              icon: "house.fill")
                .tabItem { Label("Dashboard", systemImage: "house.fill") }

            PlaceholderScreen(title: "Education",
                              subtitle: "Education Center — Phase E",
                              icon: "book.fill")
                .tabItem { Label("Education", systemImage: "book.fill") }

            PlaceholderScreen(title: "Training",
                              subtitle: "Skeleton tracking — Phase F",
                              icon: "stopwatch.fill")
                .tabItem { Label("Training", systemImage: "stopwatch.fill") }

            ProfileTab()
                .tabItem { Label("Profile", systemImage: "person.fill") }
        }
        .accentColor(Theme.Color.primary)
    }
}

// MARK: — Profile tab (logout available in Phase B)

private struct ProfileTab: View {
    @EnvironmentObject var authManager: AuthManager

    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "person.fill")
                .font(.system(size: 52))
                .foregroundColor(Theme.Color.muted)
                .padding(.top, Theme.Spacing.xl)

            Text("Profile")
                .font(.title2.weight(.semibold))
                .foregroundColor(Theme.Color.onSurface)

            Text("Native profile — Phase D")
                .font(.subheadline)
                .foregroundColor(Theme.Color.muted)

            Spacer()

            Button {
                authManager.logout()
            } label: {
                Text("Sign Out")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                    .background(Theme.Color.error.opacity(0.12))
                    .foregroundColor(Theme.Color.error)
                    .cornerRadius(Theme.Radius.sm)
            }
            .padding(.horizontal, Theme.Spacing.xl)
            .padding(.bottom, Theme.Spacing.xl)
        }
    }
}

// MARK: — Generic placeholder for Phase A tabs

struct PlaceholderScreen: View {
    let title:    String
    let subtitle: String
    let icon:     String

    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: icon)
                .font(.system(size: 52))
                .foregroundColor(Theme.Color.muted)
            Text(title)
                .font(.title2.weight(.semibold))
                .foregroundColor(Theme.Color.onSurface)
            Text(subtitle)
                .font(.subheadline)
                .foregroundColor(Theme.Color.muted)
                .multilineTextAlignment(.center)
        }
        .padding(Theme.Spacing.xl)
    }
}
