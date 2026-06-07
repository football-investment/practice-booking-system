import AVFoundation
import SwiftUI

final class CameraManager: NSObject, ObservableObject {
    let session = AVCaptureSession()

    @Published var isAuthorized = false
    @Published var authDenied   = false

    var detector: BodyPoseDetector?

    private let cameraQueue = DispatchQueue(label: "com.lfa.camera", qos: .userInitiated)

    func requestPermissionAndStart() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            isAuthorized = true
            start()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    self?.isAuthorized = granted
                    self?.authDenied   = !granted
                }
                if granted { self?.start() }
            }
        case .denied, .restricted:
            DispatchQueue.main.async { [weak self] in
                self?.authDenied = true
            }
        @unknown default:
            break
        }
    }

    private func start() {
        guard !session.isRunning else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.configure()
            self?.session.startRunning()
        }
    }

    private func configure() {
        session.beginConfiguration()
        session.sessionPreset = .high

        guard
            let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
            let input  = try? AVCaptureDeviceInput(device: device),
            session.canAddInput(input)
        else {
            session.commitConfiguration()
            return
        }
        session.addInput(input)

        if let detector = detector {
            let dataOutput = AVCaptureVideoDataOutput()
            dataOutput.videoSettings = [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
            ]
            dataOutput.alwaysDiscardsLateVideoFrames = true
            dataOutput.setSampleBufferDelegate(detector, queue: cameraQueue)

            if session.canAddOutput(dataOutput) {
                session.addOutput(dataOutput)

                if let conn = dataOutput.connection(with: .video) {
                    conn.videoOrientation = .portrait
                    conn.isVideoMirrored  = false
                }
            }
        }

        session.commitConfiguration()
    }

    func stop() {
        guard session.isRunning else { return }
        session.stopRunning()
    }
}

// MARK: — SwiftUI camera preview

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> PreviewView {
        let view = PreviewView()
        view.previewLayer.session      = session
        view.previewLayer.videoGravity = .resizeAspectFill
        // Explicit portrait lock — AVCaptureVideoPreviewLayer defaults to .landscapeRight.
        if let conn = view.previewLayer.connection, conn.isVideoOrientationSupported {
            conn.videoOrientation = .portrait
        }
        return view
    }

    func updateUIView(_ uiView: PreviewView, context: Context) {}

    final class PreviewView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer {
            layer as! AVCaptureVideoPreviewLayer
        }
    }
}
