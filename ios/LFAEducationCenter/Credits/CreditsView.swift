import SwiftUI

// Credits overview — balance hero, how to get credits info, transaction history.
//
// Balance:        read from DashboardViewModel.profile.creditBalance (already loaded)
// Transactions:   CreditsViewModel loads from GET /api/v1/lfa-player/credits/transactions
//                 Returns 404 if no license yet → empty list, no error shown
//
// NOTE: There is no in-app credit purchase gateway.
// Credits are admin-verified (offline payment / registration bonus / academic milestone).
struct CreditsView: View {

    @EnvironmentObject private var authManager:  AuthManager
    @EnvironmentObject private var dashboardVM:  DashboardViewModel
    @StateObject         private var viewModel   = CreditsViewModel()

    @Environment(\.presentationMode) private var presentationMode

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 0) {
                    balanceHero
                    howToGetSection
                    transactionSection
                    Spacer(minLength: Theme.Spacing.xl)
                }
            }
            .background(Color(UIColor.systemBackground).ignoresSafeArea())
            .navigationTitle("Credits")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        presentationMode.wrappedValue.dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(Theme.Color.onSurface)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task { await viewModel.reload(using: authManager) }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(Theme.Color.primary)
                    }
                    .disabled(isLoading)
                }
            }
        }
        .navigationViewStyle(.stack)
        .onAppear { Task { await viewModel.load(using: authManager) } }
    }

    // MARK: — Balance hero

    private var balanceHero: some View {
        VStack(spacing: 8) {
            Image(systemName: "creditcard.fill")
                .font(.system(size: 36))
                .foregroundColor(Theme.Color.secondary)

            Text("\(dashboardVM.profile?.creditBalance ?? 0)")
                .font(.system(size: 48, weight: .bold, design: .rounded))
                .foregroundColor(Theme.Color.onSurface)

            Text("CR Balance")
                .font(.subheadline)
                .foregroundColor(Theme.Color.muted)

            // Unlock cost context when insufficient
            if (dashboardVM.profile?.creditBalance ?? 0) < 100 {
                let needed = 100 - (dashboardVM.profile?.creditBalance ?? 0)
                Text("You need \(needed) more CR to unlock LFA Football Player")
                    .font(.caption)
                    .foregroundColor(Theme.Color.error)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Theme.Spacing.xl)
        .padding(.horizontal, Theme.Spacing.md)
        .background(Theme.Color.surface)
        .padding(.horizontal, Theme.Spacing.md)
        .padding(.top, Theme.Spacing.md)
        .cornerRadius(Theme.Radius.md)
    }

    // MARK: — How to get credits

    private var howToGetSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Text("HOW TO GET CREDITS")
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(Theme.Color.muted)
                .kerning(0.8)
                .padding(.horizontal, Theme.Spacing.md)
                .padding(.top, Theme.Spacing.lg)

            VStack(spacing: 1) {
                infoRow(icon: "gift.fill",          title: "Registration Bonus",        detail: "Granted automatically when you join")
                infoRow(icon: "person.badge.plus",   title: "Academy Milestones",        detail: "Awarded by your LFA instructor")
                infoRow(icon: "building.columns",    title: "Admin Grant",               detail: "Contact your Academy administrator")
            }
            .background(Theme.Color.surface)
            .cornerRadius(Theme.Radius.md)
            .padding(.horizontal, Theme.Spacing.md)
        }
    }

    private func infoRow(icon: String, title: String, detail: String) -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 15))
                .foregroundColor(Theme.Color.secondary)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.onSurface)
                Text(detail)
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
            }
            Spacer()
        }
        .padding(.horizontal, Theme.Spacing.md)
        .padding(.vertical, 10)
    }

    // MARK: — Transaction history

    @ViewBuilder
    private var transactionSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Text("TRANSACTION HISTORY")
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(Theme.Color.muted)
                .kerning(0.8)
                .padding(.horizontal, Theme.Spacing.md)
                .padding(.top, Theme.Spacing.lg)

            switch viewModel.loadState {
            case .loading:
                ProgressView()
                    .frame(maxWidth: .infinity)
                    .padding(Theme.Spacing.lg)

            case .loaded(let txs) where txs.isEmpty:
                Text("No transactions yet.")
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.muted)
                    .frame(maxWidth: .infinity)
                    .padding(Theme.Spacing.lg)

            case .loaded(let txs):
                VStack(spacing: 1) {
                    ForEach(txs) { tx in
                        transactionRow(tx)
                    }
                }
                .background(Theme.Color.surface)
                .cornerRadius(Theme.Radius.md)
                .padding(.horizontal, Theme.Spacing.md)

            case .error(let msg):
                Text(msg)
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
                    .frame(maxWidth: .infinity)
                    .padding(Theme.Spacing.lg)

            case .idle:
                EmptyView()
            }
        }
    }

    private func transactionRow(_ tx: CreditTransaction) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(tx.typeLabel)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.onSurface)
                if let desc = tx.description, !desc.isEmpty {
                    Text(desc)
                        .font(.caption)
                        .foregroundColor(Theme.Color.muted)
                        .lineLimit(1)
                }
            }
            Spacer()
            Text(tx.amountDisplay)
                .font(.subheadline.weight(.bold))
                .foregroundColor(tx.isCredit ? Color(red: 0.18, green: 0.80, blue: 0.44) : Theme.Color.error)
        }
        .padding(.horizontal, Theme.Spacing.md)
        .padding(.vertical, 10)
    }

    // MARK: — Helpers

    private var isLoading: Bool {
        if case .loading = viewModel.loadState { return true }
        return false
    }
}
