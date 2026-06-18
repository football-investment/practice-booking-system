# AN-3B2E: Tracking Identity Layer — Koncepcionális Terv

**Státusz:** KONCEPCIONÁLIS TERV — nem implementált  
**Összeállítva:** 2026-06-18  
**Alapja:** AN-3B2D architekturális audit (single-entity constraint-ek azonosítása)  
**Scope:** Tervezési referencia a következő nagy architekturális fejlesztés előtt.  
**Implementáció:** NEM STARTED. Az AN-3B2D-3 QA és az aktuális egyjátékos dense tracking pipeline nem blokkolt.

---

## Háttér

Az AN-3B2D sorozat dense ball trajectory és dense skeleton pipeline-okat épített fel egyetlen játékos + egyetlen labda feltételezéssel. Az architekturális audit (2026-06-18) azonosított három hardcoded single-entity korlátot:

1. `UNIQUE (video_id, frame_ms)` a `juggling_ball_trajectories` táblán — egy labda per frame
2. `BallTrajectoryPointDTO` és `DensePoseFrame` tracking ID nélkül
3. iOS ViewModelek 1:1 coupling-ja a videóval

A végső célállapot: több sportmód, egyszerre több játékos, játékosonként külön skeleton, több tárgyobjektum (labda, háló, eszköz), több kamera, és 3D rekonstrukció. Ezt a rétegtervet kell a következő nagy fejlesztés előtt jóváhagyni.

---

## 1. DB Migration Irány

### 1.1 Új oszlopok — Tracking Identity

Minden dense tracking táblán (trajectory, skeleton, ground truth) egységes tracking identity séma:

```
object_id   TEXT    NOT NULL DEFAULT 'ball_0'     -- tracked object azonosítója
track_id    TEXT    NOT NULL DEFAULT 'track_0'    -- futásidejű tracking futam azonosítója
player_id   TEXT    NOT NULL DEFAULT 'player_0'   -- skeleton esetén
camera_id   TEXT    NOT NULL DEFAULT 'camera_0'   -- forrás kamera
```

### 1.2 Érintett táblák és UNIQUE constraint módosítások

#### `juggling_ball_trajectories`

Jelenlegi constraint:
```sql
UNIQUE (video_id, frame_ms)
-- Egy labda per frame.
```

Cél constraint:
```sql
UNIQUE (video_id, frame_ms, object_id, camera_id)
-- Több labda / több tárgy / több kamera per frame.
```

Migration lépés:
```sql
ALTER TABLE juggling_ball_trajectories
    ADD COLUMN object_id  TEXT NOT NULL DEFAULT 'ball_0',
    ADD COLUMN track_id   TEXT NOT NULL DEFAULT 'track_0',
    ADD COLUMN camera_id  TEXT NOT NULL DEFAULT 'camera_0';

DROP CONSTRAINT ux_ball_traj_video_frame;

CREATE UNIQUE INDEX ux_ball_traj_video_frame_object_camera
    ON juggling_ball_trajectories (video_id, frame_ms, object_id, camera_id);
```

Meglévő adatok: default `object_id='ball_0'`, `camera_id='camera_0'` — nem törölnek, backward-compatible.

#### `juggling_pose_snapshots` (event-level skeleton)

Jelenlegi constraint:
```sql
UNIQUE (contact_event_id)
-- Egy pose per annotációs esemény.
```

Cél constraint:
```sql
UNIQUE (contact_event_id, player_id)
-- Több játékos esetén több pose per esemény.
```

Migration lépés:
```sql
ALTER TABLE juggling_pose_snapshots
    ADD COLUMN player_id  TEXT NOT NULL DEFAULT 'player_0',
    ADD COLUMN camera_id  TEXT NOT NULL DEFAULT 'camera_0';

DROP CONSTRAINT ux_juggling_pose_snapshots_event;

CREATE UNIQUE INDEX ux_pose_snapshots_event_player
    ON juggling_pose_snapshots (contact_event_id, player_id);
```

#### Tervezett új tábla: `juggling_dense_skeletons`

Ha a dense skeleton backend-oldalra kerül (server-side MediaPipe), új tábla:

```sql
CREATE TABLE juggling_dense_skeletons (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id     UUID NOT NULL REFERENCES juggling_videos(id) ON DELETE CASCADE,
    frame_ms     INTEGER NOT NULL,
    player_id    TEXT NOT NULL DEFAULT 'player_0',
    track_id     TEXT NOT NULL DEFAULT 'track_0',
    camera_id    TEXT NOT NULL DEFAULT 'camera_0',
    keypoints    JSONB NOT NULL,
    confidence   FLOAT,
    model_version TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (video_id, frame_ms, player_id, camera_id)
);
```

### 1.3 Default értékek és backward-compatibility

| Entitás | Default ID | Jelentés |
|---|---|---|
| Labda | `ball_0` | Az első (és jelenlegi egyetlen) labda |
| Háló / eszköz | `net_0`, `tool_0` | Fix pályaobjektumok |
| Játékos | `player_0` | Az első (és jelenlegi egyetlen) játékos |
| Kamera | `camera_0` | Az egyetlen kamera |
| Tracking futam | `track_0` | Az első tracking run |

Az összes meglévő sor implicit `*_0` default értéket kap migration után. Az existing API kliensei továbbra is egyetlen labdát / egyetlen játékost látnak, mert `WHERE object_id = 'ball_0'` szűrés adódik hozzá az új endpointok mellé, vagy a régi endpointon default szűrés marad.

---

## 2. Multi-Object Tracking

### 2.1 Tracked objectek katalógusa

Sportáganként eltérő objektumkészlet:

| Objektum típus | ID prefix | Megjegyzés |
|---|---|---|
| Labda | `ball_0`, `ball_1`, ... | Több labda esetén sorszámozva |
| Játékos | `player_0`, `player_1`, ... | Skeleton-nel rendelkező entitás |
| Háló | `net_0` | Fix, statikus; pozíció csak egyszer kalibrálandó |
| Eszköz | `tool_0`, `tool_1`, ... | Ütő, kapus kesztyű, stb. |
| Kamera | `camera_0`, `camera_1`, ... | Fizikai vagy virtuális nézőpont |

### 2.2 Tracking identity szétválasztás

Minden `JugglingBallTrajectory` sor egy adott `object_id` adott `frame_ms`-kori pozícióját írja le. Több labda esetén:

```
video_id=V, frame_ms=1000, object_id='ball_0', ball_x=0.42, ball_y=0.71   -- 1. labda
video_id=V, frame_ms=1000, object_id='ball_1', ball_x=0.19, ball_y=0.33   -- 2. labda
video_id=V, frame_ms=1000, object_id='net_0',  ball_x=0.50, ball_y=0.45   -- háló centroid
```

### 2.3 Fix objektumok (háló, eszköz)

Fix pályaobjektumok pozíciója frame-enként nem változik; elég egyszer kalibrálni (vagy homográfiával meghatározni). Tárolási lehetőség:

- **Option A:** `juggling_ball_trajectories`-ban is eltárolni, `tracking_state='static'` értékkel — egyszerű, konzisztens táblahasználat.
- **Option B:** Külön `juggling_pitch_objects` tábla — kamera-kalibráció, homográfia, és 3D koordináta is ide kerül.

Ajánlás: **Option B** — a fix objektumok más életciklusa (nem frame-szintű update) és más adatstruktúrája (szélső pontok, nem centroid) indokolja a szétválasztást.

---

## 3. Multi-Player Skeleton

### 3.1 Jelenlegi iOS Vision korlát

`VNDetectHumanBodyPoseRequest` (AN-3B2D-2 implementáció) **egy személyt** detektál frame-enként. A request elvégez full-frame analízist és a legdominánebb személyt adja vissza.

Ennek nincs konfigurációs megoldása: a Vision framework nem biztosít `maximumDetectionCount` paramétert body pose-ra (szemben az arc detekcióval).

### 3.2 VNDetectHumanBodyPosesRequest (iOS 17+)

Az iOS 17-ben bevezetett `VNDetectHumanBodyPosesRequest` (többes szám) támogatja a multi-person detekcióra:

```swift
let request = VNDetectHumanBodyPosesRequest()
request.maximumBodyCount = 4   // max 4 személy per frame

let handler = VNImageRequestHandler(cmSampleBuffer: sampleBuffer)
try handler.perform([request])

let observations: [VNHumanBodyPoseObservation] = request.results ?? []
// observations.count >= 1: minden elem egy külön játékos
```

Előnyök: on-device, nincs hálózati overhead  
Hátrányok: iOS 17.0 minimum, deployment target emelés szükséges (jelenleg: iOS 15.0)

### 3.3 Server-side MediaPipe alternatíva

Ha iOS 17 deployment target nem elfogadható (vagy pontosabb multi-person tracking kell):

```
iOS → frame PNG/JPEG (kulcsframe-ek, pl. 5 FPS) → Backend task queue
Backend → MediaPipe Pose Landmarker (multi-person mód) → player_0..N keypoints
Backend → juggling_dense_skeletons tábla → iOS lekérheti REST/WebSocket
```

Előnyök: nincs iOS verzió constraint, jobb pontosság, könnyebben frissíthető modell  
Hátrányok: hálózati latencia, szerver oldali számítási igény, frame upload pipeline kell

### 3.4 Több skeleton ugyanazon videón — tárolási séma

A `DensePoseCache` jelenlegi struktúrája: `videoId → [DensePoseFrame]`

Multi-player kiterjesztés: `(videoId, playerId) → [DensePoseFrame]`

iOS VM szintjén:
```swift
// Jelenlegi:
@StateObject private var denseSkeletonVM: DenseSkeletonViewModel

// Multi-player jövő:
@State private var skeletonVMs: [String: DenseSkeletonViewModel] = [:]
// ["player_0": vm0, "player_1": vm1]
```

---

## 4. Multi-Camera / 3D Előkészítés

### 4.1 Koordináta-rendszerek

| Típus | Mértékegység | Eredet | Jelenlegi állapot |
|---|---|---|---|
| Screen-normalized | [0,1] | top-left | **Implementált** — ball_x/y, keypoints x/y |
| Raw pixel | px | top-left | Nincs tárolva (csak `image_width_px` / `image_height_px` tárolódik referenciaként) |
| World | méter | pályaközép | `world_x_m`, `world_y_m` — NULL, tervezett (AN-3B2B-2) |
| 3D world | méter | 3D scene | Nem implementált |

### 4.2 Kamera intrinsics és extrinsics

Jövőbeli `juggling_cameras` tábla:

```sql
CREATE TABLE juggling_cameras (
    id              UUID PRIMARY KEY,
    session_id      UUID,           -- melyik felvételi session
    camera_id       TEXT NOT NULL,  -- 'camera_0', 'camera_1', ...
    model           TEXT,           -- 'iphone_15_pro_main', 'gopro_hero12', ...

    -- Intrinsics (kamera-belső paraméterek)
    focal_length_px FLOAT,
    cx_px           FLOAT,          -- principal point x
    cy_px           FLOAT,          -- principal point y
    distortion_k1   FLOAT,          -- radial distortion coefficient
    distortion_k2   FLOAT,

    -- Extrinsics (kamera pozíció a world coordinate-ban)
    rotation_matrix JSONB,          -- 3x3 R
    translation_vec JSONB,          -- 3x1 t

    -- Kalibrációs metaadatok
    calibrated_at   TIMESTAMPTZ,
    calibration_method TEXT         -- 'checkerboard', 'homography', 'manual'
);
```

### 4.3 Raw pixel koordináta tárolás

A 3D triangulációhoz a screen-normalized koordináta nem elégséges (veszít precizitást). Szükséges:

```sql
ALTER TABLE juggling_ball_trajectories
    ADD COLUMN ball_x_px FLOAT,    -- raw pixel x (kamera_id-hoz tartozó)
    ADD COLUMN ball_y_px FLOAT;    -- raw pixel y
```

A normalized x/y megtartandó — az iOS overlay és a backend is ezt használja. A px koordináta 3D pipeline input lesz.

### 4.4 Triangulációs pipeline (vázlat)

```
Camera 0: (u0, v0) → undistort → normalized ray → world ray
Camera 1: (u1, v1) → undistort → normalized ray → world ray
Triangulált 3D pont: DLT (Direct Linear Transform) vagy bundle adjustment
→ (X, Y, Z) world-ban → world_x_m, world_y_m, world_z_m
```

Ez a pipeline teljesen szerver-oldali — iOS-t nem érinti, csak az adatbázis olvasó API-t.

---

## 5. Frontend Overlay Bővíthetősége

### 5.1 Jelenlegi overlay view API-ok

Mindkét overlay view **stateless, single-entity renderer**:

```swift
struct ContinuousSkeletonOverlayView: View {
    let frame: DensePoseFrame?
    var showSyntheticFeet: Bool = true
}

struct BallTrajectoryOverlayView: View {
    let currentPoint: BallTrajectoryPointDTO?
    let trail: [BallTrajectoryPointDTO]
    let trackingLost: Bool
}
```

Ezek a view-k **változatlanul használhatók** multi-player kontextusban.

### 5.2 Multi-skeleton renderelés

```swift
// Multi-player — az overlay view maga nem változik:
ForEach(Array(skeletonVMs), id: \.key) { playerId, vm in
    ContinuousSkeletonOverlayView(
        frame: vm.interpolatedFrame(atMs: playback.currentTimestampMs),
        showSyntheticFeet: true
    )
    .frame(width: renderSize.width, height: renderSize.height)
}
```

### 5.3 Multi-object tracking renderelés

```swift
// Több labda / tárgy:
ForEach(ballVMs, id: \.objectId) { vm in
    BallTrajectoryOverlayView(
        currentPoint: vm.point(atMs: playback.currentTimestampMs),
        trail: vm.trail(beforeMs: playback.currentTimestampMs),
        trackingLost: vm.point(atMs: playback.currentTimestampMs) == nil
    )
    .frame(width: renderSize.width, height: renderSize.height)
}
```

### 5.4 Track-specifikus szín és label

A jelenlegi `BallTrajectoryOverlayView` `markerColor(for:)` statikus helper a `trackingState`-re támaszkodik. Multi-track esetén egy `trackColorPalette: [String: Color]` dictionary adható hozzá:

```swift
// Tervezett bővítés a BallTrajectoryOverlayView-n:
let trackColor: Color    // hívó oldal adja át, VM-ből jön

// Hívó oldal:
let palette: [String: Color] = [
    "ball_0":   .yellow,
    "ball_1":   .cyan,
    "net_0":    .white.opacity(0.5),
    "player_0": .green,
    "player_1": .orange,
]
```

Track label overlay (objektum neve + track confidence):

```swift
struct TrackLabelOverlayView: View {
    let objectId: String
    let position: CGPoint           // normalizált koordináta
    let confidence: Double?
    let color: Color
}
```

---

## 6. Sportmód Kompatibilitás

### 6.1 Jelenlegi namespace szeparáció

Minden jelenlegi tábla `juggling_` prefixű. A backend endpoint-ok `/me/juggling/` alatt vannak. Ez de-facto namespace, amely kiterjeszthető:

```
/me/juggling/      → jelenlegi
/me/footvolley/    → jövőbeli
/me/foottennis/    → jövőbeli
```

### 6.2 Sportáganként eltérő detection modell és objektumkészlet

| Sportág | Labdaobjektum | Skeleton/játékos | Fix objektum | Speciális detekció |
|---|---|---|---|---|
| Juggling | `ball_0` (1 labda) | `player_0` (1 játékos) | — | labdaérintés per frame |
| GAN Footvolley | `ball_0` (1 labda) | `player_0`, `player_1` | `net_0` | háló clearance, labda magasság |
| GAN Foottennis | `ball_0` (1 labda) | `player_0`, `player_1` | `net_0` | labda bounce, ütem |

### 6.3 Modell registry szétválasztás

Jövőbeli `sport_detection_models` tábla:

```sql
CREATE TABLE sport_detection_models (
    id            UUID PRIMARY KEY,
    sport_mode    TEXT NOT NULL,       -- 'juggling', 'footvolley', 'foottennis'
    object_type   TEXT NOT NULL,       -- 'ball', 'player', 'net'
    model_name    TEXT NOT NULL,       -- 'mobilenet_ssd_v2', 'mediapipe_pose', ...
    model_version TEXT NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT FALSE,
    onnx_path     TEXT
);
```

Ez teszi lehetővé, hogy sportáganként eltérő modellt aktiváljon a backend, a tracking pipeline módosítása nélkül.

---

## 7. Migrációs Stratégia

### 7.1 Alapelvek

1. **Meglévő adatok nem törlődnek** — minden sor kap default tracking identity oszlopokat
2. **Endpointok backward-compatible maradnak** — meglévő kliens API nem változik, csak opcionális paraméterek bővülnek
3. **Feature flag mögé kerül minden multi-entity feature** — `MULTI_PLAYER_ENABLED`, `MULTI_CAMERA_ENABLED`
4. **Additive migration** — csak `ADD COLUMN`, `ADD INDEX`, `DROP CONSTRAINT` + `CREATE UNIQUE INDEX`; soha `DROP COLUMN` a migration során

### 7.2 Lépésrend

```
Migration M1: ADD COLUMN object_id/track_id/player_id/camera_id defaultokkal
Migration M2: DROP régi UNIQUE constraint-ek
Migration M3: CREATE új compound UNIQUE index-ek
Migration M4: Backfill ellenőrzés (minden régi sor *_0 defaultot kapott)
```

Az M1–M4 futtatható production alatt (nem blokkoló DDL PostgreSQL-ben).

### 7.3 API backward-compatibility

Meglévő endpoint (`GET /me/juggling/videos/{id}/ball-trajectory`) viselkedése a migration után:

- Default query: visszaad minden `object_id='ball_0'` és `camera_id='camera_0'` pontot
- Új opcionális query paraméter: `?object_id=ball_1` — meglévő kliens nem küldi, tehát `ball_0` default marad
- Response schema: `object_id` opcionális mezőként adódik hozzá — meglévő kliens figyelmen kívül hagyja

### 7.4 iOS backward-compatibility

`BallTrajectoryPointDTO` bővítése:

```swift
struct BallTrajectoryPointDTO: Decodable, Equatable {
    let frameMs: Int
    let ballX: Double?
    let ballY: Double?
    let confidence: Double?
    let isManual: Bool
    let trackingState: String
    // Új, opcionális mezők — backward-compatible decode:
    let objectId: String?       // nil-t dekódol régi API válaszon
    let trackId: String?
    let playerId: String?
    let cameraId: String?
}
```

Meglévő `BallTrajectoryViewModel` kód nil-t kap ezekre régi API-val → működőképes marad.

---

## Összefoglalás

| Réteg | Változás típusa | Meglévő adatok | Backward-compat |
|---|---|---|---|
| DB UNIQUE constraint | Additive migration | Default *_0 értékek | Igen |
| API schema | Opcionális új mező | — | Igen |
| iOS DTO | Opcionális new field | nil decode | Igen |
| iOS ViewModel | Dictionary[trackId] | Párhuzamos, nem felváltja | Igen |
| iOS Overlay View | Nem változik | — | Igen |
| Vision API | iOS 17+ vagy MediaPipe | Új pipeline | Deployment target emelés vagy server-side |
| Sport namespace | Új prefix/tábla | Nem érinti juggling_ | Igen |

**Implementációs blokkolta:** Az AN-3B2D-3 QA és az aktuális egyjátékos dense tracking pipeline nem blokkolt. Ez a terv a **következő nagy architekturális fejlesztés jóváhagyása előtt kötelező input**.
