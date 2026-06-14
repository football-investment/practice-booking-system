import XCTest
import Combine
@testable import LFAEducationCenter

// MARK: — BV-01..18: JugglingVideoUploadViewModel
//
// All tests run on @MainActor (same as the ViewModel).
// No network, no AuthManager — mock injects via JugglingAnnotationAPIClientProtocol.
// Temp files are real files written to /tmp so we can verify cleanup.
//
// Naming: BV = B-phase Video upload ViewModel

@MainActor
final class JugglingVideoUploadViewModelTests: XCTestCase {

    // MARK: — Helpers

    private func makeTempVideoFile(size: Int = 1024) throws -> URL {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("mp4")
        try Data(repeating: 0xFF, count: size).write(to: url)
        return url
    }

    private func makeSuccessMock(videoId: String = "v1") -> MockUploadClient {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: videoId, status: "pending_upload", uploadUrl: "/upload")
        )
        mock.uploadVideoFileResult = .success(
            JugglingUploadFileResponse(videoId: videoId, status: "uploaded", fileSizeBytes: 1024, checksumSha256: "abc123")
        )
        mock.completeUploadResult = .success(
            JugglingCompleteResponse(videoId: videoId, status: "transcoding", message: "queued")
        )
        return mock
    }

    private func makeVM(
        mock: MockUploadClient,
        maxSize: Int64 = 100 * 1024 * 1024
    ) -> JugglingVideoUploadViewModel {
        JugglingVideoUploadViewModel(apiClient: mock, maxFileSizeBytes: maxSize)
    }

    // Runs the full picker → upload flow for a ViewModel and awaits completion.
    private func runUpload(
        vm: JugglingVideoUploadViewModel,
        tempURL: URL,
        mimeType: String = "video/mp4"
    ) async {
        vm.startPicker()
        vm.pickerDidSelect(tempURL: tempURL, mimeType: mimeType)
        let task = vm.uploadTask
        await task?.value
    }

    // MARK: — BV-01: full success state transitions

    func test_BV01_fullSuccessStateTransitions() async throws {
        let mock = makeSuccessMock()
        let vm = makeVM(mock: mock)
        var states: [JugglingVideoUploadViewModel.UploadState] = []
        let cancellable = vm.$state.sink { states.append($0) }

        let url = try makeTempVideoFile()
        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(states, [
            .idle,
            .selecting,
            .preparing,
            .uploading(progress: 0),
            .completing,
            .success
        ])
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
        cancellable.cancel()
    }

    // MARK: — BV-02: picker cancel → idle

    func test_BV02_pickerCancelReturnsIdle() {
        let vm = makeVM(mock: MockUploadClient())
        vm.startPicker()
        XCTAssertEqual(vm.state, .selecting)
        vm.pickerCancelled()
        XCTAssertEqual(vm.state, .idle)
        XCTAssertNil(vm.uploadTask)
    }

    // MARK: — BV-03: file too large → local block, no network call

    func test_BV03_fileTooLargeBlocksNetworkCall() async throws {
        let mock = MockUploadClient()
        let vm = makeVM(mock: mock, maxSize: 512)       // 512-byte limit for test
        let url = try makeTempVideoFile(size: 1024)     // 1024 > 512 → rejected locally

        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(vm.state, .failure(.fileTooLarge))
        XCTAssertFalse(mock.uploadInitCalled, "Network must not start for oversized file")
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-04: unsupported MIME → local block, no network call

    func test_BV04_unsupportedMIMEBlocksNetworkCall() async throws {
        let mock = MockUploadClient()
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url, mimeType: "video/avi")

        XCTAssertEqual(vm.state, .failure(.unsupportedFormat))
        XCTAssertFalse(mock.uploadInitCalled)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-05: no consent (403 from uploadInit)

    func test_BV05_noConsentFromInit() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(JugglingUploadError.noConsent)
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(vm.state, .failure(.noConsent))
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-06: invalid state (409 from uploadVideoFile)

    func test_BV06_invalidStateFromFileUpload() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: "v1", status: "pending_upload", uploadUrl: "/upload")
        )
        mock.uploadVideoFileResult = .failure(JugglingUploadError.invalidState("already uploaded"))
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(vm.state, .failure(.invalidState("already uploaded")))
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-07: unauthorized (401 from uploadInit)

    func test_BV07_unauthorizedFromInit() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(JugglingUploadError.unauthorized)
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(vm.state, .failure(.unauthorized))
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-08: network error

    func test_BV08_networkErrorFromInit() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(
            JugglingUploadError.networkError(URLError(.notConnectedToInternet))
        )
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        guard case .failure(.networkError) = vm.state else {
            return XCTFail("Expected .failure(.networkError), got \(vm.state)")
        }
    }

    // MARK: — BV-09: timeout

    func test_BV09_timeoutFromFileUpload() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: "v1", status: "pending_upload", uploadUrl: "/upload")
        )
        mock.uploadVideoFileResult = .failure(
            JugglingUploadError.networkError(URLError(.timedOut))
        )
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        guard case .failure(.networkError) = vm.state else {
            return XCTFail("Expected .failure(.networkError), got \(vm.state)")
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-10: retry after failure → success

    func test_BV10_retryAfterFailureSucceeds() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(
            JugglingUploadError.networkError(URLError(.notConnectedToInternet))
        )
        let vm = makeVM(mock: mock)

        let url1 = try makeTempVideoFile()
        await runUpload(vm: vm, tempURL: url1)
        guard case .failure(.networkError) = vm.state else {
            return XCTFail("Expected failure on first attempt")
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: url1.path))

        // Fix mock and retry
        mock.uploadInitResult = makeSuccessMock().uploadInitResult
        mock.uploadVideoFileResult = makeSuccessMock().uploadVideoFileResult
        mock.completeUploadResult = makeSuccessMock().completeUploadResult
        vm.retry()
        XCTAssertEqual(vm.state, .idle)

        let url2 = try makeTempVideoFile()
        await runUpload(vm: vm, tempURL: url2)
        XCTAssertEqual(vm.state, .success)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url2.path))
    }

    // MARK: — BV-11: duplicate start blocked

    func test_BV11_startPickerBlockedUnlessIdle() {
        let vm = makeVM(mock: MockUploadClient())
        vm.startPicker()
        XCTAssertEqual(vm.state, .selecting)
        vm.startPicker()  // second call blocked
        XCTAssertEqual(vm.state, .selecting)
        XCTAssertNil(vm.uploadTask, "No task must be created by a blocked startPicker")
    }

    // MARK: — BV-12: completeUpload called only after successful file upload

    func test_BV12_completeNotCalledIfFileUploadFails() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: "v1", status: "pending_upload", uploadUrl: "/upload")
        )
        mock.uploadVideoFileResult = .failure(JugglingUploadError.fileTooLarge)
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertFalse(mock.completeUploadCalled, "completeUpload must not be called if file upload failed")
        guard case .failure(.fileTooLarge) = vm.state else {
            return XCTFail("Expected .failure(.fileTooLarge)")
        }
    }

    // MARK: — BV-13: completion callback only on full success

    func test_BV13_completionCallbackFiredOnlyOnSuccess() async throws {
        // Failure case — callback must NOT fire
        let failMock = MockUploadClient()
        failMock.uploadInitResult = .failure(JugglingUploadError.noConsent)
        let failVM = makeVM(mock: failMock)
        var failCallbackFired = false
        failVM.onSuccess = { failCallbackFired = true }

        let url1 = try makeTempVideoFile()
        await runUpload(vm: failVM, tempURL: url1)
        XCTAssertFalse(failCallbackFired, "Callback must not fire on failure")

        // Success case — callback MUST fire
        let successVM = makeVM(mock: makeSuccessMock())
        var successCallbackFired = false
        successVM.onSuccess = { successCallbackFired = true }

        let url2 = try makeTempVideoFile()
        await runUpload(vm: successVM, tempURL: url2)
        XCTAssertTrue(successCallbackFired, "Callback must fire on full success")
    }

    // MARK: — BV-14: temp file deleted on success

    func test_BV14_tempFileDeletedOnSuccess() async throws {
        let vm = makeVM(mock: makeSuccessMock())
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertEqual(vm.state, .success)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-15: temp file deleted on failure

    func test_BV15_tempFileDeletedOnFailure() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(JugglingUploadError.noConsent)
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-16: temp file deleted on cancel

    func test_BV16_tempFileDeletedOnCancel() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: "v1", status: "pending_upload", uploadUrl: "/upload")
        )
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        vm.startPicker()
        vm.pickerDidSelect(tempURL: url, mimeType: "video/mp4")
        let task = vm.uploadTask   // capture before cancel
        vm.cancel()
        await task?.value          // let task observe cancellation and return

        XCTAssertEqual(vm.state, .idle)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path))
    }

    // MARK: — BV-17: retry uses fresh temp file, not stale file from first attempt

    func test_BV17_retryUsesFreshTempFileNotStale() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .failure(JugglingUploadError.noConsent)
        let vm = makeVM(mock: mock)

        let url1 = try makeTempVideoFile()
        await runUpload(vm: vm, tempURL: url1)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url1.path), "url1 must be gone after first failure")

        // Retry with a new file
        mock.uploadInitResult = makeSuccessMock().uploadInitResult
        mock.uploadVideoFileResult = makeSuccessMock().uploadVideoFileResult
        mock.completeUploadResult = makeSuccessMock().completeUploadResult
        vm.retry()

        let url2 = try makeTempVideoFile()
        await runUpload(vm: vm, tempURL: url2)
        XCTAssertEqual(vm.state, .success)
        XCTAssertFalse(FileManager.default.fileExists(atPath: url2.path), "url2 must be gone after success")
        // url1 was already cleaned — verify it's still gone
        XCTAssertFalse(FileManager.default.fileExists(atPath: url1.path))
    }

    // MARK: — BV-18: state not stuck in uploading/completing on error

    func test_BV18_stateNotStuckAfterCompleteUploadError() async throws {
        let mock = MockUploadClient()
        mock.uploadInitResult = .success(
            JugglingUploadInitResponse(videoId: "v1", status: "pending_upload", uploadUrl: "/upload")
        )
        mock.uploadVideoFileResult = .success(
            JugglingUploadFileResponse(videoId: "v1", status: "uploaded", fileSizeBytes: 1024, checksumSha256: "abc")
        )
        mock.completeUploadResult = .failure(JugglingUploadError.invalidState("not in uploaded state"))
        let vm = makeVM(mock: mock)
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)

        guard case .failure(let err) = vm.state else {
            return XCTFail("Expected .failure, got \(vm.state)")
        }
        XCTAssertEqual(err, .invalidState("not in uploaded state"),
                       "State must not remain .completing after completeUpload error")
    }

    // MARK: — BV-19: a late pickerDidSelect (state already moved on, e.g. via
    // pickerCancelled) is a no-op AND deletes the temp file it was handed —
    // no orphan files survive a late/spurious selection callback.

    func test_BV19_latePickerDidSelectIsNoOpAndDeletesTempFile() throws {
        let vm = makeVM(mock: MockUploadClient())
        let url = try makeTempVideoFile()

        vm.startPicker()
        XCTAssertEqual(vm.state, .selecting)

        vm.pickerCancelled()
        XCTAssertEqual(vm.state, .idle)

        // A late selection callback now arrives, after state moved on.
        vm.pickerDidSelect(tempURL: url, mimeType: "video/mp4")

        XCTAssertEqual(vm.state, .idle, "pickerDidSelect must be a no-op once state left .selecting")
        XCTAssertNil(vm.uploadTask, "No upload task must be created")
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.path),
                        "A late pickerDidSelect must delete the temp file it was handed — no orphans")
    }

    // MARK: — BV-20: pickerCancelled() is a no-op once an upload has
    // progressed past .selecting — defense-in-depth against any late/spurious
    // cancel signal reaching the ViewModel after pickerDidSelect already ran.

    func test_BV20_pickerCancelledIgnoredOnceUploadStarted() async throws {
        let vm = makeVM(mock: makeSuccessMock())
        let url = try makeTempVideoFile()

        await runUpload(vm: vm, tempURL: url)
        XCTAssertEqual(vm.state, .success)

        vm.pickerCancelled()

        XCTAssertEqual(vm.state, .success, "A late pickerCancelled() must not disturb a completed upload")
    }

    // MARK: — BV-21: normal selection transitions to .preparing, not .idle
    // (the headline regression for the fixed bug — startPicker() →
    // pickerDidSelect() must NOT pass through an intermediate
    // pickerCancelled()-driven .idle).

    func test_BV21_normalSelectionGoesToPreparingNotIdle() throws {
        let vm = makeVM(mock: MockUploadClient())
        let url = try makeTempVideoFile()
        var states: [JugglingVideoUploadViewModel.UploadState] = []
        let cancellable = vm.$state.sink { states.append($0) }

        vm.startPicker()
        vm.pickerDidSelect(tempURL: url, mimeType: "video/mp4")

        XCTAssertEqual(vm.state, .preparing)
        XCTAssertEqual(states, [.idle, .selecting, .preparing],
                       "No intermediate .idle must appear between .selecting and .preparing")

        vm.cancel()
        cancellable.cancel()
    }

    // MARK: — BV-22: picker cancel (no selection) still resets to .idle —
    // the legitimate cancel path must keep working after the fix.

    func test_BV22_pickerCancelStillResetsToIdle() {
        let vm = makeVM(mock: MockUploadClient())
        vm.startPicker()
        XCTAssertEqual(vm.state, .selecting)

        vm.pickerCancelled()

        XCTAssertEqual(vm.state, .idle)
        XCTAssertNil(vm.uploadTask)
    }
}

// MARK: — MockUploadClient

@MainActor
private final class MockUploadClient: JugglingAnnotationAPIClientProtocol {

    var uploadInitResult: Result<JugglingUploadInitResponse, Error> = .failure(JugglingUploadError.unauthorized)
    var uploadVideoFileResult: Result<JugglingUploadFileResponse, Error> = .failure(JugglingUploadError.unauthorized)
    var completeUploadResult: Result<JugglingCompleteResponse, Error> = .failure(JugglingUploadError.unauthorized)

    private(set) var uploadInitCalled = false
    private(set) var uploadVideoFileCalled = false
    private(set) var completeUploadCalled = false

    func uploadInit(sourceType: String, uploadSource: String) async throws -> JugglingUploadInitResponse {
        uploadInitCalled = true
        return try uploadInitResult.get()
    }

    func uploadVideoFile(videoId: String, fileURL: URL, mimeType: String) async throws -> JugglingUploadFileResponse {
        uploadVideoFileCalled = true
        return try uploadVideoFileResult.get()
    }

    func completeUpload(videoId: String) async throws -> JugglingCompleteResponse {
        completeUploadCalled = true
        return try completeUploadResult.get()
    }

    // — Unused protocol requirements (stub only)

    func listContacts(videoId: String) async throws -> ContactEventListOut {
        ContactEventListOut(videoId: videoId, annotationStatus: nil, events: [])
    }

    func createContact(videoId: String, request: ContactEventCreateRequest) async throws -> CreateContactResult {
        throw AnnotationAPIError.unauthorized
    }

    func patchContact(videoId: String, eventId: UUID, request: ContactEventPatchRequest) async throws -> ContactEventOut {
        throw AnnotationAPIError.unauthorized
    }

    func deleteContact(videoId: String, eventId: UUID) async throws -> DeleteContactResult {
        throw AnnotationAPIError.unauthorized
    }

    func finishAnnotation(videoId: String, confirmZero: Bool) async throws -> FinishAnnotationOut {
        throw AnnotationAPIError.unauthorized
    }

    func deleteVideo(videoId: String) async throws {
        throw VideoDeleteError.unauthorized
    }
}
