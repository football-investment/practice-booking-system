import SwiftUI

// Phase A: tab navigation shell.
// Phase B replaces this with auth-gated routing (LoginView → MainTabView).
struct RootView: View {
    var body: some View {
        MainTabView()
    }
}

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

            PlaceholderScreen(title: "Profile",
                              subtitle: "User profile — Phase D",
                              icon: "person.fill")
                .tabItem { Label("Profile", systemImage: "person.fill") }
        }
        .accentColor(Theme.Color.primary)
    }
}

// Shared placeholder used in Phase A for screens not yet implemented.
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
        .navigationTitle(title)
    }
}
