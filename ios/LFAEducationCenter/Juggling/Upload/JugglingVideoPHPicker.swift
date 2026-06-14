import SwiftUI
import PhotosUI

// MARK: — JugglingVideoPHPicker
//
// iOS 14-compatible PHPickerViewController wrapper. Filters to videos only.
// The coordinator copies the selected video to a controlled temp URL and
// determines MIME from the file extension before dispatching onPick on the main queue.
// The caller (onPick closure) receives ownership of the temp file and is responsible
// for cleaning it up — typically by passing it to JugglingVideoUploadViewModel.

struct JugglingVideoPHPicker: UIViewControllerRepresentable {

    let onPick: (URL, String) -> Void
    let onCancel: () -> Void

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.filter = .videos
        config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick, onCancel: onCancel)
    }

    // MARK: — Coordinator

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        private let onPick: (URL, String) -> Void
        private let onCancel: () -> Void

        init(onPick: @escaping (URL, String) -> Void, onCancel: @escaping () -> Void) {
            self.onPick = onPick
            self.onCancel = onCancel
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)
            guard let provider = results.first?.itemProvider,
                  provider.hasItemConformingToTypeIdentifier("public.movie") else {
                onCancel()
                return
            }
            provider.loadFileRepresentation(forTypeIdentifier: "public.movie") { [weak self] url, _ in
                guard let strongSelf = self else { return }
                guard let sourceURL = url else {
                    DispatchQueue.main.async { strongSelf.onCancel() }
                    return
                }
                let ext = sourceURL.pathExtension.lowercased()
                let mimeType: String
                switch ext {
                case "mov":  mimeType = "video/quicktime"
                case "m4v":  mimeType = "video/x-m4v"
                default:     mimeType = "video/mp4"
                }
                let tempURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString)
                    .appendingPathExtension(ext.isEmpty ? "mp4" : ext)
                do {
                    try FileManager.default.copyItem(at: sourceURL, to: tempURL)
                    DispatchQueue.main.async { strongSelf.onPick(tempURL, mimeType) }
                } catch {
                    DispatchQueue.main.async { strongSelf.onCancel() }
                }
            }
        }
    }
}
