/**
 * SessionGenWizard — 5-step session generation wizard for the tournament edit page.
 *
 * Steps:
 *   1. init      — Preset guard check + player count vs minimum
 *   2. schedule  — Match duration, break, parallel fields, rounds
 *   3. confirm   — Summary + mandatory confirmed checkbox if ≥128 players
 *   4. progress  — Async polling progress bar (large tournaments only)
 *   5. result    — Success/failure + session preview
 *
 * Usage (wired from tournament_edit.html):
 *   openSessionGenWizard({
 *     tournId:          <int>,
 *     enrolledCount:    <int>,
 *     presetMinPlayers: <int|null>,
 *     format:           <string>,   // e.g. "INDIVIDUAL_RANKING"
 *     schedule: {
 *       match_duration_minutes: <int|null>,
 *       break_duration_minutes: <int|null>,
 *       parallel_fields:        <int>,
 *     }
 *   });
 */

const SessionGenWizard = (() => {
  // ── State ───────────────────────────────────────────────────────────────────
  let _ctx = {};          // wizard context (tournId, counts, schedule defaults)
  let _step = 0;          // current step index
  let _params = {};       // collected generation parameters
  let _pollTimer = null;  // setInterval handle for progress polling
  let _pollCount = 0;     // number of polls fired
  const MAX_POLLS = 80;   // 80 × 1.5s = 120s timeout

  const STEPS = ['init', 'schedule', 'confirm', 'progress', 'result'];

  // ── Open / Close ────────────────────────────────────────────────────────────
  function open(ctx) {
    _ctx    = ctx;
    _step   = 0;
    _params = {};
    _clearPoll();
    _render();
    document.getElementById('sgw-overlay').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function close() {
    _clearPoll();
    document.getElementById('sgw-overlay').style.display = 'none';
    document.body.style.overflow = '';
  }

  // ── Step navigation ─────────────────────────────────────────────────────────
  function _goto(stepName) {
    _step = STEPS.indexOf(stepName);
    _render();
  }

  function _render() {
    const stepName = STEPS[_step];
    const body = document.getElementById('sgw-body');
    const nav  = document.getElementById('sgw-nav');
    const title = document.getElementById('sgw-title');

    title.textContent = _stepTitle(stepName);
    body.innerHTML = _buildBody(stepName);
    nav.innerHTML  = _buildNav(stepName);

    _updateStepIndicator(stepName);
  }

  function _stepTitle(step) {
    return {
      init:     '⚡ Generate Sessions — Step 1: Eligibility Check',
      schedule: '⚡ Generate Sessions — Step 2: Schedule Parameters',
      confirm:  '⚡ Generate Sessions — Step 3: Confirm',
      progress: '⚡ Generate Sessions — Step 4: Generating…',
      result:   '⚡ Generate Sessions — Step 5: Complete',
    }[step];
  }

  function _updateStepIndicator(active) {
    STEPS.forEach((s, i) => {
      const el = document.getElementById(`sgw-step-${s}`);
      if (!el) return;
      el.className = 'sgw-step-dot' +
        (s === active ? ' sgw-step-active' : '') +
        (['progress', 'result'].includes(s) && STEPS.indexOf(active) > i ? ' sgw-step-done' : '');
    });
  }

  // ── Body builders ────────────────────────────────────────────────────────────
  function _buildBody(step) {
    switch (step) {
      case 'init':     return _bodyInit();
      case 'schedule': return _bodySchedule();
      case 'confirm':  return _bodyConfirm();
      case 'progress': return _bodyProgress();
      case 'result':   return _bodyResult();
      default:         return '';
    }
  }

  function _bodyInit() {
    const enrolled   = _ctx.enrolledCount;
    const minPlayers = _ctx.presetMinPlayers;
    const blocked    = minPlayers && enrolled < minPlayers;
    const multiCampus = enrolled >= 128;

    let html = `<div class="sgw-info-grid">
      <div class="sgw-info-item"><span class="sgw-info-label">Tournament</span><strong>${_esc(_ctx.tournName)}</strong></div>
      <div class="sgw-info-item"><span class="sgw-info-label">Enrolled players</span><strong>${enrolled}</strong></div>
      <div class="sgw-info-item"><span class="sgw-info-label">Format</span><strong>${_esc(_ctx.format || '—')}</strong></div>`;
    if (minPlayers) {
      html += `<div class="sgw-info-item"><span class="sgw-info-label">Preset minimum</span><strong>${minPlayers}</strong></div>`;
    }
    html += `</div>`;

    if (blocked) {
      html += `<div class="sgw-warn">
        ⚠️ <strong>Not enough players.</strong>
        Preset requires <strong>${minPlayers}</strong> players,
        only <strong>${enrolled}</strong> enrolled.<br>
        Enroll more players before generating sessions.
      </div>`;
    } else {
      html += `<div class="sgw-ok">✅ Player count check passed (${enrolled} enrolled).</div>`;
    }

    if (multiCampus && !blocked) {
      html += `<div class="sgw-info-banner">
        ℹ️ <strong>Multi-campus mode available.</strong>
        ${enrolled} players triggers background generation.
        A task ID will be returned and progress will be polled automatically.
      </div>`;
    }

    // Store blocked state for nav
    _params._blocked = blocked;
    return html;
  }

  function _bodySchedule() {
    const s = _ctx.schedule || {};
    const matchDefault  = s.match_duration_minutes || 90;
    const breakDefault  = s.break_duration_minutes || 15;
    const parallelDef   = s.parallel_fields || 1;
    const isIR          = (_ctx.format || '').toUpperCase().includes('INDIVIDUAL_RANKING');

    const matchOpts = [60, 75, 90, 120];
    const breakOpts = [0, 10, 15, 20];

    const matchRadios = matchOpts.map(v =>
      `<label class="sgw-radio-label">
         <input type="radio" name="sgw-match" value="${v}" ${Math.abs(v - matchDefault) === Math.min(...matchOpts.map(o => Math.abs(o - matchDefault))) ? 'checked' : ''}>
         ${v} min
       </label>`
    ).join('');

    const breakRadios = breakOpts.map(v =>
      `<label class="sgw-radio-label">
         <input type="radio" name="sgw-break" value="${v}" ${v === breakDefault ? 'checked' : ''}>
         ${v === 0 ? 'No break' : v + ' min'}
       </label>`
    ).join('');

    let html = `
    <div class="sgw-form-row">
      <label class="sgw-form-label">Match Duration</label>
      <div class="sgw-radio-group">${matchRadios}</div>
    </div>
    <div class="sgw-form-row">
      <label class="sgw-form-label">Break Between Matches</label>
      <div class="sgw-radio-group">${breakRadios}</div>
    </div>
    <div class="sgw-form-row">
      <label class="sgw-form-label">Parallel Fields / Courts</label>
      <div style="display:flex;align-items:center;gap:0.75rem;">
        <input type="range" id="sgw-parallel" min="1" max="8" value="${parallelDef}" style="flex:1;"
               oninput="document.getElementById('sgw-parallel-val').textContent=this.value">
        <span id="sgw-parallel-val" style="font-weight:700;min-width:1.5rem;">${parallelDef}</span>
      </div>
    </div>`;

    if (isIR) {
      html += `
    <div class="sgw-form-row">
      <label class="sgw-form-label">Number of Rounds <small style="color:#a0aec0;">(INDIVIDUAL_RANKING only)</small></label>
      <div style="display:flex;align-items:center;gap:0.75rem;">
        <input type="range" id="sgw-rounds" min="1" max="10" value="1" style="flex:1;"
               oninput="document.getElementById('sgw-rounds-val').textContent=this.value">
        <span id="sgw-rounds-val" style="font-weight:700;min-width:1.5rem;">1</span>
      </div>
    </div>`;
    }

    return html;
  }

  function _bodyConfirm() {
    const matchVal    = _readRadio('sgw-match') || 90;
    const breakVal    = _readRadio('sgw-break') ?? 15;
    const parallelVal = parseInt(document.getElementById('sgw-parallel')?.value || '1');
    const roundsEl    = document.getElementById('sgw-rounds');
    const roundsVal   = roundsEl ? parseInt(roundsEl.value) : 1;

    // Store for actual submit
    _params.session_duration_minutes = matchVal;
    _params.break_minutes            = breakVal;
    _params.parallel_fields          = parallelVal;
    _params.number_of_rounds         = roundsVal;

    const multiCampus = _ctx.enrolledCount >= 128;

    let html = `
    <table class="sgw-summary-table">
      <tr><td>Tournament</td><td><strong>${_esc(_ctx.tournName)}</strong></td></tr>
      <tr><td>Players</td><td><strong>${_ctx.enrolledCount}</strong></td></tr>
      <tr><td>Match Duration</td><td><strong>${matchVal} min</strong></td></tr>
      <tr><td>Break Between</td><td><strong>${breakVal === 0 ? 'No break' : breakVal + ' min'}</strong></td></tr>
      <tr><td>Parallel Fields</td><td><strong>${parallelVal}</strong></td></tr>
      <tr><td>Rounds</td><td><strong>${roundsVal}</strong></td></tr>
      <tr><td>Generation mode</td><td><strong>${multiCampus ? '⏳ Async (background)' : '⚡ Synchronous'}</strong></td></tr>
    </table>`;

    if (multiCampus) {
      html += `
    <div class="sgw-warn" style="margin-top:1rem;">
      ⚠️ <strong>Large tournament (${_ctx.enrolledCount} players)</strong> — generation runs in background.
      You must confirm to proceed.
    </div>
    <label style="display:flex;align-items:center;gap:0.6rem;margin-top:0.75rem;cursor:pointer;">
      <input type="checkbox" id="sgw-confirmed" style="width:1.1rem;height:1.1rem;">
      <span>I confirm this will generate sessions for ${_ctx.enrolledCount} players</span>
    </label>`;
      _params._requireConfirm = true;
    } else {
      _params._requireConfirm = false;
    }

    return html;
  }

  function _bodyProgress() {
    return `
    <div style="text-align:center;padding:1rem 0;">
      <div style="font-size:2.5rem;margin-bottom:1rem;">⚡</div>
      <p style="font-weight:600;color:#2d3748;margin-bottom:1rem;">Generating sessions…</p>
      <div class="sgw-progress-bar">
        <div class="sgw-progress-fill" id="sgw-progress-fill"></div>
      </div>
      <p id="sgw-progress-msg" style="font-size:0.85rem;color:#718096;margin-top:0.75rem;">Starting…</p>
    </div>`;
  }

  function _bodyResult() {
    const r = _params._result || {};
    if (r.error) {
      return `<div class="sgw-warn">❌ <strong>Generation failed:</strong><br>${_esc(r.error)}</div>`;
    }
    let html = `
    <div class="sgw-ok">✅ <strong>${r.count} sessions created successfully.</strong></div>`;
    if (r.sessions && r.sessions.length) {
      html += `<p style="font-weight:600;color:#4a5568;margin:1rem 0 0.5rem;">First sessions:</p>
      <table class="sgw-summary-table">
        <thead><tr><th>When</th><th>Title</th><th>Type</th></tr></thead>
        <tbody>`;
      r.sessions.slice(0, 5).forEach(s => {
        const dt = s.date_start ? s.date_start.slice(0, 16).replace('T', ' ') : '—';
        html += `<tr><td>${dt}</td><td>${_esc(s.title || '')}</td><td>${_esc(s.game_type || '')}</td></tr>`;
      });
      html += `</tbody></table>`;
    }
    html += `<div style="margin-top:1rem;">
      <a href="/admin/sessions?semester_id=${_ctx.tournId}" class="btn btn-secondary" style="text-decoration:none;">
        📋 View all sessions →
      </a>
    </div>`;
    return html;
  }

  // ── Nav builders ─────────────────────────────────────────────────────────────
  function _buildNav(step) {
    const blocked = _params._blocked;
    switch (step) {
      case 'init':
        return `
          <button class="btn btn-secondary" onclick="SessionGenWizard.close()">Cancel</button>
          <button class="btn btn-primary" onclick="SessionGenWizard._nextFromInit()"
            ${blocked ? 'disabled title="Minimum player count not met"' : ''}>
            Next →
          </button>`;

      case 'schedule':
        return `
          <button class="btn btn-secondary" onclick="SessionGenWizard._goto('init')">← Back</button>
          <button class="btn btn-primary" onclick="SessionGenWizard._goto('confirm')">Next →</button>`;

      case 'confirm':
        return `
          <button class="btn btn-secondary" onclick="SessionGenWizard._goto('schedule')">← Back</button>
          <button class="btn btn-primary" id="sgw-btn-generate" onclick="SessionGenWizard._generate()">
            ⚡ Generate Sessions
          </button>`;

      case 'progress':
        return `<button class="btn btn-secondary" disabled>Please wait…</button>`;

      case 'result':
        const r = _params._result || {};
        if (r.error) {
          return `
            <button class="btn btn-secondary" onclick="SessionGenWizard._goto('schedule')">← Try Again</button>
            <button class="btn btn-secondary" onclick="SessionGenWizard.close()">Close</button>`;
        }
        return `<button class="btn btn-primary" onclick="SessionGenWizard.close();location.reload()">✅ Done — Reload</button>`;

      default: return '';
    }
  }

  // ── Actions ──────────────────────────────────────────────────────────────────
  function _nextFromInit() {
    _goto('schedule');
  }

  async function _generate() {
    // Confirm checkbox guard
    if (_params._requireConfirm) {
      const cb = document.getElementById('sgw-confirmed');
      if (!cb || !cb.checked) {
        toast('Please check the confirmation checkbox for large tournaments.', 'warning');
        return;
      }
    }

    const body = {
      parallel_fields:          _params.parallel_fields,
      session_duration_minutes: _params.session_duration_minutes,
      break_minutes:            _params.break_minutes,
      number_of_rounds:         _params.number_of_rounds,
    };

    // Show progress step immediately
    _goto('progress');

    try {
      const data = await AdminAPI.post(
        `/api/v1/tournaments/${_ctx.tournId}/generate-sessions`,
        body
      );

      if (data.async) {
        // Large tournament — poll for completion
        _startPolling(data.task_id);
      } else {
        // Small tournament — immediate result
        _params._result = {
          count:    data.sessions_generated_count || 0,
          sessions: data.sessions || [],
        };
        _goto('result');
      }
    } catch (err) {
      _params._result = { error: err.message };
      _goto('result');
    }
  }

  // ── Polling ──────────────────────────────────────────────────────────────────
  function _startPolling(taskId) {
    _pollCount = 0;

    _pollTimer = setInterval(async () => {
      _pollCount++;

      // Timeout guard
      if (_pollCount > MAX_POLLS) {
        _clearPoll();
        _params._result = { error: 'Generation timed out after 120 seconds. Check server logs.' };
        _goto('result');
        return;
      }

      // Animate progress fill (0 → 95% while pending/running)
      const pct = Math.min(95, (_pollCount / MAX_POLLS) * 100);
      const fill = document.getElementById('sgw-progress-fill');
      if (fill) fill.style.width = pct + '%';

      try {
        const status = await AdminAPI.get(
          `/api/v1/tournaments/${_ctx.tournId}/generation-status/${taskId}`
        );

        const msg = document.getElementById('sgw-progress-msg');
        if (msg) msg.textContent = _statusMessage(status.status, status.sessions_count);

        if (status.status === 'done') {
          _clearPoll();
          if (fill) fill.style.width = '100%';
          _params._result = {
            count:    status.sessions_count || 0,
            sessions: [],  // status endpoint doesn't return session list, will show count only
          };
          // Fetch first 5 sessions for preview
          try {
            const sessions = await AdminAPI.get(`/api/v1/tournaments/${_ctx.tournId}/sessions`);
            _params._result.sessions = Array.isArray(sessions) ? sessions.slice(0, 5) : [];
          } catch (_) {}
          _goto('result');

        } else if (status.status === 'error') {
          _clearPoll();
          _params._result = { error: status.message || 'Generation failed.' };
          _goto('result');
        }

      } catch (err) {
        // Network error — keep polling unless timed out
        const msg = document.getElementById('sgw-progress-msg');
        if (msg) msg.textContent = `Network error: ${err.message}. Retrying…`;
      }

    }, 1500);
  }

  function _statusMessage(status, count) {
    const map = {
      pending:  'Queued — waiting for worker…',
      running:  'Generation in progress…',
      retrying: 'Retrying after transient error…',
      done:     `Complete — ${count || 0} sessions created.`,
      error:    'Generation failed.',
    };
    return map[status] || status;
  }

  function _clearPoll() {
    if (_pollTimer) {
      clearInterval(_pollTimer);
      _pollTimer = null;
    }
    _pollCount = 0;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────────
  function _readRadio(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? parseInt(el.value) : null;
  }

  function _esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── Public API ────────────────────────────────────────────────────────────────
  return { open, close, _goto, _nextFromInit, _generate };
})();

// Alias so tournament_edit.html can call openSessionGenWizard(ctx)
function openSessionGenWizard(ctx) {
  SessionGenWizard.open(ctx);
}
