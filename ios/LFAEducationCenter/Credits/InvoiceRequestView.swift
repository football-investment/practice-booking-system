import SwiftUI

// Credit package invoice request.
//
// User selects a credit package and taps "Request Invoice".
// The backend creates a pending InvoiceRequest and returns a payment reference.
// Credits are added ONLY after an administrator verifies the bank transfer.
//
// Success state is PERSISTENT — user must explicitly copy the reference before closing.
// "Copy Reference & Close" = primary action.
// "Close Without Copying" = secondary, triggers confirmation alert.
//
// API: POST /api/v1/users/request-invoice (Bearer JSON)
struct InvoiceRequestView: View {

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var dashboardVM: DashboardViewModel
    @StateObject         private var viewModel  = InvoiceRequestViewModel()
    @Environment(\.presentationMode) private var presentationMode

    @State private var showCloseWarning = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 0) {
                    headerSection
                    packageSection
                    submitSection
                    Spacer(minLength: Theme.Spacing.xl)
                }
                .padding(.horizontal, Theme.Spacing.md)
                .padding(.top, Theme.Spacing.md)
            }
            .background(Color(UIColor.systemBackground).ignoresSafeArea())
            .navigationTitle("Request Invoice")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    if !isLoading {
                        Button {
                            if case .success = viewModel.state {
                                showCloseWarning = true
                            } else {
                                presentationMode.wrappedValue.dismiss()
                            }
                        } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 14, weight: .semibold))
                                .foregroundColor(Theme.Color.onSurface)
                        }
                    }
                }
            }
            .alert(isPresented: $showCloseWarning) {
                Alert(
                    title: Text("Leave Without Copying?"),
                    message: Text("You will need the payment reference to complete your bank transfer."),
                    primaryButton: .destructive(Text("Leave Anyway")) {
                        presentationMode.wrappedValue.dismiss()
                    },
                    secondaryButton: .cancel(Text("Stay"))
                )
            }
        }
        .navigationViewStyle(.stack)
    }

    // MARK: — Header

    private var headerSection: some View {
        VStack(spacing: Theme.Spacing.sm) {
            Image(systemName: "doc.text.fill")
                .font(.system(size: 36))
                .foregroundColor(Theme.Color.secondary)

            Text("Credit Packages")
                .font(.title3.weight(.bold))
                .foregroundColor(Theme.Color.onSurface)

            Text("Select a package and request an invoice. After completing your bank transfer, an administrator will verify your payment and add credits to your account.")
                .font(.caption)
                .foregroundColor(Theme.Color.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, Theme.Spacing.lg)
    }

    // MARK: — Package picker (hidden when success state shown)

    @ViewBuilder
    private var packageSection: some View {
        if case .success = viewModel.state {
            EmptyView()
        } else {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                Text("SELECT PACKAGE")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(Theme.Color.muted)
                    .kerning(0.8)
                    .padding(.top, Theme.Spacing.sm)

                VStack(spacing: 1) {
                    ForEach(CreditPackage.allCases) { pkg in
                        packageRow(pkg)
                    }
                }
                .background(Theme.Color.surface)
                .cornerRadius(Theme.Radius.md)
            }
        }
    }

    private func packageRow(_ pkg: CreditPackage) -> some View {
        let isSelected = viewModel.selectedPackage == pkg
        return Button { viewModel.selectedPackage = pkg } label: {
            HStack(spacing: Theme.Spacing.sm) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 18))
                    .foregroundColor(isSelected ? Theme.Color.primary : Theme.Color.muted)

                VStack(alignment: .leading, spacing: 2) {
                    Text(pkg.label)
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(Theme.Color.onSurface)
                    Text("\(pkg.creditsLabel) credits")
                        .font(.caption)
                        .foregroundColor(Theme.Color.muted)
                }

                Spacer()

                Text(pkg.priceLabel)
                    .font(.subheadline.weight(.bold))
                    .foregroundColor(isSelected ? Theme.Color.primary : Theme.Color.onSurface)
            }
            .padding(.horizontal, Theme.Spacing.md)
            .padding(.vertical, 12)
            .background(isSelected ? Theme.Color.primary.opacity(0.05) : Color.clear)
        }
        .disabled(isLoading)
    }

    // MARK: — Submit / result section

    @ViewBuilder
    private var submitSection: some View {
        switch viewModel.state {
        case .idle:
            VStack(spacing: Theme.Spacing.sm) {
                selectedSummary
                requestButton
            }
            .padding(.top, Theme.Spacing.md)

        case .loading:
            HStack(spacing: Theme.Spacing.sm) {
                ProgressView().scaleEffect(0.9)
                Text("Creating invoice…")
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.muted)
            }
            .frame(maxWidth: .infinity)
            .padding(Theme.Spacing.lg)

        case .success(let result):
            successView(result: result)

        case .error(let message):
            VStack(spacing: Theme.Spacing.sm) {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(Theme.Color.error)
                    Text(message)
                        .font(.caption)
                        .foregroundColor(Theme.Color.onSurface)
                        .fixedSize(horizontal: false, vertical: true)
                    Spacer()
                }
                .padding(Theme.Spacing.md)
                .background(Theme.Color.error.opacity(0.08))
                .cornerRadius(Theme.Radius.sm)
                .padding(.top, Theme.Spacing.md)

                Button { viewModel.reset() } label: {
                    Text("Try Again")
                        .font(.subheadline.weight(.semibold))
                        .foregroundColor(Theme.Color.primary)
                }
            }
        }
    }

    private var selectedSummary: some View {
        HStack {
            Text("Selected:")
                .font(.subheadline)
                .foregroundColor(Theme.Color.muted)
            Text("\(viewModel.selectedPackage.label) — \(viewModel.selectedPackage.creditsLabel)")
                .font(.subheadline.weight(.semibold))
                .foregroundColor(Theme.Color.onSurface)
            Spacer()
            Text(viewModel.selectedPackage.priceLabel)
                .font(.subheadline.weight(.bold))
                .foregroundColor(Theme.Color.primary)
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Color.surface)
        .cornerRadius(Theme.Radius.sm)
    }

    private var requestButton: some View {
        Button {
            Task { await viewModel.request(using: authManager) }
        } label: {
            Text("Request Invoice")
                .font(.body.weight(.semibold))
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Theme.Color.primary)
                .foregroundColor(.white)
                .cornerRadius(Theme.Radius.sm)
        }
    }

    // MARK: — Persistent success view

    private func successView(result: InvoiceResult) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.md) {

            HStack(spacing: 8) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 22))
                    .foregroundColor(Color(red: 0.18, green: 0.80, blue: 0.44))
                Text("Invoice Created")
                    .font(.headline.weight(.bold))
                    .foregroundColor(Theme.Color.onSurface)
            }

            // Reference highlight card
            VStack(alignment: .leading, spacing: 6) {
                Text("PAYMENT REFERENCE")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(Theme.Color.muted)
                    .kerning(0.8)

                Text(result.paymentReference)
                    .font(.system(size: 15, weight: .bold, design: .monospaced))
                    .foregroundColor(Theme.Color.primary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(Theme.Spacing.md)
            .background(Theme.Color.primary.opacity(0.07))
            .cornerRadius(Theme.Radius.sm)

            // Detail rows
            VStack(spacing: 1) {
                resultRow(label: "Amount",             value: String(format: "€%.2f", result.amountEur))
                resultRow(label: "Credits on approval", value: "\(result.creditAmount) CR")
                resultRow(label: "Status",              value: result.status.capitalized)
                if let date = result.createdAt {
                    resultRow(label: "Requested",       value: formatDate(date))
                }
            }
            .background(Theme.Color.surface)
            .cornerRadius(Theme.Radius.md)

            // Admin notice
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "info.circle")
                    .foregroundColor(Theme.Color.secondary)
                    .padding(.top, 1)
                Text("Include this reference in your bank transfer description. Credits will be added after your payment is verified by an administrator.")
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            // Primary action: Copy & Close
            Button {
                UIPasteboard.general.string = result.paymentReference
                presentationMode.wrappedValue.dismiss()
            } label: {
                Label("Copy Reference & Close", systemImage: "doc.on.doc.fill")
                    .font(.body.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .frame(height: 50)
                    .background(Theme.Color.primary)
                    .foregroundColor(.white)
                    .cornerRadius(Theme.Radius.sm)
            }

            // Secondary action: Close without copying
            Button { showCloseWarning = true } label: {
                Text("Close Without Copying")
                    .font(.caption)
                    .foregroundColor(Theme.Color.muted)
                    .frame(maxWidth: .infinity)
            }
        }
        .padding(Theme.Spacing.md)
        .background(Theme.Color.surface)
        .cornerRadius(Theme.Radius.md)
        .padding(.top, Theme.Spacing.md)
    }

    private func resultRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(Theme.Color.muted)
            Spacer()
            Text(value)
                .font(.subheadline.weight(.semibold))
                .foregroundColor(Theme.Color.onSurface)
        }
        .padding(.horizontal, Theme.Spacing.md)
        .padding(.vertical, 10)
    }

    // MARK: — Helpers

    private var isLoading: Bool {
        if case .loading = viewModel.state { return true }
        return false
    }

    private func formatDate(_ iso: String) -> String {
        // Try with fractional seconds first, then without
        for formatOptions: ISO8601DateFormatter.Options in [
            [.withInternetDateTime, .withFractionalSeconds],
            [.withInternetDateTime]
        ] {
            let f = ISO8601DateFormatter()
            f.formatOptions = formatOptions
            if let date = f.date(from: iso) {
                let out = DateFormatter()
                out.dateStyle = .medium
                out.timeStyle = .none
                return out.string(from: date)
            }
        }
        return String(iso.prefix(10))
    }
}
