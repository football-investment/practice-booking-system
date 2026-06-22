import Foundation

// MARK: — Clock offset

enum ClockSyncQuality: String {
    case synchronized
    case degradedMissingServerDate
    case degradedHighRTT
}

struct ClockOffset {
    let offsetSeconds: Double
    let uncertaintySeconds: Double
    let quality: ClockSyncQuality

    func localFireDate(for serverTimestamp: Date) -> Date {
        serverTimestamp.addingTimeInterval(-offsetSeconds)
    }

    static let zero = ClockOffset(offsetSeconds: 0, uncertaintySeconds: 0, quality: .degradedMissingServerDate)
}

// MARK: — Timer protocol

protocol Cancellable { func cancel() }
extension DispatchWorkItem: Cancellable {}

protocol OrchestrationTimerProvider {
    func scheduleTimer(fireAt: Date, handler: @escaping () -> Void) -> Cancellable
}

final class SystemOrchestrationTimer: OrchestrationTimerProvider {
    private let timerQueue = DispatchQueue(label: "com.lfa.multicamera.timer", qos: .userInteractive)

    func scheduleTimer(fireAt: Date, handler: @escaping () -> Void) -> Cancellable {
        let delay = max(0, fireAt.timeIntervalSinceNow)
        let item = DispatchWorkItem { handler() }
        timerQueue.asyncAfter(deadline: .now() + delay, execute: item)
        return item
    }
}

// MARK: — Clock manager

@MainActor
final class ScheduledCaptureClockManager: ObservableObject {
    @Published private(set) var currentOffset: ClockOffset = .zero

    func updateFromPolling(requestDuration: TimeInterval, serverDateHeader: Date?) {
        if let serverDate = serverDateHeader {
            let rtt = requestDuration
            let estimatedServerNow = serverDate.timeIntervalSince1970 + rtt / 2
            let localNow = Date().timeIntervalSince1970
            let quality: ClockSyncQuality = rtt > 2.0 ? .degradedHighRTT : .synchronized
            currentOffset = ClockOffset(
                offsetSeconds: estimatedServerNow - localNow,
                uncertaintySeconds: rtt / 2,
                quality: quality
            )
        } else {
            currentOffset = .zero
        }
    }

    func localFireDate(for serverTimestamp: Date) -> Date {
        currentOffset.localFireDate(for: serverTimestamp)
    }
}
