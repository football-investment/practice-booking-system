import Foundation
import WebKit

// Weak proxy breaks the WKUserContentController → handler retain cycle.
private final class WeakMessageHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ target: WKScriptMessageHandler) { self.target = target }

    func userContentController(_ ucc: WKUserContentController,
                                didReceive message: WKScriptMessage) {
        target?.userContentController(ucc, didReceive: message)
    }
}

// MARK: — SkeletonBridge

// Manages a transparent WKWebView and drives it with SkeletonFrame JSON at ≤20 FPS.
//
// Threading: feed() and all @Published mutations run on the main thread.
// evaluateJavaScript must be called from main thread (WKWebView requirement).

final class SkeletonBridge: NSObject, ObservableObject,
                             WKScriptMessageHandler,
                             WKNavigationDelegate {

    @Published private(set) var isReady:         Bool  = false
    @Published private(set) var isEnabled:        Bool  = true
    @Published private(set) var bridgeLatencyMs:  Int   = 0
    @Published private(set) var evalRoundtripMs:  Int   = 0
    @Published private(set) var totalSent:        Int   = 0
    @Published private(set) var droppedFrames:    Int   = 0

    private(set) var webView: WKWebView

    private var isSending:     Bool            = false
    private var lastSendMs:    Int64           = 0
    private var lastFrame:     SkeletonFrame?  = nil
    private let minIntervalMs: Int64           = 50
    private let encoder:       JSONEncoder     = JSONEncoder()

    override init() {
        let ucc    = WKUserContentController()
        let config = WKWebViewConfiguration()
        config.userContentController = ucc

        let wv = WKWebView(frame: .zero, configuration: config)
        wv.isOpaque                   = false
        wv.backgroundColor            = .clear
        wv.isUserInteractionEnabled   = false
        wv.scrollView.isScrollEnabled = false
        wv.scrollView.bounces         = false
        self.webView = wv

        super.init()

        let proxy = WeakMessageHandler(self)
        ucc.add(proxy, name: "skeletonReady")
        ucc.add(proxy, name: "bridgeLatency")
        wv.navigationDelegate = self
    }

    deinit {
        webView.configuration.userContentController.removeAllScriptMessageHandlers()
    }

    func loadReceiver() {
        guard let url = Bundle.main.url(forResource: "skeleton_receiver", withExtension: "html") else {
            print("[SkeletonBridge] skeleton_receiver.html not found in bundle.")
            return
        }
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }

    func setEnabled(_ enabled: Bool) { isEnabled = enabled }

    func feed(frame: SkeletonFrame) {
        guard isEnabled else { return }

        let now = Int64(Date().timeIntervalSince1970 * 1000)
        guard now - lastSendMs >= minIntervalMs else { droppedFrames += 1; return }
        guard !isSending                        else { droppedFrames += 1; return }
        guard isReady                           else { lastFrame = frame; return }

        lastSendMs = now
        sendNow(frame)
    }

    func userContentController(_ ucc: WKUserContentController,
                                didReceive message: WKScriptMessage) {
        switch message.name {
        case "skeletonReady":
            isReady = true
            if let pending = lastFrame { lastFrame = nil; sendNow(pending) }
        case "bridgeLatency":
            if let ms = message.body as? Int         { bridgeLatencyMs = ms }
            else if let ms = message.body as? Double { bridgeLatencyMs = Int(ms) }
        default: break
        }
    }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation _: WKNavigation!) {
        isReady = false; isSending = false; lastFrame = nil
    }

    func webView(_ webView: WKWebView, didFail _: WKNavigation!, withError error: Error) {
        print("[SkeletonBridge] Navigation failed: \(error.localizedDescription)")
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation _: WKNavigation!,
                 withError error: Error) {
        print("[SkeletonBridge] Provisional navigation failed: \(error.localizedDescription)")
    }

    private func sendNow(_ frame: SkeletonFrame) {
        guard let data = try? encoder.encode(frame),
              let json = String(data: data, encoding: .utf8) else { return }

        isSending  = true
        totalSent += 1
        let t0     = CFAbsoluteTimeGetCurrent()

        webView.evaluateJavaScript("window.onSkeletonFrame(\(json))") { [weak self] _, error in
            let rtt = Int((CFAbsoluteTimeGetCurrent() - t0) * 1000)
            DispatchQueue.main.async {
                self?.evalRoundtripMs = rtt
                self?.isSending       = false
            }
            if let error { print("[SkeletonBridge] JS error: \(error.localizedDescription)") }
        }
    }
}
