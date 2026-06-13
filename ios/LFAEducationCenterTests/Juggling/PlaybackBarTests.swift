import XCTest
import AVFoundation
@testable import LFAEducationCenter

// MARK: — AN-3B1: PlaybackControlBar unit tests (AN3B-B01..B08)
//
// PlaybackControlBar is a SwiftUI view — its rendering is not unit-testable without
// ViewInspector.  What IS testable:
//   - PlaybackControlBar.formatTimestamp(ms:)  (static pure function)
//   - Interaction: tapping actions delegate to PlaybackController (via MockPlayer)
//   - The bar can be instantiated without crashing

@MainActor
final class PlaybackBarTests: XCTestCase {

    // MARK: — AN3B-B01: timestamp format — zero

    func test_AN3B_B01_timestampFormat_zero() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 0), "0:00.000")
    }

    // MARK: — AN3B-B02: timestamp format — 1 second

    func test_AN3B_B02_timestampFormat_oneSecond() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 1000), "0:01.000")
    }

    // MARK: — AN3B-B03: timestamp format — 1 minute

    func test_AN3B_B03_timestampFormat_oneMinute() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 60_000), "1:00.000")
    }

    // MARK: — AN3B-B04: timestamp format — complex (1:15.500)

    func test_AN3B_B04_timestampFormat_complex() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 75_500), "1:15.500")
    }

    // MARK: — AN3B-B05: timestamp format — sub-second

    func test_AN3B_B05_timestampFormat_subSecond() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 42), "0:00.042")
    }

    // MARK: — AN3B-B06: timestamp format — two minutes

    func test_AN3B_B06_timestampFormat_twoMinutes() {
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 120_001), "2:00.001")
    }

    // MARK: — AN3B-B07: control bar initialises without crashing

    func test_AN3B_B07_controlBarInitDoesNotCrash() {
        let player     = MockPlayer()
        let controller = PlaybackController(player: player)
        // SwiftUI views are value types — instantiation must not crash.
        let bar = PlaybackControlBar(controller: controller)
        _ = bar   // suppress "never used" warning
    }

    // MARK: — AN3B-B08: formatTimestamp handles large values

    func test_AN3B_B08_timestampFormat_largeValue() {
        // 10 minutes, 5 seconds, 123 ms = 605_123 ms
        XCTAssertEqual(PlaybackControlBar.formatTimestamp(ms: 605_123), "10:05.123")
    }
}
