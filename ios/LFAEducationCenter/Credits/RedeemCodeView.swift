import SwiftUI

// Redeem a coupon code or invitation code (INV-*).
//
// Smart detection:
//   INV-* prefix → invitation code path (POST /invitation-codes/redeem-authenticated)
//   other        → coupon path (POST /coupons/validate/{code} → POST /coupons/apply)
//
// BONUS_CREDITS coupon → preview shows credits, Confirm Redeem → immediate credit jóváírás
// PURCHASE_DISCOUNT coupon → preview shows info only ("use with invoice")
// Invitation code → preview shows bonus_credits + invited_name, Confirm Redeem
//
// On success: caller should call dashboardVM.reload() to refresh the balance.
struct RedeemCodeView: View {

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var dashboardVM: DashboardViewModel
    @StateObject         private var viewModel  = RedeemCodeViewModel()
    @Environment(\.presentationMode) private var presentationMode

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: Theme.Spacing.lg) {
                    inputSection
                    previewOrResultSection
                    Spacer(minLength: Theme.Spacing.xl)
                }
                .padding(.horizontal, Theme.Spacing.md)
                .padding(.top, Theme.Spacing.md)
            }
            .background(Color(UIColor.systemBackground).ignoresSafeArea())
            .navigationTitle("Redeem a Code")
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
                    .disabled(isWorking)
                }
            }
        }
        .navigationViewStyle(.stack)
    }

    // MARK: — Input section

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            sectionLabel("Enter Code")
            Text("Coupon codes or invitation codes starting with INV-")
                .font(.caption)
                .foregroundColor(Theme.Color.muted)

            HStack(spacing: Theme.Spacing.sm) {
                TextField("e.g. BONUS50 or INV-20260101-XXXXXX", text: $viewModel.codeInput)
                    .autocapitalization(.allCharacters)
                    .disableAutocorrection(true)
                    .padding(.horizontal, Theme.Spacing.sm)
                    .frame(height: 44)
                    .background(Theme.Color.surface)
                    .cornerRadius(Theme.Radius.sm)
                    .disabled(isWorking)

                Button {
                    Task { await viewModel.validate(using: authManager) }
                } label: {
                    if case .validating = viewModel.state {
                        ProgressView().scaleEffect(0.8)
                            .frame(width: 64, height: 44)
                    } else {
                        Text("Check")
                            .font(.subheadline.weight(.semibold))
                            .frame(width: 64, height: 44)
                            .background(Theme.Color.primary)
                            .foregroundColor(.white)
                            .cornerRadius(Theme.Radius.sm)
                    }
                }
                .disabled(viewModel.codeInput.trimmingCharacters(in: .whitespaces).isEmpty || isWorking)
            }
        }
    }

    // MARK: — Preview / result section

    @ViewBuilder
    private var previewOrResultSection: some View {
        switch viewModel.state {
        case .idle, .validating:
            EmptyView()

        case .preview(let preview):
            previewCard(preview)

        case .redeeming:
            HStack(spacing: Theme.Spacing.sm) {
                ProgressView().scaleEffect(0.9)
                Text("Redeeming…")
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.muted)
            }
            .frame(maxWidth: .infinity)
            .padding(Theme.Spacing.lg)

        case .success(let credits, let balance):
            successView(creditsAwarded: credits, newBalance: balance)

        case .error(let message):
            errorView(message: message)
        }
    }

    // MARK: — Preview card

    private func previewCard(_ preview: RedeemPreview) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.md) {
            HStack(spacing: 8) {
                Image(systemName: preview.codeType == .invitationCode ? "gift.fill" : "tag.fill")
                    .foregroundColor(Theme.Color.secondary)
                Text(preview.codeType == .invitationCode ? "INVITATION CODE" : "COUPON CODE")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(Theme.Color.muted)
                    .kerning(0.8)
                Spacer()
            }

            Text(preview.description)
                .font(.subheadline.weight(.semibold))
                .foregroundColor(Theme.Color.onSurface)

            if let name = preview.invitedName {
                Text("Invited: \(name)")
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
            }

            Divider()

            if preview.requiresInvoice {
                purchaseDiscountInfo
            } else if let credits = preview.creditsToAward {
                HStack {
                    Text("Credits to receive")
                        .font(.subheadline)
                        .foregroundColor(Theme.Color.muted)
                    Spacer()
                    Text("+\(credits) CR")
                        .font(.subheadline.weight(.bold))
                        .foregroundColor(Color(red: 0.18, green: 0.80, blue: 0.44))
                }
                confirmRedeemButton(preview: preview)
            }

            Button {
                viewModel.resetToIdle()
            } label: {
                Text("Try a different code")
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Color.surface)
        .cornerRadius(Theme.Radius.md)
    }

    private var purchaseDiscountInfo: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "info.circle")
                .foregroundColor(Theme.Color.primary)
                .padding(.top, 1)
            VStack(alignment: .leading, spacing: 4) {
                Text("Purchase Discount")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.onSurface)
                Text("This coupon applies a discount when you request a credit invoice. Use it in the Request Invoice flow.")
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func confirmRedeemButton(preview: RedeemPreview) -> some View {
        Button {
            Task { await viewModel.confirm(using: authManager) }
        } label: {
            Text("Confirm Redeem")
                .font(.body.weight(.semibold))
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(Theme.Color.primary)
                .foregroundColor(.white)
                .cornerRadius(Theme.Radius.sm)
        }
        .disabled(isWorking)
    }

    // MARK: — Success view

    private func successView(creditsAwarded: Int, newBalance: Int) -> some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundColor(Color(red: 0.18, green: 0.80, blue: 0.44))

            Text("+\(creditsAwarded) CR Added!")
                .font(.title2.weight(.bold))
                .foregroundColor(Theme.Color.onSurface)

            if newBalance > 0 {
                Text("New balance: \(newBalance) CR")
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.muted)
            }

            Button {
                presentationMode.wrappedValue.dismiss()
            } label: {
                Text("Done")
                    .font(.body.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
                    .background(Theme.Color.primary)
                    .foregroundColor(.white)
                    .cornerRadius(Theme.Radius.sm)
            }
        }
        .padding(Theme.Spacing.md)
        .onAppear {
            Task {
                try? await Task.sleep(nanoseconds: 400_000_000)
                await dashboardVM.reload(using: authManager)
            }
        }
    }

    // MARK: — Error view

    private func errorView(message: String) -> some View {
        VStack(spacing: Theme.Spacing.sm) {
            HStack(spacing: 8) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(Theme.Color.error)
                Text(message)
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.onSurface)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer()
            }
            .padding(Theme.Spacing.md)
            .background(Theme.Color.error.opacity(0.08))
            .cornerRadius(Theme.Radius.sm)

            Button {
                viewModel.resetToIdle()
            } label: {
                Text("Try Again")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.primary)
            }
        }
    }

    // MARK: — Helpers

    private var isWorking: Bool {
        switch viewModel.state {
        case .validating, .redeeming: return true
        default: return false
        }
    }

    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold))
            .foregroundColor(Theme.Color.muted)
            .kerning(0.8)
    }
}
