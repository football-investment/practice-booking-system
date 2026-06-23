# Roadmap: QR Code Session Join

**Status:** Planned — follow-up PR after PR #332 merge
**Depends on:** PR #332 lifecycle fix (physical E2E validated)
**Priority:** High (blocks usable multi-device testing)

## Payload Schema

```json
{
  "type": "lfa_multicamera_join",
  "v": 1,
  "session_uuid": "79597f96-85ec-469f-a491-9658d418f901"
}
```

- `type`: discriminator — reject unknown types with clear error
- `v`: schema version — reject unsupported versions with "update app" message
- `session_uuid`: the session to join

## Acceptance Criteria

### Instructor (iPad) — QR Display
- [ ] After session creation, QR code displayed in lobby using existing `QRCodeGenerator`
- [ ] QR encodes the full JSON payload (not just bare UUID)
- [ ] QR is large enough to scan from 1 meter distance
- [ ] QR updates if session is cancelled and recreated

### Player (iPhone) — QR Scanner
- [ ] "Scan QR to Join" button visible in idle state
- [ ] Scanner opens as sheet/fullscreen with camera viewfinder
- [ ] Successful scan auto-fills UUID and initiates join
- [ ] Manual UUID text field remains as fallback
- [ ] Scanner dismisses after successful scan

### Error Handling
- [ ] Wrong `type` field → "Ez nem session QR-kód"
- [ ] Unsupported `v` → "Frissítsd az alkalmazást"
- [ ] Missing/malformed `session_uuid` → "Érvénytelen QR-kód"
- [ ] Session not found (404) → "Session nem található"
- [ ] Session full → "Session megtelt"
- [ ] Duplicate scan (same user) → idempotent success (backend returns existing participant)

### Camera Permission & Lifecycle
- [ ] Scanner uses ephemeral `AVCaptureSession` — created on open, `stopRunning()` on dismiss
- [ ] Scanner output and delegate released on dismiss
- [ ] Camera permission denial → clear message + manual UUID fallback
- [ ] Camera interruption (phone call, etc.) → scanner pauses, resumes on return
- [ ] App background → scanner pauses
- [ ] **Physical test:** QR scan → dismiss scanner → arm capture → recording starts successfully
- [ ] **Physical test:** Prove no AVCaptureSession conflict between scanner and capture manager

### Multi-Scenario
- [ ] Scenario B: 1 instructor iPad QR → 1 player iPhone scan → join
- [ ] Scenario C: 1 instructor iPad QR → 2 player iPhones scan sequentially → both join
- [ ] Scenario A: 1 STUDENT iPad QR → 1 STUDENT iPhone scan → join

### Tests
- [ ] Unit: QR payload encode/decode round-trip
- [ ] Unit: payload validation (wrong type, wrong version, missing UUID)
- [ ] Unit: scanner delegate mock — metadata output → joinSession call
- [ ] Integration: scan → join → session state updated with new participant
- [ ] Physical: QR scan → capture arm → recording (no camera conflict)

## Files

| File | Action | Lines (est.) |
|------|--------|-------------|
| `QRCodeGenerator.swift` | Reuse existing | 0 |
| `SessionQRPayload.swift` | NEW — Codable struct + validation | ~40 |
| `QRScannerView.swift` | NEW — AVCaptureMetadataOutput + UIViewRepresentable | ~100 |
| `MultiCameraLobbyView.swift` | Modify — QR display + scan button | ~30 |
| `MultiCameraSessionViewModel.swift` | Modify — scan result → joinSession | ~10 |
| Tests | NEW | ~80 |
