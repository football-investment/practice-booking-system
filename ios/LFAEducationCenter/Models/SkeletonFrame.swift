import Foundation

// JSON contract for skeleton tracking data delivered to JS via WKWebView bridge.
//
// Coordinate space (all x/y fields): screen-normalized
//   x ∈ [0,1]  0 = left screen edge,  1 = right screen edge
//   y ∈ [0,1]  0 = top  screen edge,  1 = bottom screen edge
//
// Applied transforms from Vision raw:
//   x: 1 - visionX  — front camera mirror compensation
//   y: 1 - visionY  — Vision y=0 bottom → screen y=0 top

struct SkeletonFrame: Codable {
    let tsMs:      Int64
    let source:    String
    let fps:       Int
    let body:      [BodyLandmark]
    let leftHand:  [HandLandmark]
    let rightHand: [HandLandmark]
    let face:      FaceLandmarksData?

    enum CodingKeys: String, CodingKey {
        case tsMs = "ts_ms", source, fps, body
        case leftHand = "left_hand", rightHand = "right_hand"
        case face
    }
}

struct BodyLandmark: Codable {
    let name:       String
    let x:          Float
    let y:          Float
    let confidence: Float
}

struct HandLandmark: Codable {
    let name:       String
    let x:          Float
    let y:          Float
    let confidence: Float
}

// MARK: — Face contract

struct FacePoint: Codable {
    let x: Float
    let y: Float
}

struct FaceRegion: Codable {
    let name:   String
    let points: [FacePoint]
}

// Bounding box in screen-normalized space (origin = top-left, after x-flip + y-flip).
struct FaceBoundingBox: Codable {
    let x:      Float
    let y:      Float
    let width:  Float
    let height: Float
}

struct FaceLandmarksData: Codable {
    let boundingBox: FaceBoundingBox
    let regions:     [FaceRegion]
    // Angles in radians from VNFaceObservation (Vision raw / unmirrored image space).
    // roll: positive = clockwise rotation (from camera POV)
    // yaw:  positive = face turned to subject's right (unmirrored frame)
    let roll: Float?
    let yaw:  Float?

    enum CodingKeys: String, CodingKey {
        case boundingBox = "bounding_box"
        case regions, roll, yaw
    }
}
