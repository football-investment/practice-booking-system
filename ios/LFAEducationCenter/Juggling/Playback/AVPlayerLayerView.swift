import AVFoundation
import SwiftUI

// MARK: — AVPlayerLayerView

/// UIViewRepresentable that renders an AVPlayer via AVPlayerLayer.
///
/// Usage:
///   if let player = controller.avPlayer {
///       AVPlayerLayerView(player: player)
///   }
///
/// Design notes:
/// - videoGravity is always .resizeAspect (letter-box, no crop).
/// - updateUIView handles in-place player swap without recreating the hosting view.
/// - dismantleUIView nils the layer's player to break the retain cycle before dealloc.
/// - Background is black so letter-box bars match the annotation screen chrome.
struct AVPlayerLayerView: UIViewRepresentable {
    let player: AVPlayer

    func makeUIView(context: Context) -> _AVPlayerLayerHostView {
        let view = _AVPlayerLayerHostView()
        view.playerLayer.player        = player
        view.playerLayer.videoGravity  = .resizeAspect
        view.backgroundColor           = .black
        return view
    }

    func updateUIView(_ uiView: _AVPlayerLayerHostView, context: Context) {
        // Only reassign when the player actually changes — avoids AVPlayerLayer reset cost.
        if uiView.playerLayer.player !== player {
            uiView.playerLayer.player = player
        }
    }

    static func dismantleUIView(_ uiView: _AVPlayerLayerHostView, coordinator: ()) {
        // Break the player→layer retain cycle before the view is deallocated.
        uiView.playerLayer.player = nil
    }
}

// MARK: — _AVPlayerLayerHostView

/// UIView whose backing CALayer is AVPlayerLayer.
///
/// Overriding layerClass is the documented Apple pattern for embedding
/// AVPlayerLayer (Technical Q&A QA1668). The force-cast is unconditionally
/// safe because `layerClass` guarantees the layer type at init time.
final class _AVPlayerLayerHostView: UIView {
    override class var layerClass: AnyClass { AVPlayerLayer.self }

    var playerLayer: AVPlayerLayer {
        // Safe: layerClass guarantees this cast.
        layer as! AVPlayerLayer  // swiftlint:disable:this force_cast
    }
}
