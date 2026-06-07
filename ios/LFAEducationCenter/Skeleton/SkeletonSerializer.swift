import Vision
import Foundation

// Converts BodyPoseDetector's published state into a SkeletonFrame.
//
// Coordinate transform (Vision raw → screen-normalized):
//   x: 1 - visionX   front camera x-flip (unmirrored Vision → mirrored preview)
//   y: 1 - visionY   Vision y=0 bottom   → screen y=0 top
//
// Output x/y ∈ [0,1], matching on-screen overlay positions.

enum SkeletonSerializer {

    // MARK: — Body joint name map (19 joints)

    static let bodyJointNames: [VNHumanBodyPoseObservation.JointName: String] = [
        .nose:          "nose",
        .leftEye:       "left_eye",
        .rightEye:      "right_eye",
        .leftEar:       "left_ear",
        .rightEar:      "right_ear",
        .neck:          "neck",
        .leftShoulder:  "left_shoulder",
        .rightShoulder: "right_shoulder",
        .leftElbow:     "left_elbow",
        .rightElbow:    "right_elbow",
        .leftWrist:     "left_wrist",
        .rightWrist:    "right_wrist",
        .root:          "root",
        .leftHip:       "left_hip",
        .rightHip:      "right_hip",
        .leftKnee:      "left_knee",
        .rightKnee:     "right_knee",
        .leftAnkle:     "left_ankle",
        .rightAnkle:    "right_ankle",
    ]

    // MARK: — Hand joint name map (21 joints)

    static let handJointNames: [VNHumanHandPoseObservation.JointName: String] = [
        .wrist:     "wrist",
        .thumbCMC:  "thumb_cmc",
        .thumbMP:   "thumb_mp",
        .thumbIP:   "thumb_ip",
        .thumbTip:  "thumb_tip",
        .indexMCP:  "index_mcp",
        .indexPIP:  "index_pip",
        .indexDIP:  "index_dip",
        .indexTip:  "index_tip",
        .middleMCP: "middle_mcp",
        .middlePIP: "middle_pip",
        .middleDIP: "middle_dip",
        .middleTip: "middle_tip",
        .ringMCP:   "ring_mcp",
        .ringPIP:   "ring_pip",
        .ringDIP:   "ring_dip",
        .ringTip:   "ring_tip",
        .littleMCP: "little_mcp",
        .littlePIP: "little_pip",
        .littleDIP: "little_dip",
        .littleTip: "little_tip",
    ]

    // MARK: — Coordinate transforms

    private static func norm(_ p: NormalizedPoint) -> (x: Float, y: Float) {
        (x: 1.0 - p.x, y: 1.0 - p.y)
    }

    private static func norm(_ p: FacePoint) -> FacePoint {
        FacePoint(x: 1.0 - p.x, y: 1.0 - p.y)
    }

    // MARK: — Serialization

    static func serialize(detector: BodyPoseDetector) -> SkeletonFrame {
        let tsMs = Int64(Date().timeIntervalSince1970 * 1000)

        let body: [BodyLandmark] = BodyPoseDetector.joints.compactMap { joint in
            guard let point = detector.landmarks[joint],
                  let name  = bodyJointNames[joint] else { return nil }
            let n = norm(point)
            return BodyLandmark(name: name, x: n.x, y: n.y, confidence: point.confidence)
        }

        func serializeHand(
            _ landmarks: [VNHumanHandPoseObservation.JointName: NormalizedPoint]
        ) -> [HandLandmark] {
            BodyPoseDetector.handJoints.compactMap { joint in
                guard let point = landmarks[joint],
                      let name  = handJointNames[joint] else { return nil }
                let n = norm(point)
                return HandLandmark(name: name, x: n.x, y: n.y, confidence: point.confidence)
            }
        }

        let leftHand  = detector.handLandmarks.count > 0 ? serializeHand(detector.handLandmarks[0]) : []
        let rightHand = detector.handLandmarks.count > 1 ? serializeHand(detector.handLandmarks[1]) : []

        let face: FaceLandmarksData? = detector.faceLandmarks.map { faceData in
            let bb = faceData.boundingBox
            let screenBB = FaceBoundingBox(
                x:      1.0 - bb.x - bb.width,
                y:      1.0 - bb.y - bb.height,
                width:  bb.width,
                height: bb.height
            )
            let regions = faceData.regions.map { region in
                FaceRegion(name: region.name, points: region.points.map { norm($0) })
            }
            return FaceLandmarksData(boundingBox: screenBB, regions: regions,
                                     roll: faceData.roll, yaw: faceData.yaw)
        }

        return SkeletonFrame(tsMs: tsMs, source: "ios_vision", fps: detector.fps,
                             body: body, leftHand: leftHand, rightHand: rightHand, face: face)
    }
}
