import ARKit
import Foundation

// State machine for the ARKit auto-capture liveness flow — production-integrated (PR-iOS-2).
//
// Privacy rules (enforced structurally):
//   - Raw angle/blendshape values are @Published only in #if DEBUG builds.
//   - In Release builds, the debugValues property does not exist.
//   - No raw sensor data is sent to the backend (liveness_metadata only has
//     the five allowed fields: challengeVersion, stepsCompleted, totalDurationMs,
//     retryCount, failureReason).
//   - face_match_score never appears in any model, log, or UI element.
//   - Image bytes are captured once (neutral recapture after 7/7), uploaded,
//     and then immediately discarded — not stored on-device.
//
// Flow after 7/7 gesture confirmation:
//   .gestureDone → (400 ms neutral hold) → .neutralRecapture
//   → snapshotProvider() → .uploading → POST /me/biometric-photo
//   → .submittingLiveness → POST /me/biometric-liveness
//   → .backendConfirmed(status) → caller calls onFlowComplete
//   Error at any step → .uploadFailed(error) with retry
@MainActor
final class SpikeLivenessViewModel: ObservableObject {

    // MARK: — Step state

    enum StepState: Equatable {
        case detecting                        // face visible, threshold not yet met
        case stabilizing(Double)              // threshold met, holding [0.0…1.0]
        case confirmed                        // gesture accepted — brief visual flash
        case timedOut                         // step timeout reached
        case noFace                           // ARSession running, no face anchor
        // Post-7/7 states:
        case gestureDone                      // all 7 gestures confirmed; awaiting neutral recapture
        case neutralRecapture(Double)         // holding neutral for reference snapshot [0.0…1.0]
        case uploading                        // JPEG uploading to /me/biometric-photo
        case submittingLiveness               // calling /me/biometric-liveness
        case backendConfirmed(BiometricVerificationStatus) // success
        case uploadFailed(String)             // error message, retryable

        static func == (lhs: StepState, rhs: StepState) -> Bool {
            switch (lhs, rhs) {
            case (.detecting, .detecting), (.confirmed, .confirmed),
                 (.timedOut, .timedOut), (.noFace, .noFace),
                 (.gestureDone, .gestureDone), (.uploading, .uploading),
                 (.submittingLiveness, .submittingLiveness):
                return true
            case (.stabilizing(let a), .stabilizing(let b)):    return abs(a - b) < 0.01
            case (.neutralRecapture(let a), .neutralRecapture(let b)): return abs(a - b) < 0.01
            case (.backendConfirmed, .backendConfirmed):         return true
            case (.uploadFailed(let a), .uploadFailed(let b)):   return a == b
            default: return false
            }
        }
    }

    // MARK: — Published state

    @Published private(set) var currentStepIndex: Int       = 0
    @Published private(set) var stepState:         StepState = .noFace
    @Published private(set) var retryCount:         Int      = 0

    // Raw sensor values — only compiled into DEBUG builds.
#if DEBUG
    struct DebugValues {
        var yaw:         Float  = 0
        var pitch:       Float  = 0
        var blinkLeft:   Float  = 0
        var blinkRight:  Float  = 0
        var smileLeft:   Float  = 0
        var smileRight:  Float  = 0
        var squintLeft:  Float  = 0
        var squintRight: Float  = 0
        var detected:    Bool   = false
        var gestureDetail: String = ""
    }
    @Published private(set) var debugValues = DebugValues()
#endif

    // MARK: — Callbacks

    var onFlowComplete: (() -> Void)?

    // Set by ARFaceTrackingView.Coordinator once the sceneView is ready.
    // Returns JPEG Data of the current frame, or nil if capture fails.
    // Main-thread only (ARSCNView.snapshot() requirement).
    var snapshotProvider: (() -> Data?)?

    // MARK: — Internals

    private let sequence:   [FaceGestureType]
    private let detector:   FaceGestureDetector
    private let stabilizer: GestureStabilizer
    private var timeoutTask: Task<Void, Never>?

    // Baseline yaw captured at neutral step confirmation — used for relative
    // headLeft/headRight detection so device tilt doesn't distort thresholds.
    private var baselineYaw:  Float = 0
    private var lastFrameYaw: Float = 0

    // Neutral recapture stabilizer: 400 ms hold in neutral pose after 7/7.
    private let neutralRecaptureStabilizer: GestureStabilizer

    // Challenge start time — used to compute totalDurationMs for liveness_metadata.
    private var challengeStartDate: Date = Date()

    // Biometric service — injected via injectService() from SpikeLivenessView.onAppear.
    // nil until injected; production flow always injects before gestures complete.
    private var biometricService: BiometricService?

    static let defaultSequence: [FaceGestureType] = [
        .neutral, .headLeft, .headRight, .chinUp, .blinkRight, .blinkLeft, .smile
    ]

    init(
        sequence:         [FaceGestureType]  = SpikeLivenessViewModel.defaultSequence,
        thresholds:       FacePoseThresholds = .production,
        biometricService: BiometricService?  = nil
    ) {
        self.sequence         = sequence
        self.detector         = FaceGestureDetector(thresholds: thresholds)
        self.stabilizer       = GestureStabilizer(holdDurationMs: thresholds.holdDurationMs)
        self.biometricService = biometricService
        self.neutralRecaptureStabilizer = GestureStabilizer(holdDurationMs: 400)
        stabilizer.onConfirmed = { [weak self] in self?.onGestureConfirmed() }
        neutralRecaptureStabilizer.onConfirmed = { [weak self] in self?.onNeutralRecaptureConfirmed() }
    }

    // MARK: — Public interface

    // Called from SpikeLivenessView.onAppear once authManager is available.
    // Idempotent: subsequent calls after first are ignored.
    func injectService(_ service: BiometricService) {
        guard biometricService == nil else { return }
        biometricService = service
    }

    var currentGesture: FaceGestureType? {
        guard currentStepIndex < sequence.count else { return nil }
        return sequence[currentStepIndex]
    }

    var totalSteps: Int { sequence.count }

    func start() {
        currentStepIndex   = 0
        retryCount         = 0
        baselineYaw        = 0
        lastFrameYaw       = 0
        challengeStartDate = Date()
        stabilizer.reset()
        neutralRecaptureStabilizer.reset()
        stepState = .noFace
        startTimeout()
    }

    // Called by ARFaceTrackingView on every ARSession delegate update (~60 FPS).
    func update(with anchor: FaceAnchorInput) {
        lastFrameYaw = anchor.faceEulerAngles.x

        // Post-7/7: handle neutral recapture phase.
        if case .gestureDone = stepState {
            updateNeutralRecapture(anchor)
            return
        }
        if case .neutralRecapture = stepState {
            updateNeutralRecapture(anchor)
            return
        }

        guard let gesture = currentGesture else { return }
        guard stepState != .confirmed, stepState != .uploading,
              stepState != .submittingLiveness else { return }
        if case .backendConfirmed = stepState { return }
        if case .uploadFailed = stepState { return }

        let detected = detector.detect(gesture: gesture, from: anchor, baselineYaw: baselineYaw)

#if DEBUG
        updateDebugValues(from: anchor, detected: detected)
#endif

        stabilizer.update(detected: detected)

        switch (detected, stabilizer.isDetecting, stabilizer.isConfirmed) {
        case (_, _, true):
            break   // handled by onGestureConfirmed()
        case (_, true, _):
            stepState = .stabilizing(stabilizer.holdProgress)
        case (true, false, _):
            stepState = .stabilizing(0.0)
        default:
            stepState = .detecting
        }
    }

    func faceTrackingLost() {
        guard stepState != .confirmed,
              stepState != .uploading,
              stepState != .submittingLiveness else { return }
        if case .backendConfirmed = stepState { return }
        if case .uploadFailed = stepState { return }
        stepState = .noFace
        stabilizer.reset()
    }

    func retryCurrentStep() {
        guard case .timedOut = stepState else { return }
        retryCount += 1
        stabilizer.reset()
        stepState = .noFace
        startTimeout()
    }

    // Called from SpikeLivenessView when user taps "Retry" after upload failure.
    func retryUpload() {
        guard case .uploadFailed = stepState else { return }
        retryCount += 1
        stepState = .gestureDone
        neutralRecaptureStabilizer.reset()
    }

    // MARK: — Private: gesture confirmation

    private func onGestureConfirmed() {
        if sequence[currentStepIndex] == .neutral {
            baselineYaw = lastFrameYaw
        }
        timeoutTask?.cancel()
        stepState = .confirmed
        Task {
            try? await Task.sleep(nanoseconds: 700_000_000)
            guard !Task.isCancelled else { return }
            advanceStep()
        }
    }

    private func advanceStep() {
        currentStepIndex += 1
        if currentStepIndex >= sequence.count {
            // All gestures done — begin neutral recapture for reference snapshot.
            stabilizer.reset()
            neutralRecaptureStabilizer.reset()
            stepState = .gestureDone
            timeoutTask?.cancel()
        } else {
            stabilizer.reset()
            stepState = .noFace
            startTimeout()
        }
    }

    // MARK: — Private: neutral recapture (post-7/7)

    private func updateNeutralRecapture(_ anchor: FaceAnchorInput) {
        let isNeutral = detector.detect(gesture: .neutral, from: anchor, baselineYaw: 0)

#if DEBUG
        updateDebugValues(from: anchor, detected: isNeutral)
#endif

        neutralRecaptureStabilizer.update(detected: isNeutral)

        switch (isNeutral, neutralRecaptureStabilizer.isDetecting, neutralRecaptureStabilizer.isConfirmed) {
        case (_, _, true):
            break   // handled by onNeutralRecaptureConfirmed()
        case (_, true, _):
            stepState = .neutralRecapture(neutralRecaptureStabilizer.holdProgress)
        case (true, false, _):
            stepState = .neutralRecapture(0.0)
        default:
            stepState = .gestureDone
        }
    }

    private func onNeutralRecaptureConfirmed() {
        guard let jpeg = snapshotProvider?() else {
            stepState = .uploadFailed(BiometricClientError.photoCaptureFailure.userFacingMessage)
            return
        }
        startUploadFlow(jpeg: jpeg)
    }

    // MARK: — Private: upload + liveness submit

    private func startUploadFlow(jpeg: Data) {
        stepState = .uploading
        let durationMs = Int(Date().timeIntervalSince(challengeStartDate) * 1000)
        let retries    = retryCount

        Task {
            do {
                guard let service = biometricService else {
                    stepState = .uploadFailed("Biometric service unavailable.")
                    return
                }

                // 1. Upload photo
                let filename = try await service.uploadBiometricPhoto(imageData: jpeg)

                stepState = .submittingLiveness

                // 2. Submit liveness
                let metadata = BiometricLivenessMetadata(
                    challengeVersion: kBiometricChallengeVersion,
                    stepsCompleted:   sequence.map(\.rawValue),
                    totalDurationMs:  min(durationMs, 120_000),
                    retryCount:       retries,
                    failureReason:    nil
                )
                let result = try await service.submitLiveness(
                    metadata: metadata,
                    photoFilename: filename
                )

                // 3. Success
                stepState = .backendConfirmed(result)
                onFlowComplete?()

            } catch let err as BiometricClientError {
                // 409 livenessAlreadySubmitted is treated as success (idempotent).
                if case .livenessAlreadySubmitted = err {
                    let synthetic = BiometricVerificationStatus(
                        faceMatchStatus:          "reference_pending",
                        faceReferencePhotoStatus: "onboarding_liveness_capture",
                        hasBiometricConsent:      true,
                        manualReviewRequired:     false
                    )
                    stepState = .backendConfirmed(synthetic)
                    onFlowComplete?()
                } else {
                    stepState = .uploadFailed(err.userFacingMessage)
                }
            } catch {
                stepState = .uploadFailed(BiometricClientError.from(error).userFacingMessage)
            }
        }
    }

    // MARK: — Private: timeout

    private func startTimeout() {
        timeoutTask?.cancel()
        let ms = detector.thresholds.stepTimeoutMs
        timeoutTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(ms) * 1_000_000)
            guard !Task.isCancelled else { return }
            self?.stepState = .timedOut
        }
    }

    // MARK: — Debug values (DEBUG only)

#if DEBUG
    private func updateDebugValues(from anchor: FaceAnchorInput, detected: Bool) {
        let e  = anchor.faceEulerAngles
        let bs = anchor.faceBlendShapes
        let t  = detector.thresholds
        let bl = bs[.eyeBlinkLeft]?.floatValue   ?? 0
        let br = bs[.eyeBlinkRight]?.floatValue  ?? 0
        let sl = bs[.mouthSmileLeft]?.floatValue  ?? 0
        let sr = bs[.mouthSmileRight]?.floatValue ?? 0
        let detail: String
        switch currentGesture {
        case .neutral:
            let yawOK   = abs(e.x) < t.neutralYaw
            let pitchOK = abs(e.y) < t.neutralPitch
            detail = String(format: "|yaw|<%.2f:%@  |pitch|<%.2f:%@",
                            t.neutralYaw,  yawOK   ? "✓" : "✗",
                            t.neutralPitch, pitchOK ? "✓" : "✗")
        case .headLeft:
            let target = baselineYaw + t.yawLeft
            let pass = e.x > target
            detail = String(format: "target yaw > %.3f (base%.3f+%.3f)  yawPassed: %@",
                            target, baselineYaw, t.yawLeft, pass ? "YES" : "NO")
        case .headRight:
            let target = baselineYaw - t.yawRight
            let pass = e.x < target
            detail = String(format: "target yaw < %.3f (base%.3f−%.3f)  yawPassed: %@",
                            target, baselineYaw, t.yawRight, pass ? "YES" : "NO")
        case .chinUp:
            let pass = e.y < -t.pitchUp
            detail = String(format: "target pitch < -%.3f  pitchPassed: %@", t.pitchUp, pass ? "YES" : "NO")
        case .blinkRight:
            let pass = br > t.blinkMin && bl < t.blinkOtherMax
            detail = String(format: "blinkR>%.2f:%@  blinkL(guard)<%.2f:%@",
                            t.blinkMin, br > t.blinkMin ? "✓" : "✗",
                            t.blinkOtherMax, bl < t.blinkOtherMax ? "✓" : "✗")
        case .blinkLeft:
            let pass2 = bl > t.blinkMin && br < t.blinkOtherMax
            detail = String(format: "blinkL>%.2f:%@  blinkR(guard)<%.2f:%@",
                            t.blinkMin, bl > t.blinkMin ? "✓" : "✗",
                            t.blinkOtherMax, br < t.blinkOtherMax ? "✓" : "✗")
        case .smile:
            let avg = (sl + sr) / 2
            let pass3 = avg > t.smileAvg
            detail = String(format: "smileAvg>%.2f  avg=%.2f  %@", t.smileAvg, avg, pass3 ? "YES" : "NO")
        case .none:
            // Neutral recapture phase
            let yawOK   = abs(e.x) < t.neutralYaw
            let pitchOK = abs(e.y) < t.neutralPitch
            detail = String(format: "[recapture] |yaw|<%.2f:%@  |pitch|<%.2f:%@",
                            t.neutralYaw,  yawOK   ? "✓" : "✗",
                            t.neutralPitch, pitchOK ? "✓" : "✗")
        }
        debugValues = DebugValues(
            yaw:          e.x,
            pitch:        e.y,
            blinkLeft:    bl,
            blinkRight:   br,
            smileLeft:    sl,
            smileRight:   sr,
            squintLeft:   bs[.cheekSquintLeft]?.floatValue  ?? 0,
            squintRight:  bs[.cheekSquintRight]?.floatValue ?? 0,
            detected:     detected,
            gestureDetail: detail
        )
    }
#endif
}
