import AVFoundation
import Vision

// MARK: — Data types

// Vision-normalized coordinate (before screen mapping).
// x: 0.0 = left, 1.0 = right  (unmirrored raw camera space)
// y: 0.0 = bottom, 1.0 = top  (Vision convention — opposite of UIKit)
struct NormalizedPoint {
    let x: Float
    let y: Float
    let confidence: Float
}

// MARK: — BodyPoseDetector

final class BodyPoseDetector: NSObject, ObservableObject, AVCaptureVideoDataOutputSampleBufferDelegate {

    // Body
    @Published private(set) var landmarks:  [VNHumanBodyPoseObservation.JointName: NormalizedPoint] = [:]
    @Published private(set) var jointCount: Int = 0

    // Hands: index 0 = left (or first detected), index 1 = right (or second detected)
    // On iOS 15+ sorted by chirality; on iOS 14 detection order.
    @Published private(set) var handLandmarks: [[VNHumanHandPoseObservation.JointName: NormalizedPoint]] = []
    @Published private(set) var handCount: Int = 0

    // Face: nil when no face detected or during skipped frames (last value retained on skip).
    @Published private(set) var faceLandmarks: FaceLandmarksData? = nil
    @Published private(set) var faceCount: Int = 0

    @Published private(set) var fps: Int = 0
    // Increments every processed frame — used by SkeletonBridge as a per-frame trigger.
    @Published private(set) var frameCount: Int = 0

    private let visionQueue     = DispatchQueue(label: "com.lfa.vision", qos: .userInitiated)
    private let sequenceHandler = VNSequenceRequestHandler()
    private var isProcessing    = false
    private var frameTimes:      [CFAbsoluteTime] = []

    // Face runs every 2nd processed frame to keep FPS ≥ 15 on older devices.
    private var faceFrameCounter: Int = 0
    private let faceSkipInterval: Int = 2

    static let confidenceThreshold: Float = 0.3

    // MARK: — Body joint topology

    static let joints: [VNHumanBodyPoseObservation.JointName] = [
        .nose,
        .leftEye,  .rightEye,
        .leftEar,  .rightEar,
        .neck,
        .leftShoulder,  .rightShoulder,
        .leftElbow,     .rightElbow,
        .leftWrist,     .rightWrist,
        .root,
        .leftHip,  .rightHip,
        .leftKnee, .rightKnee,
        .leftAnkle,.rightAnkle,
    ]

    static let connections: [(VNHumanBodyPoseObservation.JointName, VNHumanBodyPoseObservation.JointName)] = [
        (.nose, .leftEye), (.nose, .rightEye),
        (.leftEye, .leftEar), (.rightEye, .rightEar),
        (.nose, .neck),
        (.neck, .leftShoulder),  (.leftShoulder, .leftElbow),  (.leftElbow, .leftWrist),
        (.neck, .rightShoulder), (.rightShoulder, .rightElbow), (.rightElbow, .rightWrist),
        (.leftShoulder, .rightShoulder),
        (.leftShoulder, .leftHip), (.rightShoulder, .rightHip),
        (.leftHip, .rightHip),
        (.leftHip, .leftKnee),   (.leftKnee, .leftAnkle),
        (.rightHip, .rightKnee), (.rightKnee, .rightAnkle),
    ]

    // MARK: — Hand joint topology

    static let handJoints: [VNHumanHandPoseObservation.JointName] = [
        .wrist,
        .thumbCMC, .thumbMP, .thumbIP, .thumbTip,
        .indexMCP, .indexPIP, .indexDIP, .indexTip,
        .middleMCP, .middlePIP, .middleDIP, .middleTip,
        .ringMCP,   .ringPIP,   .ringDIP,   .ringTip,
        .littleMCP, .littlePIP, .littleDIP, .littleTip,
    ]

    static let handConnections: [(VNHumanHandPoseObservation.JointName, VNHumanHandPoseObservation.JointName)] = [
        (.wrist, .thumbCMC), (.thumbCMC, .thumbMP), (.thumbMP, .thumbIP), (.thumbIP, .thumbTip),
        (.wrist, .indexMCP), (.indexMCP, .indexPIP), (.indexPIP, .indexDIP), (.indexDIP, .indexTip),
        (.indexMCP, .middleMCP), (.middleMCP, .middlePIP), (.middlePIP, .middleDIP), (.middleDIP, .middleTip),
        (.middleMCP, .ringMCP), (.ringMCP, .ringPIP), (.ringPIP, .ringDIP), (.ringDIP, .ringTip),
        (.ringMCP, .littleMCP), (.littleMCP, .littlePIP), (.littlePIP, .littleDIP), (.littleDIP, .littleTip),
        (.wrist, .littleMCP),
    ]

    // MARK: — AVCaptureVideoDataOutputSampleBufferDelegate

    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard !isProcessing else { return }
        isProcessing = true

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            isProcessing = false
            return
        }

        visionQueue.async { [weak self] in
            self?.runDetection(on: pixelBuffer)
        }
    }

    // MARK: — Vision pipeline

    private func runDetection(on pixelBuffer: CVPixelBuffer) {
        defer { isProcessing = false }

        let bodyRequest = VNDetectHumanBodyPoseRequest()
        let handRequest = VNDetectHumanHandPoseRequest()
        handRequest.maximumHandCount = 2

        faceFrameCounter = (faceFrameCounter + 1) % faceSkipInterval
        let shouldRunFace = (faceFrameCounter == 0)
        let faceRequest: VNDetectFaceLandmarksRequest? = shouldRunFace
            ? VNDetectFaceLandmarksRequest() : nil

        var requests: [VNRequest] = [bodyRequest, handRequest]
        if let fr = faceRequest { requests.append(fr) }

        do {
            try sequenceHandler.perform(requests, on: pixelBuffer, orientation: .up)
        } catch {
            publishEmpty()
            return
        }

        // ── Body ──────────────────────────────────────────────────────────────
        var bodyDetected: [VNHumanBodyPoseObservation.JointName: NormalizedPoint] = [:]
        if let obs = bodyRequest.results?.first as? VNHumanBodyPoseObservation {
            for joint in Self.joints {
                guard let pt = try? obs.recognizedPoint(joint),
                      pt.confidence >= Self.confidenceThreshold else { continue }
                bodyDetected[joint] = NormalizedPoint(x:          Float(pt.x),
                                                      y:          Float(pt.y),
                                                      confidence: Float(pt.confidence))
            }
        }

        // ── Hands ─────────────────────────────────────────────────────────────
        let rawHandObs = handRequest.results ?? []
        typealias HandEntry = (obs: VNHumanHandPoseObservation,
                               pts: [VNHumanHandPoseObservation.JointName: NormalizedPoint])
        var entries: [HandEntry] = []

        for obs in rawHandObs {
            var pts: [VNHumanHandPoseObservation.JointName: NormalizedPoint] = [:]
            for joint in Self.handJoints {
                guard let pt = try? obs.recognizedPoint(joint),
                      pt.confidence >= Self.confidenceThreshold else { continue }
                pts[joint] = NormalizedPoint(x: Float(pt.x), y: Float(pt.y), confidence: Float(pt.confidence))
            }
            if !pts.isEmpty { entries.append((obs, pts)) }
        }

        var handResults: [[VNHumanHandPoseObservation.JointName: NormalizedPoint]]
        if #available(iOS 15, *) {
            var left:    [VNHumanHandPoseObservation.JointName: NormalizedPoint]? = nil
            var right:   [VNHumanHandPoseObservation.JointName: NormalizedPoint]? = nil
            var unknown: [[VNHumanHandPoseObservation.JointName: NormalizedPoint]] = []
            for e in entries {
                switch e.obs.chirality {
                case .left:  left    = e.pts
                case .right: right   = e.pts
                default:     unknown.append(e.pts)
                }
            }
            handResults = []
            if let l = left  { handResults.append(l) }
            if let r = right { handResults.append(r) }
            handResults.append(contentsOf: unknown)
        } else {
            handResults = entries.map { $0.pts }
        }

        // ── Face ──────────────────────────────────────────────────────────────
        var faceResult: FaceLandmarksData? = nil
        if let fr = faceRequest,
           let obs = fr.results?.first {

            let bb = obs.boundingBox
            let regionDefs: [(String, VNFaceLandmarkRegion2D?)] = [
                ("face_contour",  obs.landmarks?.faceContour),
                ("left_eye",      obs.landmarks?.leftEye),
                ("right_eye",     obs.landmarks?.rightEye),
                ("left_eyebrow",  obs.landmarks?.leftEyebrow),
                ("right_eyebrow", obs.landmarks?.rightEyebrow),
                ("nose",          obs.landmarks?.nose),
                ("nose_crest",    obs.landmarks?.noseCrest),
                ("outer_lips",    obs.landmarks?.outerLips),
                ("left_pupil",    obs.landmarks?.leftPupil),
                ("right_pupil",   obs.landmarks?.rightPupil),
            ]

            var regions: [FaceRegion] = []
            for (name, region) in regionDefs {
                guard let region = region, !region.normalizedPoints.isEmpty else { continue }
                let pts = region.normalizedPoints.map { p in
                    FacePoint(x: Float(bb.minX + p.x * bb.width),
                              y: Float(bb.minY + p.y * bb.height))
                }
                regions.append(FaceRegion(name: name, points: pts))
            }

            faceResult = FaceLandmarksData(
                boundingBox: FaceBoundingBox(x:      Float(bb.minX),
                                             y:      Float(bb.minY),
                                             width:  Float(bb.width),
                                             height: Float(bb.height)),
                regions: regions,
                roll: obs.roll.map { Float(truncating: $0) },
                yaw:  obs.yaw.map  { Float(truncating: $0) }
            )
        }

        // ── FPS ───────────────────────────────────────────────────────────────
        let now = CFAbsoluteTimeGetCurrent()
        frameTimes.append(now)
        frameTimes = frameTimes.filter { now - $0 < 2.0 }
        let fpsValue = frameTimes.count >= 2
            ? Int(Double(frameTimes.count - 1) / (now - (frameTimes.first ?? now)))
            : 0

        DispatchQueue.main.async { [weak self] in
            self?.landmarks     = bodyDetected
            self?.jointCount    = bodyDetected.count
            self?.handLandmarks = handResults
            self?.handCount     = handResults.count
            self?.fps           = fpsValue
            if shouldRunFace {
                self?.faceLandmarks = faceResult
                self?.faceCount     = faceResult != nil ? 1 : 0
            }
            self?.frameCount += 1
        }
    }

    private func publishEmpty() {
        DispatchQueue.main.async { [weak self] in
            self?.landmarks     = [:]
            self?.jointCount    = 0
            self?.handLandmarks = []
            self?.handCount     = 0
            self?.faceLandmarks = nil
            self?.faceCount     = 0
        }
    }
}
