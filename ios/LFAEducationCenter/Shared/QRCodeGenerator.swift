import CoreImage
import UIKit

// Generates a QR code UIImage from an arbitrary string using CoreImage.
// No external dependencies — CIQRCodeGenerator is available since iOS 7.
//
// Usage:
//   let img = QRCodeGenerator.image(from: "https://lfa.hu/verify/...")
//
// The output is a square black-on-white UIImage, scaled 10× to avoid
// pixelation when rendered at small sizes (e.g. the 56×56 pt card panel).
enum QRCodeGenerator {
    static func image(from string: String, scale: CGFloat = 10) -> UIImage? {
        guard
            let data   = string.data(using: .ascii),
            let filter = CIFilter(name: "CIQRCodeGenerator")
        else { return nil }

        filter.setValue(data,  forKey: "inputMessage")
        filter.setValue("M",   forKey: "inputCorrectionLevel") // ~15 % ECC

        guard let output = filter.outputImage else { return nil }

        let scaled = output.transformed(by: CGAffineTransform(scaleX: scale, y: scale))

        // CIImage-backed UIImage does not render in SwiftUI Image(uiImage:).
        // Rasterise to CGImage via CIContext so both AcademyIDFullScreenView
        // (200 pt) and AcademyIDCardView (56 pt) display correctly.
        let context = CIContext()
        guard let cgImage = context.createCGImage(scaled, from: scaled.extent) else { return nil }
        return UIImage(cgImage: cgImage)
    }
}
