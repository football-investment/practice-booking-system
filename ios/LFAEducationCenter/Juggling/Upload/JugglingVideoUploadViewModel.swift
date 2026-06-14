import Foundation
import Combine

// MARK: — JugglingVideoUploadViewModel
//
// State machine: idle → selecting → preparing → uploading(progress) → completing → success
//                                  ↘ failure (any step)
//
// Temp-file lifecycle: coordinator copies picked video → controlled tempVideoURL.
// This ViewModel owns the file from pickerDidSelect until cleanup (success/failure/cancel).
// All cleanup is deterministic; no orphan files after any terminal transition.

@MainActor
final class JugglingVideoUploadViewModel: ObservableObject {

    // MARK: — State

    enum UploadState: Equatable {
        case idle
        case selecting
        case preparing
        case uploading(progress: Double)
        case completing
        case success
        case failure(JugglingUploadError)

        static func == (lhs: UploadState, rhs: UploadState) -> Bool {
            switch (lhs, rhs) {
            case (.idle, .idle), (.selecting, .selecting), (.preparing, .preparing),
                 (.completing, .completing), (.success, .success):
                return true
            case (.uploading(let a), .uploading(let b)):
                return a == b
            case (.failure(let a), .failure(let b)):
                return a == b
            default:
                return false
            }
        }
    }

    // MARK: — Published

    @Published private(set) var state: UploadState = .idle

    // MARK: — Callback (fired exactly once, on the main actor, after completeUpload succeeds)

    var onSuccess: (() -> Void)?

    // MARK: — Computed

    var isActive: Bool {
        switch state {
        case .preparing, .uploading, .completing: return true
        default: return false
        }
    }

    var errorMessage: String? {
        guard case .failure(let err) = state else { return nil }
        return err.errorDescription
    }

    // MARK: — Internal (exposed via @testable for unit tests)

    private(set) var uploadTask: Task<Void, Never>?

    // MARK: — Private

    private let apiClient: JugglingAnnotationAPIClientProtocol
    private let maxFileSizeBytes: Int64
    private var tempVideoURL: URL?
    private var currentVideoId: String?

    private static let supportedMIMETypes: Set<String> = [
        "video/mp4", "video/quicktime", "video/x-m4v"
    ]

    // MARK: — Init

    init(
        apiClient: JugglingAnnotationAPIClientProtocol,
        maxFileSizeBytes: Int64 = 100 * 1024 * 1024
    ) {
        self.apiClient = apiClient
        self.maxFileSizeBytes = maxFileSizeBytes
    }

    // MARK: — Picker lifecycle

    func startPicker() {
        guard state == .idle else { return }
        state = .selecting
    }

    func pickerCancelled() {
        guard case .selecting = state else { return }
        state = .idle
    }

    // Called by JugglingVideoPHPicker.Coordinator after copying the picked video to a
    // controlled temp URL and determining the MIME type. Ownership of tempURL transfers
    // here; this ViewModel is responsible for deleting it in all terminal paths.
    func pickerDidSelect(tempURL: URL, mimeType: String) {
        guard case .selecting = state else { return }
        state = .preparing
        uploadTask = Task { [self] in
            await prepareAndUpload(tempURL: tempURL, mimeType: mimeType)
        }
    }

    // MARK: — Upload control

    func cancel() {
        uploadTask?.cancel()
        uploadTask = nil
        cleanupTempFile()
        currentVideoId = nil
        state = .idle
    }

    // Resets to idle so the caller can invoke startPicker() for a fresh attempt.
    // Each retry must supply a new temp file via a new picker session.
    func retry() {
        guard case .failure = state else { return }
        cleanupTempFile()
        currentVideoId = nil
        uploadTask = nil
        state = .idle
    }

    // MARK: — Pipeline

    private func prepareAndUpload(tempURL: URL, mimeType: String) async {
        guard !Task.isCancelled else {
            try? FileManager.default.removeItem(at: tempURL)
            return
        }

        guard Self.supportedMIMETypes.contains(mimeType) else {
            try? FileManager.default.removeItem(at: tempURL)
            state = .failure(.unsupportedFormat)
            return
        }

        let size: Int64
        do {
            let attrs = try FileManager.default.attributesOfItem(atPath: tempURL.path)
            size = (attrs[.size] as? Int64) ?? 0
        } catch {
            try? FileManager.default.removeItem(at: tempURL)
            state = .failure(.networkError(error))
            return
        }

        guard size <= maxFileSizeBytes else {
            try? FileManager.default.removeItem(at: tempURL)
            state = .failure(.fileTooLarge)
            return
        }

        guard !Task.isCancelled else {
            try? FileManager.default.removeItem(at: tempURL)
            return
        }

        tempVideoURL = tempURL
        await runUploadPipeline(mimeType: mimeType)
    }

    private func runUploadPipeline(mimeType: String) async {
        guard let tempURL = tempVideoURL else { return }

        do {
            // Step 1 — upload-init
            guard !Task.isCancelled else { cleanupTempFile(); return }
            let initResp = try await apiClient.uploadInit(
                sourceType: "uploaded_video", uploadSource: "gallery"
            )

            guard !Task.isCancelled else { cleanupTempFile(); return }
            currentVideoId = initResp.videoId
            state = .uploading(progress: 0)

            // Step 2 — multipart file upload
            _ = try await apiClient.uploadVideoFile(
                videoId: initResp.videoId, fileURL: tempURL, mimeType: mimeType
            )

            // Step 3 — complete (triggers server-side analysis queue)
            guard !Task.isCancelled else { cleanupTempFile(); return }
            state = .completing

            _ = try await apiClient.completeUpload(videoId: initResp.videoId)

            guard !Task.isCancelled else { cleanupTempFile(); return }
            cleanupTempFile()
            currentVideoId = nil
            state = .success
            onSuccess?()

        } catch is CancellationError {
            cleanupTempFile()
        } catch let err as JugglingUploadError {
            cleanupTempFile()
            state = .failure(err)
        } catch {
            cleanupTempFile()
            state = .failure(.networkError(error))
        }
    }

    private func cleanupTempFile() {
        guard let url = tempVideoURL else { return }
        try? FileManager.default.removeItem(at: url)
        tempVideoURL = nil
    }
}
