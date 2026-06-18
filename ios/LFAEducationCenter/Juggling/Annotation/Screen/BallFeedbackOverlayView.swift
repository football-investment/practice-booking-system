import SwiftUI

// MARK: — BallFeedbackOverlayView (AN-3B2B1)
//
// Shown in the video ZStack when feedback mode is active.
//
// Normal state (isCorrecting = false):
//   Draws a white-bordered reference circle at the model's predicted ball
//   position, with a "?" label. Helps the user understand what to validate.
//   No position means no circle is drawn (e.g., lost frames).
//
// Correcting state (isCorrecting = true):
//   Full-area semi-transparent overlay + crosshair + instruction text.
//   The parent view attaches the DragGesture and calls onTap(normalizedPoint:).
//   allowsHitTesting(false) here — tap is handled by the parent ZStack layer.

struct BallFeedbackOverlayView: View {

    let item: BallFeedbackQueueItem?
    let isCorrecting: Bool

    var body: some View {
        GeometryReader { geo in
            ZStack {
                if isCorrecting {
                    correctingLayer(in: geo)
                } else if let item, let px = item.modelPredictedX, let py = item.modelPredictedY {
                    referenceCircle(x: CGFloat(px) * geo.size.width,
                                    y: CGFloat(py) * geo.size.height)
                }
            }
        }
        .allowsHitTesting(false)
    }

    // MARK: — Reference circle (normal state)

    @ViewBuilder
    private func referenceCircle(x: CGFloat, y: CGFloat) -> some View {
        ZStack {
            Circle()
                .strokeBorder(Color.white, lineWidth: 2.5)
                .background(Circle().fill(Color.white.opacity(0.15)))
                .frame(width: 32, height: 32)
                .position(x: x, y: y)

            Text("?")
                .font(.system(size: 10, weight: .bold))
                .foregroundColor(.white)
                .padding(.horizontal, 3)
                .padding(.vertical, 1)
                .background(Color.black.opacity(0.55))
                .cornerRadius(3)
                .position(x: x + 22, y: y - 18)
        }
    }

    // MARK: — Correcting overlay

    @ViewBuilder
    private func correctingLayer(in geo: GeometryProxy) -> some View {
        ZStack {
            Color.black.opacity(0.30)

            // Crosshair at center
            let cx = geo.size.width / 2
            let cy = geo.size.height / 2
            Path { p in
                p.move(to: CGPoint(x: cx - 20, y: cy))
                p.addLine(to: CGPoint(x: cx + 20, y: cy))
                p.move(to: CGPoint(x: cx, y: cy - 20))
                p.addLine(to: CGPoint(x: cx, y: cy + 20))
            }
            .stroke(Color.white.opacity(0.6), lineWidth: 1)

            VStack {
                Text("Koppints a labda valódi pozíciójára")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.black.opacity(0.60))
                    .cornerRadius(8)
                    .padding(.top, 12)
                Spacer()
            }
        }
    }
}

// MARK: — BallFeedbackOverlayColorHelper (testable)

enum BallFeedbackOverlayColorHelper {
    static func confidenceLabel(for item: BallFeedbackQueueItem) -> String {
        guard let c = item.modelConfidence else { return "lost" }
        return "\(Int(c * 100))%"
    }
}
