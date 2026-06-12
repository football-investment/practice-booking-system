import ARKit
import SwiftUI

// kDebugSpikeCompletedAtKey is defined in BiometricAutoCapture.swift (DEBUG only).

// Production liveness view — ARKit auto-capture, backend-integrated (PR-iOS-2).
//
// What it does:
//   - Runs ARFaceTrackingView (TrueDepth camera feed + ARKit tracking)
//   - Guides user through 7 gestures with instruction + icon
//   - After 7/7: shows neutral recapture progress, then uploads photo + submits liveness
//   - On backend success: shows confirmed card and calls onDismiss
//   - Shows non-TrueDepth fallback message on unsupported hardware
//
// What it does NOT do:
//   - Does NOT store photos on the iOS device after upload
//   - Does NOT set biometric_verified status locally
//   - Does NOT expose face_match_score in any element
//   - Does NOT show debug overlay in Release / TestFlight builds
struct SpikeLivenessView: View {

    @EnvironmentObject private var authManager:  AuthManager
    @EnvironmentObject private var dashboardVM:  DashboardViewModel

    @StateObject private var vm: SpikeLivenessViewModel

    private let onDismiss: () -> Void

    init(onDismiss: @escaping () -> Void) {
        // BiometricService is wired at init via the captured closures in onAppear.
        // We use a temporary nil-service ViewModel here; the real service is injected
        // in onAppear once authManager is available via @EnvironmentObject.
        _vm = StateObject(wrappedValue: SpikeLivenessViewModel())
        self.onDismiss = onDismiss
    }

    var body: some View {
        NavigationView {
            ZStack(alignment: .bottom) {
                if ARFaceTrackingView.isDeviceSupported {
                    ARFaceTrackingView(viewModel: vm)
                        .ignoresSafeArea()
                } else {
                    unsupportedDeviceView
                }
                if ARFaceTrackingView.isDeviceSupported {
                    overlayLayer
                }
            }
            .navigationTitle("Liveness Test")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { closeToolbarItem }
        }
        .onAppear {
            // Inject real BiometricService now that authManager is available.
            let service = BiometricService(auth: authManager)
            vm.injectService(service)
            vm.onFlowComplete = {
                Task { @MainActor in
#if DEBUG
                    UserDefaults.standard.set(Date().timeIntervalSince1970,
                                             forKey: kDebugSpikeCompletedAtKey)
#endif
                    // First reload: picks up reference_pending immediately.
                    await dashboardVM.reload(using: authManager)

                    // Delayed reload: waits for the Celery embedding task
                    // (5 s countdown + ~1 s processing) then re-fetches to
                    // show the verified badge without requiring manual refresh.
                    try? await Task.sleep(nanoseconds: 8_000_000_000)  // 8 s
                    await dashboardVM.reload(using: authManager)
                }
            }
            vm.start()
#if DEBUG
            let build   = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "?"
            let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
            print("[SPIKE] SpikeLivenessView appeared — \(kSpikeLabel) — v\(version)(\(build))")
#endif
        }
        .navigationViewStyle(.stack)
    }

    // MARK: — Main overlay

    private var overlayLayer: some View {
        VStack(spacing: 12) {
            progressStepBar
            stateCard
#if DEBUG
            debugOverlay
#endif
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 40)
    }

    // MARK: — Step progress bar

    private var progressStepBar: some View {
        VStack(spacing: 4) {
            Text("\(min(vm.currentStepIndex + 1, vm.totalSteps)) / \(vm.totalSteps)")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.white)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.3)).frame(height: 5)
                    Capsule()
                        .fill(Color.white)
                        .frame(
                            width: geo.size.width *
                                   CGFloat(vm.currentStepIndex) / CGFloat(vm.totalSteps),
                            height: 5
                        )
                        .animation(.easeInOut(duration: 0.25), value: vm.currentStepIndex)
                }
            }
            .frame(height: 5)
        }
    }

    // MARK: — State card

    @ViewBuilder
    private var stateCard: some View {
        switch vm.stepState {
        case .noFace:
            instructionCard(
                icon: vm.currentGesture?.systemIcon ?? "faceid",
                instruction: vm.currentGesture?.instruction ?? "Position your face",
                hint: "Position your face in the frame",
                borderColor: .white.opacity(0.6)
            )

        case .detecting:
            instructionCard(
                icon: vm.currentGesture?.systemIcon ?? "faceid",
                instruction: vm.currentGesture?.instruction ?? "",
                hint: nil,
                borderColor: .white.opacity(0.6)
            )

        case .stabilizing(let progress):
            VStack(spacing: 8) {
                instructionCard(
                    icon: vm.currentGesture?.systemIcon ?? "faceid",
                    instruction: vm.currentGesture?.instruction ?? "",
                    hint: "Hold...",
                    borderColor: .yellow
                )
                stabilizerBar(progress: progress)
            }

        case .confirmed:
            confirmedStepCard

        case .timedOut:
            timedOutCard

        case .gestureDone:
            instructionCard(
                icon: "face.smiling",
                instruction: "Look straight at the camera",
                hint: "Hold neutral pose for reference photo",
                borderColor: .white.opacity(0.8)
            )

        case .neutralRecapture(let progress):
            VStack(spacing: 8) {
                instructionCard(
                    icon: "face.smiling",
                    instruction: "Look straight at the camera",
                    hint: "Hold still — capturing reference photo...",
                    borderColor: Color(red: 0.3, green: 0.85, blue: 0.95)
                )
                stabilizerBar(progress: progress)
            }

        case .uploading:
            progressCard(
                icon: "arrow.up.circle",
                title: "Uploading photo...",
                tint: .blue
            )

        case .submittingLiveness:
            progressCard(
                icon: "checkmark.shield",
                title: "Verifying liveness...",
                tint: .blue
            )

        case .backendConfirmed:
            backendConfirmedCard

        case .uploadFailed(let message):
            uploadFailedCard(message: message)
        }
    }

    // MARK: — Card builders

    private func instructionCard(
        icon: String,
        instruction: String,
        hint: String?,
        borderColor: Color
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 24))
                .foregroundColor(.white)
                .frame(width: 36)
            VStack(alignment: .leading, spacing: 2) {
                Text(instruction)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundColor(.white)
                if let hint {
                    Text(hint)
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.7))
                }
            }
            Spacer()
        }
        .padding(14)
        .background(Color.black.opacity(0.55))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(borderColor, lineWidth: 2))
        .animation(.easeInOut(duration: 0.2), value: borderColor.description)
    }

    private func stabilizerBar(progress: Double) -> some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.yellow.opacity(0.3)).frame(height: 8)
                Capsule()
                    .fill(Color.yellow)
                    .frame(width: geo.size.width * CGFloat(progress), height: 8)
                    .animation(.linear(duration: 0.05), value: progress)
            }
        }
        .frame(height: 8)
    }

    private func progressCard(icon: String, title: String, tint: Color) -> some View {
        HStack(spacing: 12) {
            ProgressView()
                .progressViewStyle(.circular)
                .frame(width: 36)
                .colorMultiply(.white)
            Text(title)
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.white)
            Spacer()
        }
        .padding(14)
        .background(Color.black.opacity(0.55))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(tint, lineWidth: 2))
    }

    private var confirmedStepCard: some View {
        HStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 24))
                .foregroundColor(Theme.Color.primary)
                .frame(width: 36)
            Text("Confirmed")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(.white)
            Spacer()
        }
        .padding(14)
        .background(Color.black.opacity(0.55))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.Color.primary, lineWidth: 2))
        .onAppear { UIImpactFeedbackGenerator(style: .medium).impactOccurred() }
    }

    private var backendConfirmedCard: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 48))
                .foregroundColor(Theme.Color.primary)
            Text("Liveness verified")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
            Text("Your biometric data has been submitted for review.\nNo raw sensor data was transmitted.")
                .font(.system(size: 13))
                .foregroundColor(.white.opacity(0.8))
                .multilineTextAlignment(.center)
            Button {
                onDismiss()
            } label: {
                Text("Continue")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(Color.white)
                    .cornerRadius(8)
            }
        }
        .padding(20)
        .background(Color.black.opacity(0.7))
        .cornerRadius(14)
        .onAppear {
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        }
    }

    private func uploadFailedCard(message: String) -> some View {
        VStack(spacing: 10) {
            HStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 20))
                    .foregroundColor(Theme.Color.warning)
                    .frame(width: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Submission failed")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.white)
                    Text(message)
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
            }
            Button {
                vm.retryUpload()
            } label: {
                Text("Try again (\(vm.retryCount + 1))")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color.white)
                    .cornerRadius(8)
            }
        }
        .padding(14)
        .background(Color.black.opacity(0.65))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.Color.warning, lineWidth: 2))
    }

    private var timedOutCard: some View {
        VStack(spacing: 10) {
            HStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 20))
                    .foregroundColor(Theme.Color.warning)
                    .frame(width: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Gesture not detected")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.white)
                    Text("Make sure your face is well lit and visible.")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
            }
            Button {
                vm.retryCurrentStep()
            } label: {
                Text("Try again (\(vm.retryCount + 1))")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.black)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color.white)
                    .cornerRadius(8)
            }
        }
        .padding(14)
        .background(Color.black.opacity(0.65))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.Color.warning, lineWidth: 2))
    }

    // MARK: — Non-TrueDepth fallback

    private var unsupportedDeviceView: some View {
        VStack(spacing: Theme.Spacing.lg) {
            Image(systemName: "faceid")
                .font(.system(size: 52))
                .foregroundColor(Theme.Color.warning)
            Text("TrueDepth camera required")
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(Theme.Color.onSurface)
                .multilineTextAlignment(.center)
            Text("ARKit face tracking is only available on iPhone X and later.\n\nThe standard biometric flow will be used on this device.")
                .font(.system(size: 14))
                .foregroundColor(Theme.Color.muted)
                .multilineTextAlignment(.center)
            Button(action: onDismiss) {
                Text("Close")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(Theme.Color.primary)
                    .cornerRadius(8)
            }
        }
        .padding(Theme.Spacing.md)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(UIColor.systemBackground))
    }

    // MARK: — Toolbar

    private var closeToolbarItem: some ToolbarContent {
        ToolbarItem(placement: .navigationBarLeading) {
            Button(action: onDismiss) {
                Image(systemName: "xmark")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(Theme.Color.onSurface)
            }
        }
    }

    // MARK: — Debug overlay (DEBUG builds only)

#if DEBUG
    private var debugOverlay: some View {
        let v         = vm.debugValues
        let build     = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "?"
        let version   = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
        let truedepth = ARFaceTrackingView.isDeviceSupported

        let holdPct: Int = {
            switch vm.stepState {
            case .stabilizing(let p):     return Int(p * 100)
            case .neutralRecapture(let p): return Int(p * 100)
            case .confirmed, .backendConfirmed: return 100
            default: return 0
            }
        }()

        let stateLabel: String = {
            switch vm.stepState {
            case .gestureDone:       return "gestureDone"
            case .neutralRecapture:  return "neutralRecapture"
            case .uploading:         return "uploading"
            case .submittingLiveness: return "submittingLiveness"
            case .backendConfirmed:  return "backendConfirmed"
            case .uploadFailed(let m): return "uploadFailed:\(m.prefix(20))"
            default:                 return ""
            }
        }()

        let lines: [String] = [
            "\(kSpikeLabel)  TrueDepth:\(truedepth ? "YES" : "NO")  v\(version)(\(build))",
            "step \(vm.currentStepIndex + 1)/\(vm.totalSteps): \(vm.currentGesture?.debugLabel ?? stateLabel)  detected: \(v.detected ? "YES✓" : "no")",
            v.gestureDetail,
            String(format: "yaw: %+.3f  pitch: %+.3f  hold: \(holdPct)%%", v.yaw, v.pitch),
            String(format: "blinkL: %.2f  blinkR: %.2f", v.blinkLeft, v.blinkRight),
            String(format: "smileL: %.2f  smileR: %.2f  sqntAvg: %.2f",
                   v.smileLeft, v.smileRight, (v.squintLeft + v.squintRight) / 2),
        ].filter { !$0.isEmpty }

        return VStack(alignment: .leading, spacing: 2) {
            Text("⚙ SPIKE DEBUG")
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(.orange)
            ForEach(lines, id: \.self) { line in
                Text(line)
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.orange.opacity(0.9))
            }
        }
        .padding(6)
        .background(Color.black.opacity(0.08))
        .cornerRadius(6)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
#endif
}
