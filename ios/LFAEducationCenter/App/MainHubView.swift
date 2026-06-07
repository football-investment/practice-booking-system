import SwiftUI

// Central hub — mirrors hub_specializations.html.
// Login → MainHubView (this) → LFA card tap → LFASpecTabView (fullScreenCover).
// LFASpecTabView is only accessible from the .active card state.
// All other specializations are "Coming Soon" for now.
struct MainHubView: View {
    @EnvironmentObject var authManager: AuthManager
    @EnvironmentObject var dashboardVM: DashboardViewModel
    @State private var isShowingLFASpec = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: Theme.Spacing.md) {
                    greetingSection
                    creditSection
                    Divider()

                    // LFA Football Player — state-driven card
                    let lfaState = dashboardVM.lfaCardState
                    SpecCard(
                        icon:     "⚽",
                        title:    "LFA Football Player",
                        subtitle: lfaSubtitle(for: lfaState),
                        status:   lfaSpecStatus(for: lfaState),
                        action:   lfaState == .active ? { isShowingLFASpec = true } : nil
                    )

                    // Coming-soon specializations
                    SpecCard(icon: "🏮", title: "GānCuju Player",
                             subtitle: "8-level martial arts progression",
                             status: .comingSoon, action: nil)
                    SpecCard(icon: "📋", title: "LFA Coach",
                             subtitle: "Coaching licence progression",
                             status: .comingSoon, action: nil)
                    SpecCard(icon: "💼", title: "Internship",
                             subtitle: "IT Career Program",
                             status: .comingSoon, action: nil)

                    Divider().padding(.vertical, Theme.Spacing.xs)
                    signOutButton
                }
                .padding(Theme.Spacing.md)
            }
            .navigationTitle("LFA Education Center")
        }
        .navigationViewStyle(.stack)
        .onAppear {
            Task { await dashboardVM.load(using: authManager) }
        }
        .fullScreenCover(isPresented: $isShowingLFASpec) {
            LFASpecTabView()
        }
    }

    // MARK: — LFA card helpers

    private func lfaSpecStatus(for state: LFACardState) -> SpecStatus {
        switch state {
        case .loading:             return .comingSoon
        case .ageLocked:           return .ageLocked
        case .insufficientCredits: return .insufficientCredits
        case .unlockAvailable:     return .unlockAvailable
        case .setupPending:        return .setupPending
        case .active:              return .active
        }
    }

    private func lfaSubtitle(for state: LFACardState) -> String {
        switch state {
        case .loading:             return "Loading..."
        case .ageLocked:           return "Minimum age: 5 years"
        case .insufficientCredits: return "100 CR required to unlock"
        case .unlockAvailable:
            let cr = dashboardVM.profile?.creditBalance ?? 0
            return "Ready to unlock · \(cr) CR available"
        case .setupPending:        return "Complete onboarding to continue"
        case .active:              return "Skill development · Tournaments · Cards"
        }
    }

    // MARK: — Sections

    @ViewBuilder
    private var greetingSection: some View {
        if let name = dashboardVM.profile?.displayName {
            HStack {
                Text("Welcome, \(name)")
                    .font(.headline)
                    .foregroundColor(Theme.Color.onSurface)
                Spacer()
            }
        }
    }

    @ViewBuilder
    private var creditSection: some View {
        if let balance = dashboardVM.profile?.creditBalance {
            HStack {
                Spacer()
                Label("\(balance) CR", systemImage: "creditcard.fill")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.secondary)
                    .padding(.horizontal, Theme.Spacing.sm)
                    .padding(.vertical, 6)
                    .background(Theme.Color.secondary.opacity(0.12))
                    .cornerRadius(Theme.Radius.sm)
            }
        }
    }

    private var signOutButton: some View {
        Button {
            authManager.logout()
        } label: {
            Text("Sign Out")
                .fontWeight(.semibold)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(Theme.Color.error.opacity(0.12))
                .foregroundColor(Theme.Color.error)
                .cornerRadius(Theme.Radius.sm)
        }
    }
}

// MARK: — Specialization card

private enum SpecStatus {
    case active
    case ageLocked
    case insufficientCredits
    case unlockAvailable
    case setupPending
    case comingSoon

    // Full opacity + primary title colour for actionable/prominent states.
    var isProminent: Bool {
        switch self {
        case .active, .unlockAvailable: return true
        default: return false
        }
    }
}

private struct SpecCard: View {
    let icon:     String
    let title:    String
    let subtitle: String
    let status:   SpecStatus
    let action:   (() -> Void)?

    var body: some View {
        Button { action?() } label: {
            HStack(spacing: Theme.Spacing.md) {
                Text(icon)
                    .font(.system(size: 36))
                    .frame(width: 48)

                VStack(alignment: .leading, spacing: 4) {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(status.isProminent ? Theme.Color.onSurface : Theme.Color.muted)
                    Text(subtitle)
                        .font(.caption)
                        .foregroundColor(Theme.Color.muted)
                        .lineLimit(1)
                }

                Spacer()
                statusBadge
            }
            .padding(Theme.Spacing.md)
            .background(Theme.Color.surface)
            .cornerRadius(Theme.Radius.md)
            .opacity(status.isProminent ? 1.0 : 0.55)
        }
        .disabled(action == nil)
    }

    @ViewBuilder
    private var statusBadge: some View {
        switch status {
        case .active:
            Text("Open →")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.primary)

        case .unlockAvailable:
            Text("Unlock Available")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.primary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Theme.Color.primary.opacity(0.12))
                .cornerRadius(4)

        case .setupPending:
            Text("Setup Pending")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Theme.Color.secondary.opacity(0.12))
                .cornerRadius(4)

        case .ageLocked:
            Text("Age Locked")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.error)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Theme.Color.error.opacity(0.12))
                .cornerRadius(4)

        case .insufficientCredits:
            Text("Need Credits")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.muted)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Theme.Color.muted.opacity(0.15))
                .cornerRadius(4)

        case .comingSoon:
            Text("Coming Soon")
                .font(.caption.weight(.semibold))
                .foregroundColor(Theme.Color.muted)
                .padding(.horizontal, 6)
                .padding(.vertical, 3)
                .background(Theme.Color.muted.opacity(0.15))
                .cornerRadius(4)
        }
    }
}
