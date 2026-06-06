/**
 * calib-hand-worker.js — Calibration Center hand detection worker (P0)
 *
 * Classic Worker (not module worker): MediaPipe's vision_bundle.mjs uses
 * importScripts() internally; module workers break this path.
 *
 * Self-hosted assets (never fetched from an external CDN):
 *   /static/mediapipe/vision_bundle.mjs
 *   /static/mediapipe/vision_wasm_internal.js / .wasm   (SIMD)
 *   /static/mediapipe/vision_wasm_nosimd_internal.js / .wasm  (iOS Safari)
 *   /static/mediapipe/hand_landmarker.task
 *
 * Privacy: only wrist {x,y,z} + handedness category/score are posted to the
 * main thread. No pixel data, no face data, nothing sent to the server.
 *
 * Protocol — main → worker:
 *   { type: 'init' }
 *   { type: 'frame', bitmap: ImageBitmap, timestamp: number }
 *   { type: 'stop' }
 *
 * Protocol — worker → main:
 *   { type: 'ready',    delegate: 'GPU'|'CPU' }
 *   { type: 'error',    code: string, message: string }
 *   { type: 'hands',    hands: HandData[] }
 *   { type: 'no_hands' }
 *
 * HandData = { side: 'Left'|'Right', confidence: number, wrist: {x,y,z} }
 * NOTE: 'side' is MediaPipe's raw label. With facingMode='user' (selfie),
 *       'Left' = user's RIGHT hand. The main thread applies the mirror flip.
 */

const MEDIAPIPE_BASE = '/static/mediapipe';
const MODEL_PATH     = '/static/mediapipe/hand_landmarker.task';

let _landmarker      = null;
let _modelReady      = false;
let _frameInFlight   = false;
let _frameCount      = 0;    // diagnostic only — logged for first frame

// ── Diagnostic helpers (DIAG prefix — remove after iPhone QA) ────────────────
function _D(msg) { console.log('[CALIB_WORKER] ' + msg); }
function _Derr(msg, err) {
    console.error('[CALIB_WORKER] ' + msg,
        err ? (err.name + ': ' + err.message) : '(no error object)');
}

async function initModel() {
    _D('initModel start — UA=' + (self.navigator && self.navigator.userAgent
        ? self.navigator.userAgent.substring(0, 80) : 'N/A'));
    _D('WebAssembly exists: ' + (typeof WebAssembly !== 'undefined'));
    _D('crossOriginIsolated: ' + (typeof crossOriginIsolated !== 'undefined'
        ? crossOriginIsolated : 'N/A'));

    let HandLandmarker, FilesetResolver;
    _D('dynamic import vision_bundle.mjs — start');
    try {
        ({ HandLandmarker, FilesetResolver } =
            await import('/static/mediapipe/vision_bundle.mjs'));
        _D('vision_bundle.mjs import OK — HandLandmarker=' + typeof HandLandmarker
            + ' FilesetResolver=' + typeof FilesetResolver);
    } catch (err) {
        _Derr('vision_bundle.mjs import FAILED', err);
        self.postMessage({ type: 'error', code: 'import_failed', message: err.message });
        return;
    }

    // Load WASM fileset once — reused across GPU→CPU fallback.
    // Calling forVisionTasks() inside the loop caused double WASM loading (+9 MB)
    // and left GPU fileset resources unreleased on iOS, leading to OOM crashes
    // after the CPU delegate sent 'ready'.
    let vision;
    _D('FilesetResolver.forVisionTasks start — base=' + MEDIAPIPE_BASE);
    try {
        vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_BASE);
        _D('FilesetResolver.forVisionTasks OK — vision=' + typeof vision);
    } catch (err) {
        _Derr('FilesetResolver.forVisionTasks FAILED', err);
        self.postMessage({ type: 'error', code: 'fileset_failed', message: err.message });
        return;
    }

    for (const delegate of ['GPU', 'CPU']) {
        _D('HandLandmarker.createFromOptions try — delegate=' + delegate);
        try {
            _landmarker = await HandLandmarker.createFromOptions(vision, {
                baseOptions: { modelAssetPath: MODEL_PATH, delegate },
                numHands:                   2,
                minHandDetectionConfidence: 0.60,
                minHandPresenceConfidence:  0.60,
                minTrackingConfidence:      0.50,
                runningMode:                'VIDEO',
            });
            _modelReady = true;
            _D('createFromOptions OK — delegate=' + delegate + ' → posting ready');
            self.postMessage({ type: 'ready', delegate });
            return;
        } catch (err) {
            _Derr('createFromOptions FAIL — delegate=' + delegate, err);
            if (delegate === 'CPU') {
                self.postMessage({ type: 'error', code: 'model_init_failed', message: err.message });
            }
        }
    }
    _D('initModel exhausted all delegates — no ready sent');
}

function processFrame(bitmap, timestamp) {
    if (!_landmarker || !_modelReady) { bitmap.close(); return; }
    _frameCount++;
    if (_frameCount === 1) {
        _D('first detectForVideo call — timestamp=' + timestamp.toFixed(1));
    }
    let result;
    try {
        result = _landmarker.detectForVideo(bitmap, timestamp);
    } catch (err) {
        if (_frameCount <= 5) {
            _Derr('detectForVideo THREW (frame #' + _frameCount + ')', err);
        }
        bitmap.close();
        return;
    }
    if (_frameCount === 1) {
        _D('first detectForVideo OK — hands=' + (result.handedness || []).length);
    }
    bitmap.close();

    const handedness = result.handedness || [];
    const landmarks  = result.landmarks  || [];

    if (!handedness.length) {
        self.postMessage({ type: 'no_hands' });
        return;
    }

    const hands = handedness.map(function (cats, i) {
        const h  = cats[0] || {};
        const lm = landmarks[i] || [];
        return {
            side:       h.categoryName || 'Unknown',
            confidence: h.score        || 0,
            wrist:      lm[0] ? { x: lm[0].x, y: lm[0].y, z: lm[0].z }
                               : { x: 0.5, y: 0.5, z: 0 },
        };
    });

    self.postMessage({ type: 'hands', hands });
}

self.onmessage = async function (event) {
    const msg = event.data;
    if (!msg || !msg.type) return;

    switch (msg.type) {
        case 'init':
            _D('received init message');
            await initModel();
            break;
        case 'frame':
            if (!msg.bitmap) break;
            if (_frameInFlight) { msg.bitmap.close(); break; }
            _frameInFlight = true;
            processFrame(msg.bitmap, msg.timestamp || performance.now());
            _frameInFlight = false;
            break;
        case 'stop':
            _D('received stop — _frameCount=' + _frameCount);
            _modelReady = false;
            if (_landmarker) {
                try { _landmarker.close(); } catch (_) {}
                _landmarker = null;
            }
            break;
    }
};
