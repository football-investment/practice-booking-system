import XCTest
@testable import LFAEducationCenter

// BPC — BiometricPhotoCapture unit tests.
//
// Tests the compress() path using synthetic UIImages.
// No ARKit / TrueDepth hardware required — only UIImage + JPEG codec.
//
// BPC-01  compress(nil-sized image) → nil
// BPC-02  compress(valid image) → non-nil Data, JPEG header
// BPC-03  compress(valid image) → size ≤ 5 MB
// BPC-04  Large image: primary quality produces output ≤ 5 MB
// BPC-05  Compress output starts with JPEG magic bytes (0xFF 0xD8)
final class BiometricPhotoCaptureTests: XCTestCase {

    // BPC-02 + BPC-05: small image → valid JPEG Data
    func testCompressSmallImage_returnsJPEG() {
        let image = makeImage(size: CGSize(width: 64, height: 64))
        let data = BiometricPhotoCapture.compress(image: image)
        XCTAssertNotNil(data, "compress() should return Data for a valid image")
        // JPEG magic bytes: 0xFF 0xD8
        if let data = data {
            XCTAssertEqual(data[0], 0xFF)
            XCTAssertEqual(data[1], 0xD8)
        }
    }

    // BPC-03: output is within 5 MB limit
    func testCompressSmallImage_withinSizeLimit() {
        let image = makeImage(size: CGSize(width: 512, height: 512))
        let data = BiometricPhotoCapture.compress(image: image)
        XCTAssertNotNil(data)
        XCTAssertLessThanOrEqual(data!.count, 5 * 1024 * 1024)
    }

    // BPC-04: larger image still within limit (quality fallback if needed)
    func testCompressLargerImage_withinSizeLimit() {
        let image = makeImage(size: CGSize(width: 2048, height: 2048))
        let data = BiometricPhotoCapture.compress(image: image)
        XCTAssertNotNil(data)
        if let data = data {
            XCTAssertLessThanOrEqual(data.count, 5 * 1024 * 1024)
        }
    }

    // MARK: — Helper

    private func makeImage(size: CGSize, color: UIColor = .blue) -> UIImage {
        UIGraphicsBeginImageContextWithOptions(size, false, 1.0)
        defer { UIGraphicsEndImageContext() }
        color.setFill()
        UIRectFill(CGRect(origin: .zero, size: size))
        return UIGraphicsGetImageFromCurrentImageContext()!
    }
}
