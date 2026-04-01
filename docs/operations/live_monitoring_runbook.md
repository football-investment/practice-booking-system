# Live Monitoring — Operator Runbook

**Audience:** Tournament admins, sport directors, master instructors
**Endpoint:** `/admin/tournaments/{id}/live`
**Updated:** 2026-03-24

---

## 1. What you are looking at

| Dashboard element | What it tells you |
|---|---|
| **Progress bar** | % of sessions completed across the entire tournament |
| **KPI pills** | Completed / Remaining / Total / Estimated finish time |
| **Pitch activity table** | Per-pitch: which campus, how many done, last activity time |
| **Live feed** | Last 20 completed sessions (campus / pitch / round / session ID) |
| **WS dot (top-left)** | 🟢 = connected; 🔴 = reconnecting (last known data still shown) |
| **⚡ events/min** | Redis events received in the last 60 s (UI activity, not result count) |
| **↓ drop:** | Events dropped by throttle (normal when > 5 results/sec arrive simultaneously) |
| **Alert panel** | Idle pitch warnings + throttle-stats summaries |

---

## 2. Normal operation

1. Open the dashboard **after** the tournament has started and results are being submitted.
2. The progress bar advances with every result submitted by any instructor.
3. The **Est. finish** time updates automatically as the completion rate is measured.
4. Each pitch row shows: green dot (active < 5 min), yellow (pending), **red (idle > 5 min)**.

**You can make decisions based on this dashboard alone:**
- Is tournament pace on track? → Compare Est. finish vs. planned end time.
- Which pitch is falling behind? → Look for red dots in the pitch table.
- Which campus has the most activity? → Check campus label (C1, C2…) next to pitch numbers.
- Is data fresh? → Look at "last: HH:MM:SS" next to the progress bar heading.

---

## 3. Alert types and what to do

### 3a. `pitch_idle_alert` (orange banner)

> ⚠️ **Pitch #5 (Campus 2) idle for 7m 32s — no result submitted. Check instructor assignment.**

**Cause:** No result was submitted from that pitch for more than 5 minutes.

**Action checklist:**
1. Radio the instructor assigned to Pitch #5 / Campus 2.
2. If unreachable: send a sport director to the physical location.
3. Common causes:
   - Instructor app crashed or phone died → give them a spare device.
   - Match is still ongoing (long session) → verify the schedule.
   - Instructor was never assigned → assign via `/admin/pitches/{id}/assign-instructor`.
4. Once a result is submitted the red dot turns green and the alert auto-dismisses in 5 minutes.

**Threshold:** 5 minutes (300 s). Adjust `PITCH_IDLE_ALERT_S` in `tournament_live.py` if needed.

---

### 3b. `throttle_stats` (blue banner — shown only when drop rate > 50%)

> 📊 **Throttle stats: 1 422 delivered, 98 578 dropped (98.6% drop rate). High drop rate means Redis is producing faster than WS can deliver — clients see latest state only, no count data lost.**

**This is expected behaviour during batch imports** (e.g. 1 000 results imported via CSV in < 10 seconds).

**What "dropped" means:** The dashboard always shows the *latest* aggregate count. Dropped events are intermediate states that were never rendered, not lost results. The final `completed_count` / `total_count` values are always correct.

**Action:** No action required unless:
- The drop rate stays > 50% for longer than 10 minutes *after* batch import finishes.
- In that case, check if the result-submission endpoint is in a loop or if a script is running unintentionally.

---

### 3c. "No new events for Xs — data may be stale" (yellow banner)

**Cause:** No Redis message received for 60 s, but WS is still connected.

**Likely causes:**
- All sessions for the tournament are completed (no more events).
- Result submission is paused (lunch break, incident, etc.).
- Redis pub/sub channel subscription silently dropped (rare).

**Action:**
1. Verify via `/admin/tournaments/{id}/edit` that uncompleted sessions still exist.
2. If sessions remain open, check that instructors are actively submitting.
3. Click **Reload** on the banner to re-fetch counts from the database (bypasses Redis).

---

### 3d. "Live data unavailable — Redis connection failed" (red banner)

**Cause:** WebSocket could not connect to the server after 30 s, or Redis is down.

**Action:**
1. Reload the page — it will retry the WebSocket connection with exponential back-off.
2. If the banner reappears: check with engineering that `redis-server` is running.
3. Result submission still works and is counted — you will just not see live updates.
4. Use `/admin/tournaments/{id}/edit` → Section 7 for the current state (static page).

---

## 4. When to escalate

| Symptom | Escalate to |
|---|---|
| > 3 pitches simultaneously idle for > 10 min | Sport Director + on-site coordinator |
| WS disconnected and cannot reconnect for > 5 min | Engineering (Redis / server down) |
| Progress bar stuck at same % for > 20 min while pitches show green | Engineering (DB or result endpoint issue) |
| Est. finish time > 60 min past planned end | Admin decision: extend tournament or skip remaining sessions |

---

## 5. Quick reference

```
Page:        GET /admin/tournaments/{id}/live
WS:          wss://{host}/ws/tournaments/{id}/live?token={jwt}
Auth:        ADMIN, SPORT_DIRECTOR, INSTRUCTOR roles allowed
Throttle:    200 ms between WS frames (max 5 frames/sec per client)
Idle alert:  5 min without a result from a pitch
Stats:       Throttle stats sent to client every 30 s
Redis down:  Page still loads; WS retries with 2→4→8→…→30 s back-off
```

---

## 6. Architecture overview (for engineering reference)

```
Result submission (HTTP PATCH /api/v1/sessions/{id}/results)
  └─ _publish_session_result(db, session)
       ├─ Queries: completed_count, total_count
       ├─ Calls:   publish_tournament_update(tournament_id, payload)
       │             ├─ Updates _pitch_last_activity[tid][pitch_id] = now()
       │             └─ redis.publish("tournament:{id}:updates", json_payload)
       └─ Swallows ALL exceptions — live monitoring never blocks results

WebSocket handler (WS /ws/tournaments/{id}/live?token=…)
  ├─ Background task: emit throttle_stats every 30 s
  ├─ Background task: call get_idle_pitches() every 60 s → emit pitch_idle_alert
  └─ _throttled_stream(subscribe_tournament_updates(tid), interval=0.2s)
       ├─ asyncio.Queue(maxsize=1) — drops stale, keeps latest
       └─ Yields at most 5 msg/s to websocket.send_text()
```

**Log locations (server-side):**
- `WS connected: tournament=X user=Y role=Z` — on each WS open
- `WS session ended: … recv=N fwd=N drop=N (X% drop rate)` — on disconnect (INFO)
- `WS dropped events: … dropped=N` — on disconnect if dropped > 0 (WARNING)
- `Pitch idle alert: tournament=X pitch=Y idle=Zs` — each idle alert fired (WARNING)
- `Redis pub/sub unavailable` — on Redis connection failure (WARNING)
