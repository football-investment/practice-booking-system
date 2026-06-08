import SwiftUI
import UIKit

// Full-screen My Academy ID view — suitable for on-site verification.
//
// Layout (scrollable):
//   AcademyIDCardView  — same component shown in RegisterView, now with real user data
//   Divider
//   QR scan panel      — 200×200pt, white background, tap to boost brightness
//   Hint + verify URL
//
// Visual consistency: uses the identical AcademyIDCardView component as the
// registration preview, so the user sees the same card identity both during
// registration and later in "My Academy ID".
//
// Brightness boost:
//   tap QR → UIScreen.main.brightness = 1.0
//   tap again or dismiss → restore original brightness
//
// Privacy: email / phone / user_id / credits are never rendered.
// Offline: fast path uses cached publicToken — QR visible without network.
struct AcademyIDFullScreenView: View {

    @EnvironmentObject private var authManager: AuthManager
    @EnvironmentObject private var dashboardVM: DashboardViewModel
    @StateObject         private var viewModel  = AcademyIDViewModel()

    @Environment(\.presentationMode) private var presentationMode

    @State private var brightnessBoostActive = false
    @State private var originalBrightness: CGFloat = UIScreen.main.brightness

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 0) {
                    cardSection
                    Divider()
                        .background(Theme.Color.secondary.opacity(0.15))
                        .padding(.vertical, Theme.Spacing.lg)
                    qrSection
                    Spacer(minLength: Theme.Spacing.xl)
                }
                .padding(.horizontal, Theme.Spacing.md)
                .padding(.top, Theme.Spacing.lg)
            }
            .background(Color(UIColor.systemBackground).ignoresSafeArea())
            .navigationTitle("My Academy ID")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        restoreBrightness()
                        presentationMode.wrappedValue.dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(Theme.Color.onSurface)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task { await viewModel.reload(using: authManager, profile: dashboardVM.profile) }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(Theme.Color.primary)
                    }
                    .disabled(isReloading)
                }
            }
        }
        .navigationViewStyle(.stack)
        .onAppear { Task { await viewModel.load(using: authManager, profile: dashboardVM.profile) } }
        .onDisappear { restoreBrightness() }
        // If the slow path just lazy-assigned a new Academy ID, reload the dashboard so
        // ProfileView subtitle and ProfileCompletionScore.academyID (+10%) update immediately.
        .onChange(of: viewModel.loadState.isLoaded) { isLoaded in
            guard isLoaded,
                  dashboardVM.profile?.lfaAcademyId == nil,
                  viewModel.loadState.response?.lfaAcademyId != nil else { return }
            Task { await dashboardVM.reload(using: authManager) }
        }
    }

    // MARK: — Academy ID card (same component as RegisterView preview)

    private var cardSection: some View {
        AcademyIDCardView(
            firstName:                cardFirstName,
            lastName:                 cardLastName,
            nickname:                 nil,
            age:                      dashboardVM.profile?.calculatedAge,
            nationality:              "",
            gender:                   nil,
            city:                     nil,
            country:                  nil,
            profileImage:             nil,
            profilePhotoURL:          dashboardVM.profile?.profilePhotoUrl,
            profilePhotoProcessedURL: dashboardVM.profile?.profilePhotoProcessedUrl,
            isVerified:               true,
            lfaAcademyId:             viewModel.loadState.response?.lfaAcademyId
                                      ?? dashboardVM.profile?.lfaAcademyId,
            publicToken:              viewModel.loadState.response?.publicToken
                                      ?? dashboardVM.profile?.publicToken
        )
    }

    // MARK: — QR scan panel (200×200, brightness boost)

    @ViewBuilder
    private var qrSection: some View {
        switch viewModel.loadState {
        case .loading:
            ProgressView()
                .frame(width: 200, height: 200)
                .padding(.bottom, Theme.Spacing.md)

        case .loaded(let response):
            loadedQR(qrData: response.qrData)

        case .error(let msg):
            errorState(message: msg)

        case .idle:
            ProgressView()
                .frame(width: 200, height: 200)
                .padding(.bottom, Theme.Spacing.md)
        }
    }

    private func loadedQR(qrData: String) -> some View {
        VStack(spacing: Theme.Spacing.sm) {
            if let qrImage = QRCodeGenerator.image(from: qrData, scale: 20) {
                Image(uiImage: qrImage)
                    .interpolation(.none)
                    .resizable()
                    .scaledToFit()
                    .frame(width: 200, height: 200)
                    .padding(12)
                    .background(Color.white)
                    .cornerRadius(Theme.Radius.md)
                    .overlay(
                        RoundedRectangle(cornerRadius: Theme.Radius.md)
                            .stroke(Theme.Color.secondary.opacity(0.2), lineWidth: 1)
                    )
                    .contentShape(Rectangle())
                    .onTapGesture { toggleBrightness() }
            }

            HStack(spacing: 5) {
                Image(systemName: brightnessBoostActive ? "sun.max.fill" : "sun.min")
                    .font(.system(size: 11))
                Text(brightnessBoostActive
                     ? "Brightness boosted — tap to restore"
                     : "Tap QR to boost brightness for scanning")
                    .font(.system(size: 11))
            }
            .foregroundColor(brightnessBoostActive ? Theme.Color.secondary : Theme.Color.muted)
            .animation(.easeInOut(duration: 0.2), value: brightnessBoostActive)

            Text(qrData)
                .font(.system(size: 8))
                .foregroundColor(Theme.Color.muted.opacity(0.5))
                .lineLimit(1)
                .truncationMode(.middle)
                .padding(.top, 2)
        }
    }

    private func errorState(message: String) -> some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "qrcode")
                .font(.system(size: 56))
                .foregroundColor(Theme.Color.muted.opacity(0.25))
                .frame(width: 200, height: 200)

            Text(message)
                .font(.subheadline)
                .foregroundColor(Theme.Color.muted)
                .multilineTextAlignment(.center)

            Button {
                Task { await viewModel.reload(using: authManager, profile: dashboardVM.profile) }
            } label: {
                Text("Try Again")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Theme.Color.primary)
                    .padding(.horizontal, Theme.Spacing.lg)
                    .padding(.vertical, 10)
                    .background(Theme.Color.primary.opacity(0.12))
                    .cornerRadius(Theme.Radius.sm)
            }
        }
        .padding(.vertical, Theme.Spacing.lg)
    }

    // MARK: — Brightness

    private func toggleBrightness() {
        brightnessBoostActive.toggle()
        UIScreen.main.brightness = brightnessBoostActive ? 1.0 : originalBrightness
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
    }

    private func restoreBrightness() {
        if brightnessBoostActive {
            UIScreen.main.brightness = originalBrightness
            brightnessBoostActive = false
        }
    }

    // MARK: — Helpers

    private var isReloading: Bool {
        if case .loading = viewModel.loadState { return true }
        return false
    }

    // Split displayName ("R2Test Beta") → firstName ("R2Test") / lastName ("Beta")
    private var cardFirstName: String? {
        guard let name = dashboardVM.profile?.displayName, !name.isEmpty else { return nil }
        return name.split(separator: " ", maxSplits: 1).first.map(String.init)
    }

    private var cardLastName: String? {
        guard let name = dashboardVM.profile?.displayName else { return nil }
        let parts = name.split(separator: " ", maxSplits: 1)
        guard parts.count > 1 else { return nil }
        return String(parts[1])
    }
}
