# AN-3B2B1 — B1 iOS Ball Feedback UI: Audit & Implementation Plan

**Branch:** `feat/an3b2b1-ios-feedback-ui`  
**Státusz:** TERV — implementáció csak jóváhagyás után  
**Dátum:** 2026-06-18  
**Előfeltétel:** PR #303 MERGED (main HEAD: `6f8c1efd`)  
**B0 backend:** KÉSZ (`main`-en: migration `2026_06_18_2000`, `ball_feedback_service.py`, 479 teszt PASS)

---

## 1. Jelenlegi iOS juggling annotation UI állapot

### 1.1 Képernyő-struktúra (`JugglingAnnotationScreen.swift`)

```
NavigationView
  GeometryReader → VStack
    videoArea(in:)                    ← ZStack: videó + overlays + togglek
    PlaybackControlBar                ← play/pause/scrub/rotate
    statusBar                         ← szinkron státusz
    generatePosesBanner               ← feltételes
    EventTimelineView                 ← idővonal pin-ekkel
    eventList                         ← ScrollView eseménylista
    labelingCTA                       ← feltételes
    saveAndCloseButton
```

### 1.2 `videoArea` ZStack rétegek (bottom → top)

| Réteg | Típus | Feltétel |
|---|---|---|
| `Color.black` | háttér | mindig |
| `AVPlayerLayerView` | videó | `loaderReady` |
| `ContinuousSkeletonOverlayView` / `PoseSnapshotOverlayView` | skeleton | `showSkeletonOverlay && loaderReady` |
| `BallTrajectoryOverlayView` / `BallVideoOverlayView` / `ballOverlayStatusBanner` | labda | `showBallOverlay && loaderReady` |
| Processing bannerek | ProgressView | `ballTrajectoryVM.status == .processing` |
| Overlay toggle gombok (skeleton + ball) | VStack/HStack | `loaderReady` |

### 1.3 Meglévő ViewModelek és állapotok

| ViewModel / State | Típus | Szerep |
|---|---|---|
| `BallTrajectoryViewModel` | `@StateObject` | Dense trajectory adatok, 100ms polling |
| `DenseSkeletonViewModel` | `@StateObject` | Offline skeleton extraction |
| `JugglingAnnotationViewModel` | `@StateObject` | Event CRUD, sync, ball detections |
| `showBallOverlay` | `@State Bool` | Ball overlay láthatósága |
| `showSkeletonOverlay` | `@State Bool` | Skeleton overlay láthatósága |
| `isBallSelecting` | `@State Bool` | Tap-to-correct mód (AN-3B2C-1) |
| `ballSelectionDragPoint` | `@State CGPoint?` | Drag korrekció pont |

### 1.4 Meglévő ball interaction flow (AN-3B2C-1)

Az `isBallSelecting` mód már létezik: a ball overlay toggle melletti gomb aktiválja, a felhasználó tappel vagy dragel → `handleBallSelection(normalizedPoint:)` → `POST /ball-detection` (manual override). Ez az event-szintű (egyedi contact event) korrekció.

**B1 ettől eltér:** a ball feedback a dense trajectory frame-szintű visszajelzés — nem contact eventre, hanem `frame_ms`-re vonatkozik, és a B0 feedback API-t (`POST /ball-feedback`) használja.

---

## 2. Érintett képernyők és ViewModelek

### 2.1 Érintett (módosítandó)

| Fájl | Változás típusa |
|---|---|
| `JugglingAnnotationScreen.swift` | Új `@StateObject feedbackVM`, új toggle gomb, feedback panel megjelenítése |
| `JugglingAnnotationAPIClient.swift` | 2 új API hívás: `GET /ball-feedback/queue`, `POST /ball-feedback` |

### 2.2 Új fájlok

| Fájl | Leírás |
|---|---|
| `BallFeedbackViewModel.swift` | Queue fetch + feedback submit logika |
| `BallFeedbackDTO.swift` | `BallFeedbackRequest`, `BallFeedbackOut`, `BallFeedbackQueueItem`, `BallFeedbackQueueResponse` — Swift structs |
| `BallFeedbackPanel.swift` | SwiftUI panel — feedback action gombok (confirm / no_ball / corrected / skip) |
| `BallFeedbackOverlayView.swift` | Videó feletti overlay — jelöli a feedback frame pozícióját (ha van predicted x/y) |
| `BallFeedbackVMTests.swift` | Unit tesztek (`BFB-01..N`) |
| `BallFeedbackPanelTests.swift` | Unit tesztek — action → döntés mapping |

### 2.3 Nem érintett

| Fájl | Indok |
|---|---|
| `BallTrajectoryViewModel.swift` | Külön polling VM, B1 nem módosítja |
| `DenseSkeletonViewModel.swift` | Független |
| `JugglingAnnotationViewModel.swift` | Ball detection CRUD itt marad; feedback külön VM |
| `EventLabelDetailView.swift` | Nincs feedback UI event-detail szinten (B1 scope-on kívül) |

---

## 3. Feedback actionök és API mapping

### 3.1 A négy action

| Action | Megjelenítés | API `decision` | Extra mezők |
|---|---|---|---|
| **Confirm** | "Helyes" (zöld pipa) | `"confirm"` | — |
| **No ball** | "Nincs labda" (x szimbólum) | `"no_ball"` | — |
| **Correct position** | "Javítom" (crosshair) → tap/drag | `"corrected"` | `corrected_x`, `corrected_y`, `correction_method: "tap"\|"drag"` |
| **Skip** | "Kihagyom" (nyíl) | nem küld API hívást | client-side: lép a queue következő elemére |

### 3.2 Model context snapshot (mindig küldendő ha elérhető)

A `BallFeedbackRequest` tartalmaz model context mezőket az iOS klienssel küldve — ezeket a `BallFeedbackQueueItem` adja:

```swift
model_predicted_x:    item.modelPredictedX
model_predicted_y:    item.modelPredictedY
model_confidence:     item.modelConfidence
model_tracking_state: item.modelTrackingState
```

### 3.3 "Correct position" flow részlete

1. Felhasználó a "Javítom" gombra koppint → `isFeedbackCorrecting = true`
2. Az overlay interaktívvá válik: `DragGesture` + `TapGesture` a videó területen
3. Felhasználó megjelöli a labda valódi pozícióját
4. `correction_method = "tap"` (single tap) vagy `"drag"` (gesture ended)
5. POST küldés normalizált koordinátákkal (0.0–1.0)
6. Sikeres POST után: frame optimistikusan "submitted" lesz, panel lép a következő queue itemre

### 3.4 Session limit

A backend `max_per_session: 3` értéket ad vissza. A VM session-szinten számolja az elküldött feedback-eket. Ha `submittedCount >= maxPerSession`, a panel ún. "session teljes" állapotba lép (nem további frame-ek jönnek az aktuális session-ben).

---

## 4. API endpointok

### 4.1 `GET /users/me/juggling/videos/{video_id}/ball-feedback/queue`

```
Query:  limit: Int  (default 5, max 20)
Response: BallFeedbackQueueResponse {
    video_id: String
    queue_items: [BallFeedbackQueueItem]
    total: Int
    max_per_session: Int  // = 3
}

BallFeedbackQueueItem {
    frame_ms:                Int
    priority_score:          Float
    model_predicted_x:       Float?
    model_predicted_y:       Float?
    model_confidence:        Float?
    model_tracking_state:    String?  // "detected" | "predicted" | "lost"
    existing_feedback_count: Int
}
```

**iOS viselkedés:** a VM induláskor és feedback-session megnyitásakor hívja meg. Ha `queue_items.isEmpty` → "Nincs visszajelzendő frame" üzenet.

### 4.2 `POST /users/me/juggling/videos/{video_id}/ball-feedback`

```
Body: BallFeedbackRequest {
    frame_ms:             Int    (required)
    decision:             String (required: "confirm"|"reject"|"no_ball"|"corrected")
    corrected_x:          Float? (required if decision="corrected")
    corrected_y:          Float? (required if decision="corrected")
    correction_method:    String? ("tap"|"drag")
    model_predicted_x:    Float?
    model_predicted_y:    Float?
    model_confidence:     Float?
    model_tracking_state: String?
}

Response 201: BallFeedbackOut {
    id:             UUID
    video_id:       UUID
    frame_ms:       Int
    decision:       String
    approval_state: String  // "pending"
    created_at:     DateTime
}

Error 409: user already submitted for this video+frame
Error 404: video not found
Error 503: BALL_FEEDBACK_ENABLED=false
```

### 4.3 Feature flag

Mindkét endpoint `JUGGLING_POC_ENABLED` és `BALL_FEEDBACK_ENABLED` feature flag-et igényel. Ha `503` jön vissza: a feedback panel nem jelenik meg, UI-ban nincs feedback toggle gomb. A VM `isAvailable: Bool` computed property-vel jelzi ezt.

---

## 5. Optimistic update / error rollback terv

### 5.1 Optimistic update flow

```
Felhasználó → action gomb tappel
    ↓
feedbackVM.submitFeedback(decision:, ...) meghívódik
    ↓
[Optimistic] currentQueueItem eltávolítva a helyi listából
             submittedCount += 1
             panel lép a következő queue itemre (vagy "session kész" állapotba)
    ↓
[Async] POST /ball-feedback
    ↓ (success 201)
    feedbackVM.confirmedFrames.insert(frame_ms)
    ↓ (failure 409 — duplicate)
    409 = nem kritikus; a frame már be lett küldve → silent ignore
          optimistic állapot megmarad (nem rollback)
    ↓ (failure 4xx/5xx != 409)
    [Rollback] frame visszakerül a queue elejére
               submittedCount -= 1
               hibaüzenet megjelenik ("Hiba, próbáld újra")
               panel visszaugrik az előző queue itemre
```

### 5.2 Miért nem critical a 409?

A 409 azt jelenti, hogy a felhasználó ugyanazon frame-re már küldött feedback-et. Ez csak akkor fordulhat elő, ha a user gyorsan duplán tappel — az optimistic állapot helyes marad, a frame valóban submitted.

### 5.3 Rollback adatstruktúra

```swift
struct PendingFeedback {
    let queueItem: BallFeedbackQueueItem
    let decision:  String
    let correctedX: Double?
    let correctedY: Double?
    let correctionMethod: String?
}
```

A VM tárolja `inFlight: [Int: PendingFeedback]` (keyed by `frame_ms`). Sikeres 201 után törlődik. Hibánál rollback: visszakerül a queue elejére.

---

## 6. `BallFeedbackViewModel` — belső állapotok

```swift
enum FeedbackSessionState {
    case idle                    // nincs aktív session, toggle ki
    case loading                 // GET queue fut
    case ready([BallFeedbackQueueItem])  // van queue, panel nyitható
    case empty                   // queue_items.isEmpty
    case sessionComplete         // submittedCount >= max_per_session
    case unavailable             // 503 / feature flag off
    case error(String)
}

@MainActor
class BallFeedbackViewModel: ObservableObject {
    @Published var sessionState: FeedbackSessionState = .idle
    @Published var currentQueueIndex: Int = 0
    @Published var submittedCount: Int = 0
    let maxPerSession: Int = 3  // server-provided, cached after first GET

    var currentItem: BallFeedbackQueueItem? { ... }
    var isAvailable: Bool { ... }  // false if unavailable

    func loadQueue() async { ... }
    func submitFeedback(decision: String, correctedX: Double?, correctedY: Double?,
                        correctionMethod: String?) async { ... }
    func skip() { ... }  // nem hív API-t, csak index lép
}
```

---

## 7. `BallFeedbackPanel` UI terv

### 7.1 Elhelyezés

A panel a videó alatt, a `PlaybackControlBar` felett jelenik meg — **nem sheet** (ne blokkolja a videót). Egy sima SwiftUI `VStack` blokk a `videoArea` és `PlaybackControlBar` közé ékelve, `feedbackVM.sessionState == .ready(...)` esetén.

```
[ videoArea ]
[ BallFeedbackPanel ]    ← új, feltételes
[ PlaybackControlBar ]
[ statusBar ]
...
```

### 7.2 Panel layout (portrait nézet)

```
┌──────────────────────────────────────────────┐
│  Frame: 4 230 ms  ·  Bizonytalanság: 78%     │  ← fejléc
│  Labda pozíció: megjelölve az overlay-en      │
├──────────────────────────────────────────────┤
│  [✓ Helyes]  [✗ Nincs labda]                 │  ← 2 gomb sor
│  [✎ Javítom] [→ Kihagyom]                    │
├──────────────────────────────────────────────┤
│  1 / 3 visszajelzés elküldve   [✕ Bezárás]  │  ← lábléc
└──────────────────────────────────────────────┘
```

### 7.3 Feedback mode aktiválása

A meglévő overlay toggle gombsor mellé egy harmadik gomb kerül:

```swift
overlayToggleButton(
    icon: isFeedbackMode ? "hand.thumbsup.circle.fill" : "hand.thumbsup.circle",
    isOn: isFeedbackMode,
    accessLabel: "Labda visszajelzés mód"
) {
    if !isFeedbackMode {
        Task { await feedbackVM.loadQueue() }
    }
    isFeedbackMode.toggle()
}
```

### 7.4 `BallFeedbackOverlayView` — videó feletti jelölés

Ha az aktuális queue item-nek van `modelPredictedX/Y`, a videó területén megjelenik egy referencia kör (hasonló a `BallTrajectoryOverlayView` dot-jához, de más színnel — pl. fehér szegélyű, kék töltésű). Ez segíti a user-t látni, mit kell megerősítenie vagy javítania.

---

## 8. Tesztterv

### 8.1 Unit tesztek — `BallFeedbackVMTests.swift` (BFB-01..BFB-N)

| ID | Teszt |
|---|---|
| BFB-01 | `loadQueue()` → `ready(items)` ha 3 item jön |
| BFB-02 | `loadQueue()` → `empty` ha `queue_items = []` |
| BFB-03 | `loadQueue()` → `unavailable` ha 503 response |
| BFB-04 | `submitFeedback(decision: "confirm")` → optimistic: `currentQueueIndex += 1`, `submittedCount == 1` |
| BFB-05 | `submitFeedback` 409 → silent ignore, optimistic állapot megmarad |
| BFB-06 | `submitFeedback` 500 → rollback: `submittedCount == 0`, frame visszakerül |
| BFB-07 | `skip()` → `currentQueueIndex += 1`, `submittedCount` változatlan |
| BFB-08 | `submittedCount >= 3` → `sessionState == .sessionComplete` |
| BFB-09 | `submitFeedback(decision: "corrected")` correctedX/Y nélkül → precondition fail (assert) |
| BFB-10 | `submitFeedback(decision: "corrected")` correctedX/Y megadva → request helyes |
| BFB-11 | `currentItem` → `nil` ha `currentQueueIndex >= items.count` |
| BFB-12 | Model context snapshot: request tartalmazza `modelPredictedX`, `modelConfidence`, `modelTrackingState` |

### 8.2 Unit tesztek — `BallFeedbackPanelTests.swift` (BFP-01..BFP-N)

| ID | Teszt |
|---|---|
| BFP-01 | `BallFeedbackColorHelper.decisionColor("confirm")` → `.green` |
| BFP-02 | `BallFeedbackColorHelper.decisionColor("no_ball")` → `.red` |
| BFP-03 | Panel nem jelenik meg (`sessionState == .idle`) |
| BFP-04 | Panel megjelenik (`sessionState == .ready([...])`) |

### 8.3 Independence tesztek — `BallFeedbackAnnotationIndependenceTests.swift` (BFI-01..BFI-N)

| ID | Teszt |
|---|---|
| BFI-01 | `feedbackVM.submitFeedback` nem módosít `JugglingAnnotationViewModel` állapotot |
| BFI-02 | `feedbackVM.loadQueue()` nem módosít `ballTrajectoryVM` állapotot |
| BFI-03 | `isFeedbackMode = false` → `BallFeedbackViewModel` polling nem fut |

### 8.4 API client tesztek — `JugglingAnnotationAPIClientFeedbackTests.swift`

| ID | Teszt |
|---|---|
| ACF-01 | `fetchFeedbackQueue(videoId:limit:)` → helyes URL + query param |
| ACF-02 | `submitBallFeedback(videoId:request:)` → helyes JSON body |

**Összesen tervezett: ~20 unit teszt**

---

## 9. Backward compatibility

| Szempont | Kockázat | Kezelés |
|---|---|---|
| `BALL_FEEDBACK_ENABLED=false` | Endpoint 503-at ad | `feedbackVM.isAvailable = false`, toggle gomb rejtett |
| iOS < 15.0 | Nincs (iOS 15.0 a target) | — |
| `queue_items = []` | Nincs visszajelzendő frame | "empty" állapot, "Köszönjük!" üzenet |
| 409 duplicate | Gyors dupla tapp | Silent ignore — optimistic állapot helyes |
| `model_predicted_x == nil` | Lost frame-nél null koordináta | `BallFeedbackOverlayView` nem renderel referencia kört |
| Dense trajectory `status != .complete` | Ball overlay még nem kész | Feedback panel elérhető marad (frame_ms alapú, nem trajectory-dependent) |
| `BallTrajectoryViewModel` polling | Párhuzamos API hívások | Feedback VM és Trajectory VM teljesen független `@StateObject`-ek |

---

## 10. Kockázatok és rollout sorrend

### 10.1 Kockázatok

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| UX: panel elrejti az eseménylistát portrait-ban | Közepes | Magas | Panel max 80pt magasság, kollapsálható |
| UX: "Javítom" mód konfliktusa `isBallSelecting` (AN-3B2C-1) móddal | Közepes | Közepes | Kölcsönösen kizárják egymást: `isFeedbackMode` ki → `isBallSelecting` is ki |
| Incorrect feature flag state: 503 nem várható prod-on | Alacsony | Alacsony | `isAvailable = false` → gomb rejtett, nem crash |
| Queue refresh staleség: user kétszer látja ugyanazt a frame-et | Alacsony | Alacsony | 409 silent ignore; user élményre nincs hatás |
| Optimistic rollback villanás: user UI-ban visszaugrik | Alacsony | Közepes | Animation + hibaüzenet egyértelmű |

### 10.2 Rollout sorrend

| # | Lépés | Fájlok |
|---|---|---|
| C1 | `BallFeedbackDTO.swift` — Swift structs | új |
| C2 | `JugglingAnnotationAPIClient.swift` bővítés — `fetchFeedbackQueue` + `submitBallFeedback` | módosítás |
| C3 | `BallFeedbackViewModel.swift` — állapotgép + submit/rollback logika | új |
| C4 | `BallFeedbackOverlayView.swift` — referencia kör overlay | új |
| C5 | `BallFeedbackPanel.swift` — action gombok panel | új |
| C6 | `JugglingAnnotationScreen.swift` — `@StateObject feedbackVM`, toggle gomb, panel integráció | módosítás |
| C7 | `BallFeedbackVMTests.swift` (BFB-01..12) | új |
| C8 | `BallFeedbackPanelTests.swift` (BFP-01..04) | új |
| C9 | `BallFeedbackAnnotationIndependenceTests.swift` (BFI-01..03) | új |
| C10 | `JugglingAnnotationAPIClientFeedbackTests.swift` (ACF-01..02) | új |

**Minden commit egy C-szám — külön commit, átjárható QA per lépés.**

---

## 11. B0 backend státusz (tájékoztató)

A B0 backend a `6f8c1efd` merge commit-tal mainre került:

| Komponens | Státusz |
|---|---|
| Migration `2026_06_18_2000_add_juggling_ball_feedback_tables` | KÉSZ |
| `JugglingBallFeedback` model + `UserAnnotationReliability` model | KÉSZ |
| `ball_feedback_service.py` (`submit_feedback`, `get_feedback_queue`) | KÉSZ |
| `juggling_ball_feedback.py` endpoint (`POST /ball-feedback`, `GET /ball-feedback/queue`) | KÉSZ |
| 479 backend teszt PASS | KÉSZ |
| `BALL_FEEDBACK_ENABLED` feature flag | KÉSZ (config.py) |

**B1 iOS implementáció kizárólag ezeket a már meglévő endpointokat fogja használni — backend változtatás B1-ben nem szükséges.**

---

## 12. Döntési pontok (jóváhagyást igényelnek)

| # | Kérdés | Opciók |
|---|---|---|
| D1 | Panel elhelyezése | A: `videoArea` és `PlaybackControlBar` közé (nem takar videót) [JAVASOLT]; B: overlay a videón belül (részben takarja) |
| D2 | Feedback mode belépési pont | A: harmadik toggle gomb az overlay-en [JAVASOLT]; B: külön "Visszajelzés" CTA a `labelingCTA` alá |
| D3 | "Correct position" korrekciós módszer | A: tap + drag mindkettő [JAVASOLT]; B: csak tap |
| D4 | Session limit UI | A: "N/3 elküldve" progress label [JAVASOLT]; B: nincs UI, csak `sessionComplete` állapot |

---

*Ez a dokumentum koncepcionális / tervezési terv. Implementáció kizárólag explicit jóváhagyás után indul.*
