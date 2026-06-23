import SwiftUI

#if DEBUG
struct CaptureOverlayView: View {
    let orchestrationState: OrchestrationState

    @State private var tick: Int = 0
    @State private var captureElapsed: Int = 0

    private let timer = Timer.publish(every: 1, on: .main, in: .common).autoconnect()

    var body: some View {
        ZStack(alignment: .topLeading) {
            overlayContent
        }
        .onReceive(timer) { _ in
            tick += 1
            if case .capturing = orchestrationState {
                captureElapsed += 1
            }
        }
        .onChange(of: orchestrationState) { newState in
            if case .capturing = newState { } else { captureElapsed = 0 }
        }
    }

    @ViewBuilder
    private var overlayContent: some View {
        switch orchestrationState {
        case .capturing:
            recBadge
        case .starting:
            statePill("Indítás…", color: .orange)
        case .stopping:
            statePill("Leállítás…", color: .secondary)
        case .scheduled(let fireAt):
            countdownPill(fireAt: fireAt)
        default:
            EmptyView()
        }
    }

    private var recBadge: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Color.red)
                .frame(width: 10, height: 10)
            Text("REC")
                .font(.system(size: 13, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
            Text(formatElapsed(captureElapsed))
                .font(.system(size: 13, weight: .semibold, design: .monospaced))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(Color.black.opacity(0.65))
        .clipShape(Capsule())
        .padding(12)
    }

    private func statePill(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .foregroundColor(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(color.opacity(0.8))
            .clipShape(Capsule())
            .padding(12)
    }

    private func countdownPill(fireAt: Date) -> some View {
        let remaining = max(0, fireAt.timeIntervalSinceNow)
        return statePill("Indítás: \(Int(remaining))s", color: .orange)
    }

    private func formatElapsed(_ seconds: Int) -> String {
        String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }
}
#endif
