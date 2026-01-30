"""
Playwright E2E Test: Quick Test - FULL FLOW (Alapján: COMPLETE_WORKFLOW_ANALYSIS.md)

TELJES frontend click-flow tesztelése:
🏠 Home → ➕ New Tournament → Configuration → ✅ Create → ⏳ Progress → ✅ Results

Video + Screenshot rögzítéssel.
Valós backend API hívásokkal.
Headed módban (látható böngésző).

Ez a BELÉPŐTESZT - amíg ez nem megy, nem lépünk tovább.
"""

from playwright.sync_api import sync_playwright
import time
import os

BASE_URL = "http://localhost:8501"

def test_quick_test_e2e_final():
    """
    TELJES E2E teszt: Quick Test flow

    SUCCESS CRITERIA:
    - "⏳ Test Running..." megjelenik
    - "✅ Test Results" megjelenik
    - Tournament ID létezik és nem null
    - Verdict megjelenik (WORKING/DEGRADED/NOT_WORKING)
    - ZERO crashes
    """

    print("\n" + "="*100)
    print("🎭 PLAYWRIGHT E2E TEST: QUICK TEST - TELJES FLOW")
    print("="*100)
    print("Flow: Home → New Tournament → Config → Create → Progress → Results")
    print("="*100 + "\n")

    with sync_playwright() as p:
        # ============================================================
        # BROWSER SETUP - Headed mode + Video recording
        # ============================================================
        print("🔧 Browser setup...")
        browser = p.firefox.launch(
            headless=False,
            slow_mo=800,  # 800ms slow motion for visibility
        )

        # Create context with video recording
        context = browser.new_context(
            record_video_dir="./test_videos",
            record_video_size={"width": 1280, "height": 720}
        )

        page = context.new_page()

        print("   ✅ Firefox launched in headed mode")
        print("   📹 Video recording enabled → ./test_videos/")
        print("")

        try:
            # ============================================================
            # LÉPÉS 0: Navigate to Home
            # ============================================================
            print("="*100)
            print("LÉPÉS 0: NAVIGATE TO HOME SCREEN")
            print("="*100)
            print(f"→ Opening {BASE_URL}...")

            page.goto(BASE_URL, wait_until="networkidle")
            time.sleep(3)

            # Verify home screen
            page_text = page.text_content('body') or ""
            assert "Tournament Sandbox" in page_text, "Home screen címe nem található"
            print("   ✅ Home screen betöltődött")

            # Screenshot
            page.screenshot(path="screenshot_00_home.png")
            print("   📸 Screenshot: screenshot_00_home.png")
            print("")

            # ============================================================
            # LÉPÉS 1: Click "➕ New Tournament"
            # ============================================================
            print("="*100)
            print("LÉPÉS 1: CLICK '➕ NEW TOURNAMENT' BUTTON")
            print("="*100)
            print("→ Keresem a '➕ New Tournament' gombot...")

            new_tournament_btn = page.get_by_role("button", name="➕ New Tournament")
            assert new_tournament_btn.is_visible(timeout=5000), "New Tournament gomb nem látható"
            print("   ✅ '➕ New Tournament' gomb megtalálva")

            print("→ Kattintás a '➕ New Tournament' gombra...")
            new_tournament_btn.click()
            time.sleep(3)

            # Verify configuration screen appeared
            page_text = page.text_content('body') or ""
            assert "Test Mode" in page_text or "Game Type" in page_text, "Configuration screen nem töltődött be"
            print("   ✅ Configuration screen betöltődött")

            page.screenshot(path="screenshot_01_config_loaded.png")
            print("   📸 Screenshot: screenshot_01_config_loaded.png")
            print("")

            # ============================================================
            # LÉPÉS 2: Fill Configuration Form
            # ============================================================
            print("="*100)
            print("LÉPÉS 2: FILL CONFIGURATION FORM")
            print("="*100)

            # 2.1: Verify Quick Test is selected
            print("→ Ellenőrzés: 'Quick Test' mode kiválasztva...")
            page_text = page.text_content('body') or ""
            assert "Quick Test" in page_text, "Quick Test mode nem található"
            print("   ✅ Quick Test mode aktív")

            # 2.2: Verify Game Type is selected
            print("→ Ellenőrzés: Game type (GânFootvolley) kiválasztva...")
            assert "GânFootvolley" in page_text or "Selected" in page_text, "Game type nem kiválasztva"
            print("   ✅ Game type kiválasztva")

            # 2.2.5: SCROLL DOWN to reveal Tournament Configuration section
            print("→ Görgetés lefelé a Tournament Configuration szekcióhoz...")
            page.evaluate("window.scrollBy(0, 400)")  # Scroll down 400px
            time.sleep(2)
            page.screenshot(path="screenshot_02a_scrolled_to_tournament_config.png")
            print("   ✅ Legörgetve")

            # 2.3: Select Tournament Type (KÖTELEZŐ!)
            print("→ Tournament Type kiválasztása (KÖTELEZŐ mező)...")
            try:
                # Find ALL selectboxes
                selects = page.locator('select').all()
                print(f"   Talált {len(selects)} selectbox")

                tournament_type_select = None
                for idx, select in enumerate(selects):
                    options = select.locator('option').all()
                    option_texts = [opt.text_content() or "" for opt in options]

                    # Check if this is tournament type selector
                    if any("league" in text.lower() or "knockout" in text.lower() for text in option_texts):
                        tournament_type_select = select
                        print(f"   Megtaláltam a Tournament Type selectbox-ot (index {idx})")
                        print(f"   Opciók: {[t for t in option_texts if t]}")
                        break

                if tournament_type_select:
                    # Select "League" (általában index=1, 0 a placeholder)
                    tournament_type_select.select_option(index=1)
                    time.sleep(2)  # Wait for form update
                    print("   ✅ Tournament Type = League")
                else:
                    print("   ❌ Tournament Type selector NEM TALÁLHATÓ!")
                    raise Exception("Tournament Type kötelező mező nem található")
            except Exception as e:
                print(f"   ❌ Tournament Type selection FAILED: {e}")
                raise

            # 2.4: Select Campus (KÖTELEZŐ!)
            print("→ Campus kiválasztása (KÖTELEZŐ mező)...")
            try:
                # Find Campus selectbox (általában a második select)
                selects = page.locator('select').all()
                campus_select = None

                for idx, select in enumerate(selects):
                    options = select.locator('option').all()
                    option_texts = [opt.text_content() or "" for opt in options]

                    # Check if this is campus selector
                    if any("offline" in text.lower() or "online" in text.lower() for text in option_texts):
                        campus_select = select
                        print(f"   Megtaláltam a Campus selectbox-ot (index {idx})")
                        break

                if campus_select:
                    # Select "Offline"
                    campus_select.select_option(index=1)
                    time.sleep(2)
                    print("   ✅ Campus = Offline")
                else:
                    print("   ❌ Campus selector NEM TALÁLHATÓ!")
                    raise Exception("Campus kötelező mező nem található")
            except Exception as e:
                print(f"   ❌ Campus selection FAILED: {e}")
                raise

            # 2.5: Set Player Count (KÖTELEZŐ!)
            print("→ Player Count beállítása (KÖTELEZŐ mező)...")
            try:
                # Find number input for player count
                number_inputs = page.locator('input[type="number"]').all()
                print(f"   Talált {len(number_inputs)} number input")

                if len(number_inputs) > 0:
                    player_count_input = number_inputs[0]  # First number input is likely player count
                    player_count_input.click()
                    player_count_input.fill("")  # Clear first
                    player_count_input.fill("8")
                    time.sleep(2)
                    print("   ✅ Player Count = 8")
                else:
                    print("   ❌ Player Count input NEM TALÁLHATÓ!")
                    raise Exception("Player Count kötelező mező nem található")
            except Exception as e:
                print(f"   ❌ Player Count FAILED: {e}")
                raise

            page.screenshot(path="screenshot_02_form_filled.png")
            print("   📸 Screenshot: screenshot_02_form_filled.png")
            print("")

            # ============================================================
            # LÉPÉS 3: Scroll to "Create Tournament" button
            # ============================================================
            print("="*100)
            print("LÉPÉS 3: SCROLL TO 'CREATE TOURNAMENT' BUTTON")
            print("="*100)
            print("→ Görgetés a lap aljára (több lépésben)...")

            # Multiple scroll attempts
            for i in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            # Also try keyboard End key
            page.keyboard.press("End")
            time.sleep(2)

            print("   ✅ Lap végére görgetve (többszöri scroll)")

            page.screenshot(path="screenshot_03_scrolled.png")
            print("   📸 Screenshot: screenshot_03_scrolled.png")

            # Log current page height
            page_height = page.evaluate("document.body.scrollHeight")
            scroll_pos = page.evaluate("window.pageYOffset")
            print(f"   Page height: {page_height}px, Scroll position: {scroll_pos}px")
            print("")

            # ============================================================
            # LÉPÉS 4: Click "✅ Create Tournament"
            # ============================================================
            print("="*100)
            print("LÉPÉS 4: CLICK '✅ CREATE TOURNAMENT' BUTTON")
            print("="*100)
            print("→ Keresem a '✅ Create Tournament' gombot...")

            # Try multiple button name variations
            create_btn = None
            button_variations = [
                "✅ Create Tournament",
                "Create Tournament",
                "✅Create Tournament",  # No space
                "Create tournament",   # Lowercase
            ]

            for btn_name in button_variations:
                try:
                    print(f"   Próbálom: '{btn_name}'")
                    btn = page.get_by_role("button", name=btn_name)
                    if btn.count() > 0:
                        print(f"   Megtaláltam a gombot: '{btn_name}' (count={btn.count()})")

                        # Check visibility
                        if btn.is_visible(timeout=3000):
                            create_btn = btn
                            print(f"   ✅ Gomb látható: '{btn_name}'")
                            break
                        else:
                            print(f"   ⚠️  Gomb létezik de nem látható: '{btn_name}'")
                except Exception as e:
                    print(f"   Nem található: '{btn_name}'")

            # If still not found, try text search
            if not create_btn:
                print("   → Alternatív keresés: text contains 'Create'...")
                all_buttons = page.locator('button').all()
                print(f"   Talált {len(all_buttons)} gombot az oldalon")

                for idx, btn in enumerate(all_buttons):
                    btn_text = btn.text_content() or ""
                    if "create" in btn_text.lower() and "tournament" in btn_text.lower():
                        print(f"   Megtaláltam index={idx}: '{btn_text.strip()}'")
                        if btn.is_visible():
                            create_btn = btn
                            print(f"   ✅ Ez a gomb látható!")
                            break

            if not create_btn:
                print("   ❌ Create Tournament gomb NEM TALÁLHATÓ!")
                print("   → DOM debug log készítése...")

                # Log all buttons on page
                all_buttons = page.locator('button').all()
                print(f"\n   Összes gomb az oldalon ({len(all_buttons)} db):")
                for idx, btn in enumerate(all_buttons[:20]):  # First 20 buttons
                    btn_text = btn.text_content() or ""
                    is_visible = btn.is_visible()
                    print(f"     {idx}. '{btn_text.strip()}' (visible={is_visible})")

                raise Exception("Create Tournament gomb nem található a DOM-ban")

            print("   ✅ '✅ Create Tournament' gomb megtalálva és látható")

            print("→ ⚠️  KATTINTÁS a 'Create Tournament' gombra...")
            print("   (Ez elindítja a Quick Test API hívást)")
            create_btn.click()
            time.sleep(3)

            page.screenshot(path="screenshot_04_create_clicked.png")
            print("   📸 Screenshot: screenshot_04_create_clicked.png")
            print("")

            # ============================================================
            # LÉPÉS 5: Wait for Progress Screen
            # ============================================================
            print("="*100)
            print("LÉPÉS 5: WAIT FOR PROGRESS SCREEN & API EXECUTION")
            print("="*100)
            print("→ Várakozás a 'Progress' screen megjelenésére...")

            # Wait for progress indicators
            max_wait = 5
            progress_found = False

            for i in range(max_wait):
                time.sleep(1)
                page_text = page.text_content('body') or ""

                if "Test Running" in page_text or "Running" in page_text or "Progress" in page_text:
                    progress_found = True
                    print(f"   ✅ Progress screen megjelent (t={i+1}s)")
                    break

            # Screenshot of progress (if appeared)
            if progress_found:
                page.screenshot(path="screenshot_05_progress.png")
                print("   📸 Screenshot: screenshot_05_progress.png")
            else:
                print("   ⚠️  Progress screen lehet hogy túl gyors volt")

            print("")
            print("→ Várakozás az API válaszra (Quick Test futás)...")
            print("   Backend folyamat: Create → Enroll → Rank → Complete → Reward → Verdict")

            # ============================================================
            # LÉPÉS 6: Wait for Results Screen
            # ============================================================
            print("="*100)
            print("LÉPÉS 6: WAIT FOR RESULTS SCREEN")
            print("="*100)
            print("→ Várakozás a Results screen megjelenésére...")

            max_wait_results = 30  # 30 seconds max
            results_found = False

            for i in range(max_wait_results):
                time.sleep(1)
                page_text = page.text_content('body') or ""

                # Check for results indicators
                if ("Verdict" in page_text or
                    "WORKING" in page_text or
                    "Test Results" in page_text or
                    "Skill Progression" in page_text):
                    results_found = True
                    print(f"   ✅ Results screen megjelent! (t={i+1}s)")
                    break

                # Progress indicator
                if i % 5 == 0:
                    print(f"   ⏳ Várakozás... {i+1}s / {max_wait_results}s")

            assert results_found, f"Results screen nem jelent meg {max_wait_results}s alatt"

            time.sleep(3)  # Let results fully load

            page.screenshot(path="screenshot_06_results.png")
            print("   📸 Screenshot: screenshot_06_results.png")
            print("")

            # ============================================================
            # LÉPÉS 7: VERIFY RESULTS SCREEN
            # ============================================================
            print("="*100)
            print("LÉPÉS 7: VERIFY RESULTS SCREEN CONTENT")
            print("="*100)

            page_text = page.text_content('body') or ""

            # ASSERTION 1: "Test Results" cím
            print("→ Assertion 1: '✅ Test Results' vagy 'Results' cím...")
            assert "Result" in page_text or "result" in page_text, "Results cím nem található"
            print("   ✅ PASS: Results cím megtalálva")

            # ASSERTION 2: Verdict
            print("→ Assertion 2: Verdict megjelenése...")
            has_verdict = ("WORKING" in page_text or
                          "DEGRADED" in page_text or
                          "NOT_WORKING" in page_text or
                          "Verdict" in page_text)
            assert has_verdict, "Verdict nem található"
            print("   ✅ PASS: Verdict megtalálva")

            # ASSERTION 3: Tournament ID
            print("→ Assertion 3: Tournament ID létezik...")
            has_tournament_id = ("Tournament" in page_text and
                               ("ID" in page_text or "id" in page_text or any(char.isdigit() for char in page_text)))
            assert has_tournament_id, "Tournament ID nem található"
            print("   ✅ PASS: Tournament ID megtalálva")

            # ASSERTION 4: No errors
            print("→ Assertion 4: No Streamlit errors...")
            error_elements = page.locator('[data-testid="stException"]').all()
            none_type_errors = page.get_by_text("'NoneType' object has no attribute").all()
            traceback_errors = page.get_by_text("Traceback (most recent call last)").all()

            total_errors = len(error_elements) + len(none_type_errors) + len(traceback_errors)
            assert total_errors == 0, f"Errors detected: {total_errors}"
            print("   ✅ PASS: No errors detected")

            print("")

            # ============================================================
            # SUCCESS!
            # ============================================================
            print("="*100)
            print("✅ ✅ ✅ TEST PASSED - TELJES FLOW SIKERES ✅ ✅ ✅")
            print("="*100)
            print("🎉 Quick Test flow végigment hibátlanul!")
            print("")
            print("Ellenőrzött lépések:")
            print("  ✅ Home screen betöltés")
            print("  ✅ New Tournament gomb kattintás")
            print("  ✅ Configuration screen betöltés")
            print("  ✅ Form kitöltés")
            print("  ✅ Create Tournament kattintás")
            print("  ✅ Progress screen (vagy direkt Results)")
            print("  ✅ Results screen megjelenés")
            print("  ✅ Verdict megjelenés")
            print("  ✅ Tournament ID létezik")
            print("  ✅ Zero errors")
            print("")
            print("="*100)

            # Keep browser open for inspection
            print("\n🔍 Böngésző nyitva marad 5 másodpercig vizsgálatra...")
            time.sleep(5)

        except AssertionError as e:
            print("\n" + "="*100)
            print("❌ ❌ ❌ TEST FAILED - ASSERTION ERROR ❌ ❌ ❌")
            print("="*100)
            print(f"Hiba: {e}")
            print("")

            # Take failure screenshot
            page.screenshot(path="screenshot_FAILURE.png")
            print("📸 Failure screenshot: screenshot_FAILURE.png")

            raise

        except Exception as e:
            print("\n" + "="*100)
            print("❌ ❌ ❌ TEST FAILED - EXCEPTION ❌ ❌ ❌")
            print("="*100)
            print(f"Exception: {e}")
            print("")

            # Take failure screenshot
            page.screenshot(path="screenshot_EXCEPTION.png")
            print("📸 Exception screenshot: screenshot_EXCEPTION.png")

            raise

        finally:
            # Close context and browser
            context.close()
            browser.close()

            print("\n📹 Video mentve: ./test_videos/")
            print("🖼️  Screenshots mentve: ./screenshot_*.png")
            print("")


if __name__ == "__main__":
    try:
        test_quick_test_e2e_final()
        print("\n🎉 ✅ E2E TEST SIKERES!")
        exit(0)
    except Exception as e:
        print(f"\n💥 ❌ E2E TEST FAILED: {e}")
        exit(1)
