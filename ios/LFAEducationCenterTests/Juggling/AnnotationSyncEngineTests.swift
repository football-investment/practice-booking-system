import XCTest
@testable import LFAEducationCenter

// MARK: — MockAnnotationAPIClient
//
// Configurable stand-in for JugglingAnnotationAPIClient. Each endpoint has a
// Result<_, Error> slot set by the test before calling the engine.

@MainActor
final class MockAnnotationAPIClient: JugglingAnnotationAPIClientProtocol {

    var listContactsResult:    Result<ContactEventListOut, Error> = .success(ContactEventListOut(videoId: "vid-1", annotationStatus: nil, events: []))
    var createContactResult:   Result<CreateContactResult, Error> = .failure(AnnotationAPIError.unauthorized)
    var patchContactResult:    Result<ContactEventOut, Error> = .failure(AnnotationAPIError.unauthorized)
    var deleteContactResult:   Result<DeleteContactResult, Error> = .failure(AnnotationAPIError.unauthorized)
    var finishAnnotationResult: Result<FinishAnnotationOut, Error> = .failure(AnnotationAPIError.unauthorized)

    func listContacts(videoId: String) async throws -> ContactEventListOut {
        try listContactsResult.get()
    }

    func createContact(videoId: String, request: ContactEventCreateRequest) async throws -> CreateContactResult {
        try createContactResult.get()
    }

    func patchContact(videoId: String, eventId: UUID, request: ContactEventPatchRequest) async throws -> ContactEventOut {
        try patchContactResult.get()
    }

    func deleteContact(videoId: String, eventId: UUID) async throws -> DeleteContactResult {
        try deleteContactResult.get()
    }

    func finishAnnotation(videoId: String, confirmZero: Bool) async throws -> FinishAnnotationOut {
        try finishAnnotationResult.get()
    }
}

// MARK: — AN2-T17..T25: AnnotationSyncEngine state transitions

@MainActor
final class AnnotationSyncEngineTests: XCTestCase {

    // AN2-T17: successful create (201) → synced, server identity captured.
    func test_AN2_T17_pushCreateSuccessBecomesSynced() async {
        let mock = MockAnnotationAPIClient()
        let draft = ContactEventDraft.new(timestampMs: 100, contactType: "right_instep", side: "right", annotationConfidence: "certain")
        let serverEvent = makeServerEvent(deviceEventId: draft.deviceEventId, contactType: "right_instep", side: "right", version: 1)
        mock.createContactResult = .success(CreateContactResult(event: serverEvent, isNew: true))

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushCreate(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .synced)
        XCTAssertEqual(result.serverEventId, serverEvent.eventId)
        XCTAssertEqual(result.version, 1)
        XCTAssertEqual(result.retryCount, 0)
    }

    // AN2-T18: network error → retryPending, retryCount incremented.
    func test_AN2_T18_pushCreateNetworkErrorBecomesRetryPending() async {
        let mock = MockAnnotationAPIClient()
        mock.createContactResult = .failure(AnnotationAPIError.retryable(code: nil))
        let draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushCreate(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .retryPending)
        XCTAssertEqual(result.retryCount, 1)
    }

    // AN2-T19: permanent error (403 consent blocked) → failedPermanent, no retry.
    func test_AN2_T19_pushCreatePermanentErrorBecomesFailedPermanent() async {
        let mock = MockAnnotationAPIClient()
        mock.createContactResult = .failure(AnnotationAPIError.permanent(code: 403, detail: "consent_blocked"))
        let draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushCreate(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .failedPermanent)
        XCTAssertEqual(result.retryCount, 0)
    }

    // AN2-T20: retryable error once retryCount has hit maxRetries → failedPermanent.
    func test_AN2_T20_pushCreateRetryableAtMaxRetriesBecomesFailedPermanent() async {
        let mock = MockAnnotationAPIClient()
        mock.createContactResult = .failure(AnnotationAPIError.retryable(code: 503))
        var draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        draft.retryCount = AnnotationSyncEngine.maxRetries

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushCreate(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .failedPermanent)
        XCTAssertEqual(result.retryCount, AnnotationSyncEngine.maxRetries)
    }

    // AN2-T21: DELETE 204 → deleted.
    func test_AN2_T21_pushDeleteConfirmedBecomesDeleted() async {
        let mock = MockAnnotationAPIClient()
        mock.deleteContactResult = .success(.deleted)
        var draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        draft.serverEventId = UUID()
        draft.syncStatus = .synced

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushDelete(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .deleted)
    }

    // AN2-T22: DELETE 404 is ownership-ambiguous → needsReconciliation, not auto-success.
    func test_AN2_T22_pushDeleteNotFoundBecomesNeedsReconciliation() async {
        let mock = MockAnnotationAPIClient()
        mock.deleteContactResult = .success(.notFoundAmbiguous)
        var draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        draft.serverEventId = UUID()
        draft.syncStatus = .synced

        let engine = AnnotationSyncEngine(apiClient: mock)
        let result = await engine.pushDelete(draft: draft, videoId: "vid-1")

        XCTAssertEqual(result.syncStatus, .needsReconciliation)
        XCTAssertEqual(result.failureReason, "delete_404_ambiguous")
    }

    // AN2-T23: reconcile finds the event on the server → synced with server state applied.
    func test_AN2_T23_reconcileFindsEventOnServerBecomesSynced() async throws {
        let mock = MockAnnotationAPIClient()
        var draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        draft.syncStatus = .needsReconciliation

        let serverEvent = makeServerEvent(deviceEventId: draft.deviceEventId, contactType: "head", side: "center", version: 2)
        mock.listContactsResult = .success(ContactEventListOut(videoId: "vid-1", annotationStatus: "in_progress", events: [serverEvent]))

        let engine = AnnotationSyncEngine(apiClient: mock)
        var session = makeSession(drafts: [draft])
        try await engine.reconcile(session: &session)

        XCTAssertEqual(session.drafts[0].syncStatus, .synced)
        XCTAssertEqual(session.drafts[0].serverEventId, serverEvent.eventId)
        XCTAssertEqual(session.drafts[0].version, 2)
    }

    // AN2-T24: reconcile finds the event absent from the server → deleted.
    func test_AN2_T24_reconcileEventAbsentFromServerBecomesDeleted() async throws {
        let mock = MockAnnotationAPIClient()
        var draft = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        draft.syncStatus = .needsReconciliation
        draft.serverEventId = UUID()

        mock.listContactsResult = .success(ContactEventListOut(videoId: "vid-1", annotationStatus: "in_progress", events: []))

        let engine = AnnotationSyncEngine(apiClient: mock)
        var session = makeSession(drafts: [draft])
        try await engine.reconcile(session: &session)

        XCTAssertEqual(session.drafts[0].syncStatus, .deleted)
    }

    // AN2-T25: flushPending pushes localOnly creates and skips never-synced
    // drafts that were deleted locally before ever reaching the server.
    func test_AN2_T25_flushPendingSyncsCreatesAndSkipsLocallyDeletedNeverSynced() async {
        let mock = MockAnnotationAPIClient()
        let toCreate = ContactEventDraft.new(timestampMs: 1, contactType: "head", side: "center", annotationConfidence: "certain")
        var toSkip = ContactEventDraft.new(timestampMs: 2, contactType: "chest", side: "center", annotationConfidence: "certain")
        toSkip.deletedLocally = true

        let serverEvent = makeServerEvent(deviceEventId: toCreate.deviceEventId, contactType: "head", side: "center", version: 1)
        mock.createContactResult = .success(CreateContactResult(event: serverEvent, isNew: true))

        let engine = AnnotationSyncEngine(apiClient: mock)
        var session = makeSession(drafts: [toCreate, toSkip])
        await engine.flushPending(session: &session)

        let created = session.drafts.first { $0.deviceEventId == toCreate.deviceEventId }!
        let skipped = session.drafts.first { $0.deviceEventId == toSkip.deviceEventId }!

        XCTAssertEqual(created.syncStatus, .synced)
        XCTAssertEqual(created.serverEventId, serverEvent.eventId)
        XCTAssertEqual(skipped.syncStatus, .deleted)
    }

    // MARK: — Helpers

    private func makeSession(drafts: [ContactEventDraft]) -> AnnotationSessionFile {
        AnnotationSessionFile(
            schemaVersion: 1, userId: 1, videoId: "vid-1",
            taxonomyVersion: "v1", lastUpdatedAt: Date(),
            drafts: drafts, checksum: ""
        )
    }

    private func makeServerEvent(
        deviceEventId: UUID, contactType: String, side: String?, version: Int
    ) -> ContactEventOut {
        ContactEventOut(
            eventId: UUID(),
            deviceEventId: deviceEventId,
            timestampMs: 1,
            contactType: contactType,
            side: side,
            annotationConfidence: "certain",
            annotationReviewStatus: "pending",
            taxonomyReviewStatus: "not_applicable",
            excludedFromTraining: true,
            customLabel: nil,
            customDescription: nil,
            version: version,
            createdAt: Date(),
            updatedAt: Date()
        )
    }
}
