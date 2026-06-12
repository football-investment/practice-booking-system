import ARKit
import Foundation

// State machine for the ARKit auto-capture spike liveness flow.
//
// Privacy rules (enforced structurally):
//   - Raw angle/blendshape values are @Published only in #if DEBUG builds.
//   - In Release builds, the debugValues property does not exist; the fields
//     are absent from binary and cannot be read or logged.
//   - No data is sent to the backend from this ViewModel.
//   - No images are stored on disk.
//
// Backend upload and image persistence are Phase 3 items — out of scope for spike.
@MainActor
final class SpikeLivenessViewModel: ObservableObject {

    // MARK: — Step state

    enum StepState: Equatable {
        case detecting                  // face visible, not yet at threshold
        case stabilizing(Double)        // threshold met, holding [0.0…1.0]
        case confirmed                  // gesture accepted — showing visual confirmation
        case timedOut                   // step timeout reached
        case complete                   // all gestures done
        case noFace                     // ARSession running but no face anchor present

        static func == (lhs: StepState, rhs: StepState) -> Bool {
            switch (lhs, rhs) {
            case (.detecting, .detecting),
                 (.confirmed, .confirmed),
                 (.timedOut, .timedOut),
                 (.complete, .complete),
                 (.noFace, .noFace):
                return true
            case (.stabilizing(let a), .stabilizing(let b)):
                return abs(a - b) < 0.01
            default:
                return false
            }
        }
    }

    // MARK: — Published state

    @Published private(set) var currentStepIndex: Int       = 0
    @Published private(set) var stepState:         StepState = .noFace
    @Published private(set) var retryCount:         Int      = 0

    // Raw sensor values — only compiled into DEBUG builds.
    // These power the calibration overlay and are never logged in Release.
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
        // Gesture-specific threshold line: "target yaw > +0.15  yawPassed: YES"
        var gestureDetail: String = ""
    }
    @Published private(set) var debugValues = DebugValues()
#endif

    // MARK: — Callbacks

    var onFlowComplete: (() -> Void)?

    // MARK: — Internals

    private let sequence:   [FaceGestureType]
    private let detector:   FaceGestureDetector
    private let stabilizer: GestureStabilizer
    private var timeoutTask: Task<Void, Never>?

    static let defaultSequence: [FaceGestureType] = [
        .neutral, .headLeft, .headRight, .chinUp, .blinkRight, .blinkLeft, .smile
    ]

    init(
        sequence:   [FaceGestureType]  = SpikeLivenessViewModel.defaultSequence,
        thresholds: FacePoseThresholds = .production
    ) {
        self.sequence   = sequence
        self.detector   = FaceGestureDetector(thresholds: thresholds)
        self.stabilizer = GestureStabilizer(holdDurationMs: thresholds.holdDurationMs)
        stabilizer.onConfirmed = { [weak self] in self?.onGestureConfirmed() }
    }

    // MARK: — Public interface

    var currentGesture: FaceGestureType? {
        guard currentStepIndex < sequence.count else { return nil }
        return sequence[currentStepIndex]
    }

    var totalSteps: Int { sequence.count }

    func start() {
        currentStepIndex = 0
        retryCount       = 0
        stabilizer.reset()
        stepState        = .noFace
        startTimeout()
    }

    // Called by ARFaceTrackingView on every ARSession delegate update (~60 FPS).
    // This is the only entry point for sensor data — nothing is stored.
    func update(with anchor: FaceAnchorInput) {
        guard let gesture = currentGesture else { return }
        guard stepState != .confirmed, stepState != .complete else { return }

        let detected = detector.detect(gesture: gesture, from: anchor)

#if DEBUG
        updateDebugValues(from: anchor, detected: detected)
#endif

        stabilizer.update(detected: detected)

        switch (detected, stabilizer.isDetecting, stabilizer.isConfirmed) {
        case (_, _, true):
            break   // stabilizer fires onConfirmed — handled in onGestureConfirmed()
        case (_, true, _):
            stepState = .stabilizing(stabilizer.holdProgress)
        case (true, false, _):
            stepState = .stabilizing(0.0)
        default:
            stepState = .detecting
        }
    }

    // Called when ARSession loses face tracking.
    func faceTrackingLost() {
        guard stepState != .confirmed, stepState != .complete else { return }
        stepState = .noFace
        stabilizer.reset()
    }

    // Manual retry after timeout — user taps the retry button.
    func retryCurrentStep() {
        guard stepState == .timedOut else { return }
        retryCount += 1
        stabilizer.reset()
        stepState = .noFace
        startTimeout()
    }

    // MARK: — Private

    private func onGestureConfirmed() {
        timeoutTask?.cancel()
        stepState = .confirmed
        Task {
            try? await Task.sleep(nanoseconds: 700_000_000)  // 700 ms visual confirmation
            guard !Task.isCancelled else { return }
            advanceStep()
        }
    }

    private func advanceStep() {
        currentStepIndex += 1
        if currentStepIndex >= sequence.count {
            stepState = .complete
            onFlowComplete?()
        } else {
            stabilizer.reset()
            stepState = .noFace
            startTimeout()
        }
    }

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
            let pass = e.x > t.yawLeft
            detail = String(format: "target yaw > +%.3f  yawPassed: %@", t.yawLeft, pass ? "YES" : "NO")
        case .headRight:
            let pass = e.x < -t.yawRight
            detail = String(format: "target yaw < -%.3f  yawPassed: %@", t.yawRight, pass ? "YES" : "NO")
        case .chinUp:
            let pass = e.y < -t.pitchUp
            detail = String(format: "target pitch < -%.3f  pitchPassed: %@", t.pitchUp, pass ? "YES" : "NO")
        case .blinkRight:
            let pass = br > t.blinkMin && bl < t.blinkOtherMax
            detail = String(format: "blinkR>%.2f:%@  blinkL<%.2f:%@",
                            t.blinkMin, br > t.blinkMin ? "✓" : "✗",
                            t.blinkOtherMax, bl < t.blinkOtherMax ? "✓" : "✗")
        case .blinkLeft:
            let pass2 = bl > t.blinkMin && br < t.blinkOtherMax
            detail = String(format: "blinkL>%.2f:%@  blinkR<%.2f:%@",
                            t.blinkMin, bl > t.blinkMin ? "✓" : "✗",
                            t.blinkOtherMax, br < t.blinkOtherMax ? "✓" : "✗")
        case .smile:
            let avg = (sl + sr) / 2
            let pass3 = avg > t.smileAvg
            detail = String(format: "smileAvg>%.2f  avg=%.2f  %@", t.smileAvg, avg, pass3 ? "YES" : "NO")
        case .none:
            detail = ""
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
