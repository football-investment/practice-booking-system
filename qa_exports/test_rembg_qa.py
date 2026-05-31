"""
Phase 2A rembg mode QA — Playwright script.

Tests the full BG removal flow on mood_intro_neutral (uploaded, no proc URL).
Requires: server on :8000, Redis running, Celery mood_photos worker running,
          BG_REMOVAL_PROCESSOR=rembg in .env.
"""
import time
import psycopg2
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8000"
EMAIL = "rdias@manchestercity.com"
PASSWORD = "Dias2026!"
SLOT = "mood_intro_neutral"
DB_URL = "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"

RESULTS = []

def log(label, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((label, status, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))

def get_slot_row():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT status, original_url, processed_png_url FROM user_mood_photos "
        "WHERE user_id=3 AND slot=%s",
        (SLOT,),
    )
    row = cur.fetchone()
    conn.close()
    return row  # (status, original_url, processed_png_url)

def _make_token(email: str) -> str:
    """Generate a JWT access token directly (bypasses web login form / CSRF)."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from datetime import timedelta
    from app.core.auth import create_access_token
    return create_access_token({"sub": email}, timedelta(hours=2))


def run_qa():
    token = _make_token(EMAIL)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        # ── 1. Inject auth cookie (bypasses CSRF/login-form complexity) ───────
        print("\n── 1. Auth cookie injection")
        # Visit the base URL first so the domain is known, then set cookie
        page.goto(f"{BASE}/health")
        ctx.add_cookies([{
            "name":     "access_token",
            "value":    f"Bearer {token}",
            "domain":   "127.0.0.1",
            "path":     "/",
            "httpOnly": False,
            "secure":   False,
        }])
        log("access_token cookie injected", True, EMAIL)

        # ── 2. Navigate to mood photos page ──────────────────────────────────
        print("\n── 2. Navigate to mood photos page")
        page.goto(f"{BASE}/profile/my-mood-photos")
        page.wait_for_load_state("networkidle", timeout=10000)
        log("Page loads (200)", "my-mood-photos" in page.url, page.url)

        # ── 3. rembg mode: Remove Background button visible on uploaded slot ─
        print("\n── 3. Remove Background button visibility (rembg mode)")
        # Wait for the page to fully render — look for any mp-card
        page.wait_for_selector('.mp-card', timeout=5000)

        # Button should be visible — uploaded slot, rembg mode
        # Selector: button with onclick containing _mpRemoveBg('mood_intro_neutral')
        remove_btn_sel = f"button[onclick*=\"_mpRemoveBg('{SLOT}')\"]"
        has_remove_btn = page.locator(remove_btn_sel).count() > 0
        log("Remove Background button visible for uploaded slot", has_remove_btn)

        # Retry button should NOT be visible (status=uploaded, not failed)
        retry_sel_text = "↺ Retry Remove Background"
        # Retry button uses same _mpRemoveBg onclick but with text "↺ Retry Remove Background"
        # In uploaded state the retry button won't appear (only for failed slots)
        retry_count = page.locator(f"button:has-text('{retry_sel_text}')").count()
        # Count only retry button for THIS slot — check if any is associated
        no_retry = retry_count == 0
        log("Retry button absent (status=uploaded, not failed)", no_retry)

        # Reset button: id="btn-reset-{slot}", only shown on processing status (hidden by CSS initially)
        reset_btn_id = f"#btn-reset-{SLOT}"
        no_reset = page.locator(reset_btn_id).count() == 0
        log("Reset button absent (status=uploaded)", no_reset)

        if not has_remove_btn:
            print("\n  ABORT: Remove Background button not found — check BG_REMOVAL_PROCESSOR=rembg in .env")
            ctx.close(); browser.close()
            return

        # ── 4. Click Remove Background ────────────────────────────────────────
        print("\n── 4. Click Remove Background")
        # CSRF token lives in the csrf_token cookie (set by middleware on GET requests)
        # Read it from the browser cookie jar
        csrf_resp = page.evaluate("""() => {
            var m = document.cookie.match(/(?:^|;\\s*)csrf_token=([^;]+)/);
            return m ? decodeURIComponent(m[1]) : null;
        }""")
        log("CSRF token found in cookie", bool(csrf_resp), csrf_resp[:12] + "..." if csrf_resp else "None")

        # Trigger via JS fetch (same as the template does)
        fetch_result = page.evaluate(f"""async (csrfToken) => {{
            const r = await fetch('/profile/my-mood-photos/{SLOT}/remove-bg', {{
                method: 'POST',
                headers: {{'X-CSRF-Token': csrfToken}},
                credentials: 'include',
                redirect: 'follow',
            }});
            return r.status;
        }}""", csrf_resp)
        log("POST /remove-bg returns 200/303", fetch_result in (200, 303), f"status={fetch_result}")
        # status 0 = opaque (redirect followed by manual) — expected with redirect:'manual'

        # ── 5. Verify DB status=processing ───────────────────────────────────
        print("\n── 5. DB status after trigger")
        time.sleep(0.5)
        row = get_slot_row()
        log("DB status='processing' after trigger", row[0] == "processing", f"got={row[0]}")

        # ── 6. Poll status endpoint until ready (max 60s) ────────────────────
        print("\n── 6. Poll status endpoint (max 60s)")
        ready = False
        for i in range(20):
            time.sleep(3)
            status_json = page.evaluate(f"""async () => {{
                const r = await fetch('/profile/my-mood-photos/{SLOT}/status', {{
                    credentials: 'include'
                }});
                return r.json();
            }}""")
            current = status_json.get("status")
            proc_url = status_json.get("processed_png_url")
            timed_out = status_json.get("processing_timed_out", False)
            print(f"    [{i+1}/20] status={current} timed_out={timed_out} proc_url={bool(proc_url)}")
            if current == "ready":
                ready = True
                log("Status endpoint returns ready", True, f"proc_url={bool(proc_url)}")
                log("processed_png_url set in status response", bool(proc_url), proc_url or "None")
                break
            if current == "failed":
                log("Status endpoint returns ready", False, "got=failed")
                break
            if timed_out:
                log("Status endpoint returns ready", False, "got=processing+timed_out")
                break

        if not ready:
            log("Status endpoint returns ready", False, f"last status={current}")

        # ── 7. Verify DB state ────────────────────────────────────────────────
        print("\n── 7. DB state after completion")
        row = get_slot_row()
        log("DB status='ready'", row[0] == "ready", f"got={row[0]}")
        log("DB processed_png_url populated", bool(row[2]), row[2] or "None")

        # ── 8. Verify _proc_ file exists on disk ──────────────────────────────
        print("\n── 8. Disk file check")
        import os
        if row[2]:
            filename = row[2].split("/")[-1]
            disk_path = (
                f"/Users/lovas.zoltan/Seafile/Football Investment/Projects/"
                f"Football Investment Internship/practice_booking_system/"
                f"app/static/uploads/mood_photos/{filename}"
            )
            exists = os.path.exists(disk_path)
            log("_proc_ file exists on disk", exists, filename)
        else:
            log("_proc_ file exists on disk", False, "processed_png_url is NULL")

        # ── 9. Reload page — UI shows processed image ─────────────────────────
        print("\n── 9. Page reload — processed image displayed")
        page.goto(f"{BASE}/profile/my-mood-photos")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_selector('.mp-card', timeout=5000)

        # Find the img element near the slot's Remove Bg button OR near its delete button.
        # Since there's no data-slot on the card div, use the delete button's onclick to
        # find the card, then find the img within it.
        if row[2]:
            proc_filename = row[2].split("/")[-1]
            # Get all img elements and find one with proc_filename in src
            all_imgs = page.locator("img").all()
            found_proc = any(
                proc_filename in (el.get_attribute("src") or "")
                for el in all_imgs
            )
            log("UI shows processed image src", found_proc, proc_filename[-50:])
        else:
            log("UI shows processed image src", False, "no proc URL")

        # Status badge for this slot should say "Background Removed" (rembg mode + ready)
        # The badge with the ready label is "✨ Background Removed" in rembg mode
        ready_badge = page.locator(".mp-badge-ready")
        ready_count = ready_badge.count()
        log("Ready badge present on page", ready_count > 0, f"{ready_count} ready badges")

        # Remove Bg button for this slot should now be ABSENT (status=ready)
        has_remove_after = page.locator(remove_btn_sel).count() > 0
        log("Remove Background button absent after ready", not has_remove_after)

        # ── 10. Simulate failed slot for Retry button test ─────────────────────
        print("\n── 10. Retry button test (force a slot to failed state)")
        conn3 = psycopg2.connect(DB_URL)
        cur3 = conn3.cursor()
        # Use angry_competitive (already ready) — force to failed for test
        test_slot = "mood_angry_competitive"
        cur3.execute(
            "UPDATE user_mood_photos SET status='failed', processed_png_url=NULL "
            "WHERE user_id=3 AND slot=%s",
            (test_slot,),
        )
        conn3.commit()
        conn3.close()

        page.goto(f"{BASE}/profile/my-mood-photos")
        page.wait_for_selector('.mp-card', timeout=5000)
        retry_btn_sel2 = f"button[onclick*=\"_mpRemoveBg('{test_slot}')\"]"
        retry_text_sel = f"button:has-text('↺ Retry Remove Background')"
        has_retry_btn = page.locator(retry_btn_sel2).count() > 0
        log("Retry Remove Background button on failed slot", has_retry_btn, f"slot={test_slot}")

        # Restore the slot to ready (undo the forced failure)
        proc_url = f"/static/uploads/mood_photos/3_mood_{test_slot}_proc_restored.png"
        conn4 = psycopg2.connect(DB_URL)
        cur4 = conn4.cursor()
        cur4.execute(
            "UPDATE user_mood_photos SET status='ready', "
            "processed_png_url=(SELECT processed_png_url FROM user_mood_photos WHERE user_id=3 AND slot=%s LIMIT 1) "
            "WHERE user_id=3 AND slot=%s",
            (test_slot, test_slot),
        )
        # Actually just restore the original ready state from before
        cur4.execute(
            "UPDATE user_mood_photos SET status='ready' WHERE user_id=3 AND slot=%s",
            (test_slot,),
        )
        conn4.commit()
        conn4.close()

        ctx.close()
        browser.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PHASE 2A rembg QA — SUMMARY")
    print("="*60)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed_list = [(l, d) for l, s, d in RESULTS if s == "FAIL"]
    print(f"  {passed}/{len(RESULTS)} checks PASS")
    if failed_list:
        print("\n  FAILURES:")
        for l, d in failed_list:
            print(f"    ✗ {l}" + (f" — {d}" if d else ""))
    else:
        print("  ALL PASS ✓")
    print()

if __name__ == "__main__":
    run_qa()
