import ARKit
import SceneKit
import SwiftUI
import UIKit

// UIViewRepresentable wrapping ARSCNView for TrueDepth face tracking.
//
// Device support:
//   Supported:    iPhone X+ (A11 Bionic + TrueDepth camera), iOS 12+
//   Not supported: iPhone SE (1st/2nd gen), iPad without TrueDepth
//
// Privacy rules:
//   - The ARSession runs entirely on-device; no data leaves the device.
//   - No frame images, landmarks, or blendshape values are stored anywhere.
//   - ViewModel.update(with:) processes each anchor ephemerally in memory only.
//   - BiometricPhotoCapture.captureJPEG is the single path by which image data
//     is produced, and only on explicit request after 7/7 gesture completion.
struct ARFaceTrackingView: UIViewRepresentable {

    @ObservedObject var viewModel: SpikeLivenessViewModel

    func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView(frame: .zero)
        view.delegate              = context.coordinator
        view.session.delegate      = context.coordinator
        view.showsStatistics       = false
        view.automaticallyUpdatesLighting = false
        view.rendersCameraGrain    = false
        view.rendersMotionBlur     = false

        if ARFaceTrackingConfiguration.isSupported {
            let config = ARFaceTrackingConfiguration()
            config.isLightEstimationEnabled = false
            config.maximumNumberOfTrackedFaces = 1
            view.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        }

        context.coordinator.sceneView = view
        wireSnapshotProvider(coordinator: context.coordinator)
        return view
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {
        context.coordinator.sceneView = uiView
        wireSnapshotProvider(coordinator: context.coordinator)
    }

    static func dismantleUIView(_ uiView: ARSCNView, coordinator: Coordinator) {
        uiView.session.pause()
    }

    func makeCoordinator() -> Coordinator { Coordinator(viewModel: viewModel) }

    // Wire the snapshot provider once per ViewModel instance.
    // Called from makeUIView / updateUIView (both run on the main thread).
    // Uses DispatchQueue.main.async to satisfy the Swift compiler's actor
    // isolation check: snapshotProvider is @MainActor, Coordinator is not.
    private func wireSnapshotProvider(coordinator: Coordinator) {
        DispatchQueue.main.async { [weak coordinator] in
            guard
                let coord = coordinator,
                self.viewModel.snapshotProvider == nil
            else { return }
            self.viewModel.snapshotProvider = { [weak coord] in
                guard let view = coord?.sceneView else { return nil }
                return BiometricPhotoCapture.captureJPEG(from: view)
            }
        }
    }

    // MARK: — Coordinator

    final class Coordinator: NSObject, ARSCNViewDelegate, ARSessionDelegate {

        private let viewModel: SpikeLivenessViewModel

        // Weak ref prevents Coordinator from extending the view's lifetime.
        weak var sceneView: ARSCNView?

        init(viewModel: SpikeLivenessViewModel) {
            self.viewModel = viewModel
        }

        func renderer(_ renderer: SCNSceneRenderer, didAdd node: SCNNode, for anchor: ARAnchor) {
            guard anchor is ARFaceAnchor else { return }
        }

        func renderer(_ renderer: SCNSceneRenderer,
                      didUpdate node: SCNNode,
                      for anchor: ARAnchor) {
            guard let face = anchor as? ARFaceAnchor else { return }
            Task { @MainActor [weak viewModel] in
                viewModel?.update(with: face)
            }
        }

        func renderer(_ renderer: SCNSceneRenderer,
                      didRemove node: SCNNode,
                      for anchor: ARAnchor) {
            guard anchor is ARFaceAnchor else { return }
            Task { @MainActor [weak viewModel] in
                viewModel?.faceTrackingLost()
            }
        }

        func sessionWasInterrupted(_ session: ARSession) {
            Task { @MainActor [weak viewModel] in
                viewModel?.faceTrackingLost()
            }
        }
    }
}

// MARK: — Device support check

extension ARFaceTrackingView {
    static var isDeviceSupported: Bool {
        ARFaceTrackingConfiguration.isSupported
    }
}

// MARK: — BiometricPhotoCapture
//
// Inlined here so no additional Xcode project file entry is required.
// Captures a JPEG snapshot from an ARSCNView at liveness-challenge completion.
//
// Privacy rules:
//   - Snapshot taken only on explicit caller request (after neutral recapture hold).
//   - Image data lives in memory only; written to disk only during upload.
//   - No landmark, blendshape, yaw, pitch, or face_match_score is extracted here.
//   - No image is stored persistently on the iOS device.
enum BiometricPhotoCapture {

    static let maxBytes:       Int    = 5 * 1024 * 1024  // 5 MB
    static let primaryQuality: CGFloat = 0.82
    static let fallbackQuality: CGFloat = 0.55

    // Capture a JPEG snapshot from the live ARSCNView.
    // Returns nil if the image has zero size or if JPEG compression exceeds maxBytes.
    static func captureJPEG(from sceneView: ARSCNView) -> Data? {
        let image = sceneView.snapshot()
        guard image.size.width > 0, image.size.height > 0 else { return nil }
        return compress(image: image)
    }

    // Compress UIImage to JPEG with quality fallback.
    // Internal (not private) so tests can access it via @testable import.
    static func compress(image: UIImage) -> Data? {
        if let data = image.jpegData(compressionQuality: primaryQuality),
           data.count <= maxBytes {
            return data
        }
        if let data = image.jpegData(compressionQuality: fallbackQuality),
           data.count <= maxBytes {
            return data
        }
        return nil
    }
}
