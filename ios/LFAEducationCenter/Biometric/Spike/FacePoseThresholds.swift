import Foundation

// All detection thresholds in one calibration struct.
//
// These are PROVISIONAL first-prototype values based on published ARKit usage patterns.
// They MUST be validated against physical measurements during the Phase 0 calibration
// session before the spike can be declared stable.
//
// How to calibrate: run the spike with kBiometricAutoCaptureSpikeEnabled = true,
// watch the #if DEBUG overlay, record raw yaw/pitch/blendshape values per gesture
// across 5+ test subjects and 3 lighting conditions, then update these defaults.
//
// Convention (empirically verify with calibration — see ARFaceTrackingView):
//   eulerAngles.x = yaw:   positive when head turns to user's LEFT
//   eulerAngles.y = pitch: positive when chin raises (face tilts upward)
struct FacePoseThresholds {

    // MARK: — Head pose (radians)

    /// Yaw delta for head-left: eulerAngles.x > baselineYaw + yawLeft
    /// Detection is now RELATIVE to the rest yaw captured at neutral confirmation.
    /// Device calibration: rest yaw ≈ -0.143; user reached +0.255 (delta ≈ +0.40) in live testing.
    /// 0.25 rad delta (≈ 14°) is well within the observed turning range.
    var yawLeft:  Float = 0.25      // ≈ 14° relative delta from baseline — spike-v8 calibration
    /// Yaw delta for head-right: eulerAngles.x < baselineYaw - yawRight
    /// Symmetric with yawLeft so left/right turns require equal effort from the rest position.
    var yawRight: Float = 0.25      // ≈ 14° relative delta from baseline — matched to yawLeft
    /// Pitch threshold for chin-up.
    /// Device data shows pitch is NEGATIVE when chin raises (opposite of initial assumption).
    /// Fix: detectChinUp checks pitch < -pitchUp (more negative = chin up).
    /// Set to 0.35 so user needs pitch < -0.35 — below natural rest of -0.18 to -0.33.
    var pitchUp:  Float = 0.35      // chin-up when pitch < -0.35 (sign handled in detector)

    /// Neutral window: |yaw| < neutralYaw AND |pitch| < neutralPitch
    /// Calibrated from device: rest yaw ≈ -0.143, rest pitch ≈ -0.176 → needs ≥ 0.20.
    /// Set to 0.25 (±14°) to give a comfortable margin above observed rest values.
    var neutralYaw:   Float = 0.25  // ≈ ±14° — widened from 0.12 after device calibration
    var neutralPitch: Float = 0.25  // ≈ ±14° — widened from 0.12 after device calibration

    // MARK: — Blendshapes [0.0 … 1.0]

    /// Eye blink accepted as wink above this value.
    /// Spike-v8 calibration: user achieved blinkL=0.57 (smile interference reduces max closure).
    /// Lowered from 0.75 → 0.60 to account for cheek-squint lift from simultaneous smiling.
    var blinkMin:      Float = 0.60
    /// The OTHER eye must stay below this (prevents both-eyes-shut triggering a wink).
    var blinkOtherMax: Float = 0.35

    /// Smile: average of mouthSmileLeft + mouthSmileRight must exceed this.
    var smileAvg:      Float = 0.45
    /// Smile reinforcement: cheekSquint average must also meet this (reduces false smiles).
    var smileSquintMin: Float = 0.15

    /// All blendshapes below this → neutral expression component satisfied.
    var neutralMaxBlend: Float = 0.25

    // MARK: — Timing (milliseconds)

    /// Gesture must be held continuously for this duration before it is accepted.
    var holdDurationMs: Int = 400   // 300–700 ms range per audit; 400 ms is baseline

    /// Per-step timeout: if no gesture detected within this window, fire .timedOut.
    var stepTimeoutMs:  Int = 15_000

    // MARK: — Defaults

    static let production = FacePoseThresholds()
}
