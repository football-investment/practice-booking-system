import Foundation

// PR-iOS-2: SpikeLivenessView is now the production liveness mechanism.
// kBiometricAutoCaptureSpikeEnabled is no longer used as a routing flag —
// BiometricDisclosureView routes unconditionally to SpikeLivenessView after
// disclosure + consent acceptance.
//
// This constant is retained for backward compatibility with any debug tooling
// that checks it, but it has no effect on the production flow in PR-iOS-2+.
#if DEBUG
let kBiometricAutoCaptureSpikeEnabled: Bool = false   // retired — see BiometricDisclosureView
#else
let kBiometricAutoCaptureSpikeEnabled: Bool = false   // compile-time constant
#endif

// Build label — identifies this binary in the device debug overlay and console.
// Format: "pr2-v<N>/<scope>"
let kSpikeLabel = "pr2-v1/liveness-photo-upload"

// DEBUG-only UserDefaults key written by SpikeLivenessView on backend-confirmed completion.
// Read by ProfileView.biometricDebugOverlay to show local completion timestamp.
// Never compiled into Release builds; never touches backend or profile state directly.
#if DEBUG
let kDebugSpikeCompletedAtKey = "debug_spike_completed_at"
#endif
