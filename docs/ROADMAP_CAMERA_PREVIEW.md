# Roadmap: Live Camera Preview

**Status:** Planned — follow-up PR after QR Join PR
**Depends on:** PR #332 lifecycle fix + QR Join PR
**Priority:** High (users cannot verify camera framing before/during recording)

## Architecture Audit (Required Before Implementation)

### Ownership
- `SessionCaptureManager` owns `private let captureSession = AVCaptureSession()`
- Session is configured on `captureQueue` (background, `.userInitiated`)
- Session is `startRunning()` on `captureQueue` during `prepare()`
- Session is NOT exposed — a new property is needed

### Thread Safety
- `AVCaptureVideoPreviewLayer.session` assignment on main thread is safe per Apple docs
- But `captureSession` configuration (addInput/addOutput) happens on `captureQueue`
- Preview layer must be added AFTER `commitConfiguration()`, not during
- Must verify: no `startRunning()` / `stopRunning()` race between preview and recording

### Exposure Strategy — To Be Validated
```swift
// SessionCaptureManager — proposed, needs ownership/lifecycle proof
var captureSessionForPreview: AVCaptureSession? {
    guard state != .idle && state != .tornDown else { return nil }
    return captureSession
}
```

**Open questions (must be answered with code evidence before accepting):**
1. What happens if SwiftUI view holding the preview layer is deallocated while session runs?
2. Does `AVCaptureVideoPreviewLayer` retain the session? (Yes — must break cycle)
3. When `teardown()` calls `stopRunning()`, does the preview layer handle this gracefully?
4. What happens on `UIScene.didEnterBackground` — does preview auto-pause?

## Acceptance Criteria

### Preview Lifecycle by State

| Orchestration State | Preview | Overlay |
|---------------------|---------|---------|
| `idle` | Hidden | — |
| `arming` | "Kamera előkészítés…" placeholder | — |
| `armed` | Live preview | — |
| `scheduled(fireAt:)` | Live preview | Countdown to fireAt |
| `starting` | Live preview | "Indítás…" |
| `capturing` | Live preview | 🔴 REC + elapsed time |
| `stopping` | Live preview freezes | "Leállítás…" |
| `completed` | Hidden | File info |
| `failed` | Hidden | Error message |

### UI Requirements
- [ ] Preview uses `AVCaptureVideoPreviewLayer` via `UIViewRepresentable`
- [ ] Same `AVCaptureSession` instance as recording — no second session
- [ ] Correct aspect ratio (`.resizeAspectFill` or `.resizeAspect` — TBD)
- [ ] Portrait orientation on both iPhone and iPad
- [ ] Responsive layout — adapts to device screen size
- [ ] REC indicator: red circle + "REC" text + elapsed time (MM:SS)
- [ ] Camera and microphone permission status badges

### Safety
- [ ] No duplicate `startRunning()` — preview layer piggybacks on existing running session
- [ ] No duplicate `stopRunning()` — `teardown()` is the single stop authority
- [ ] Preview layer retain cycle broken in `dismantleUIView` (follow AVPlayerLayerView pattern)
- [ ] App background: preview pauses (system handles this for AVCaptureVideoPreviewLayer)
- [ ] Camera interruption (phone call): preview shows interrupted state
- [ ] Orientation change: preview layer connection orientation updated
- [ ] Permission denied after initial grant: preview shows permission error

### Proof of Same Session
- [ ] Unit test: `previewLayer.session === captureManager.captureSession`
- [ ] Physical test: preview shows same frame as recorded .mov first frame
- [ ] No second `AVCaptureSession()` instantiation in preview code

### Tests
- [ ] Unit: preview property returns nil in idle/tornDown
- [ ] Unit: preview property returns non-nil in armed/capturing
- [ ] Unit: same AVCaptureSession instance as recording
- [ ] Unit: preview layer removed after teardown
- [ ] Integration: arm → preview visible → capture → REC overlay → stop → preview hidden
- [ ] Physical: recorded .mov content matches what preview showed
- [ ] Physical: iPhone + iPad layout correct

## Files

| File | Action | Lines (est.) |
|------|--------|-------------|
| `SessionCaptureManager.swift` | Modify — expose captureSession property | ~5 |
| `CapturePreviewView.swift` | NEW — UIViewRepresentable + AVCaptureVideoPreviewLayer | ~50 |
| `CaptureOverlayView.swift` | NEW — REC dot + elapsed time + state label | ~40 |
| `MultiCameraLobbyView.swift` | Modify — preview panel above Capture section | ~30 |
| `CaptureProtocols.swift` | Modify — add preview protocol if needed | ~5 |
| Tests | NEW | ~60 |
