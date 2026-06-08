import PhotosUI
import SwiftUI

// UIViewControllerRepresentable wrapping PHPickerViewController.
// Single-image selection, no crop, no camera — MVP scope.
// Calls onImagePicked on the main thread when the user confirms selection.
// Dismisses the picker automatically (picker.dismiss is called by the coordinator).
// Named ProfilePhotoPicker to avoid collision with the private PhotoPicker in RegisterView.
struct ProfilePhotoPicker: UIViewControllerRepresentable {

    let onImagePicked: (UIImage) -> Void

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config            = PHPickerConfiguration(photoLibrary: .shared())
        config.filter         = .images
        config.selectionLimit = 1
        let picker            = PHPickerViewController(configuration: config)
        picker.delegate       = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(onImagePicked: onImagePicked) }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        private let onImagePicked: (UIImage) -> Void

        init(onImagePicked: @escaping (UIImage) -> Void) {
            self.onImagePicked = onImagePicked
        }

        func picker(_ picker: PHPickerViewController,
                    didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)
            guard let result = results.first,
                  result.itemProvider.canLoadObject(ofClass: UIImage.self) else { return }
            result.itemProvider.loadObject(ofClass: UIImage.self) { [weak self] object, _ in
                guard let image = object as? UIImage else { return }
                DispatchQueue.main.async { self?.onImagePicked(image) }
            }
        }
    }
}
