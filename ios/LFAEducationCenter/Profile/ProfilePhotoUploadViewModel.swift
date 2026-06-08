import UIKit

// MARK: — Response

private struct ProfilePhotoUploadResponse: Decodable {
    let profilePhotoUrl: String
    let status:          String
    enum CodingKeys: String, CodingKey {
        case profilePhotoUrl = "profile_photo_url"
        case status
    }
}

// MARK: — State

enum PhotoUploadState {
    case idle
    case preview(UIImage)   // image selected, not yet uploaded
    case uploading          // POST in flight
    case success            // 201 received
    case error(String)      // user-readable message
}

// MARK: — ViewModel

@MainActor
final class ProfilePhotoUploadViewModel: ObservableObject {

    @Published private(set) var state: PhotoUploadState = .idle

    // 5 MB hard cap — mirrors backend _MAX_BYTES
    private let maxBytes = 5 * 1024 * 1024

    func selectImage(_ image: UIImage) {
        state = .preview(image)
    }

    func upload(using authManager: AuthManager) async {
        guard case .preview(let image) = state else { return }

        // JPEG at 0.85 quality — MIME image/jpeg, FastAPI field name "photo"
        guard let jpegData = image.jpegData(compressionQuality: 0.85) else {
            state = .error("Could not process the selected image. Please try another photo.")
            return
        }

        if jpegData.count > maxBytes {
            state = .error("The selected photo is too large (max 5 MB). Please choose a smaller image.")
            return
        }

        state = .uploading

        do {
            let _: ProfilePhotoUploadResponse = try await authManager.authenticatedMultipartPost(
                path:      "/api/v1/users/me/profile-photo",
                imageData: jpegData,
                mimeType:  "image/jpeg",
                fieldName: "photo"
            )
            state = .success

        } catch APIError.httpError(let code, let detail) {
            switch code {
            case 400:
                state = .error(detail ?? "Invalid photo. Please choose a JPEG, PNG, or WEBP image under 5 MB.")
            case 401:
                state = .error("Your session has expired. Please sign in again.")
            default:
                state = .error("Upload failed (error \(code)). Please try again.")
            }
        } catch APIError.unauthorized {
            state = .error("Your session has expired. Please sign in again.")
        } catch {
            state = .error("Network error. Check your connection and try again.")
        }
    }

    func reset() {
        state = .idle
    }
}
