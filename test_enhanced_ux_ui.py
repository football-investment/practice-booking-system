#!/usr/bin/env python3
"""
Enhanced UX/UI Testing Script
=============================

Teszteli az onboarding oldal UX/UI fejlesztéseit:
1. Egyenrangú szakirány megjelenítés
2. Átlátható kártya elrendezés  
3. Intuitív felhasználói élmény
4. Összehasonlítható választási lehetőségek

Created: 2025-09-21
"""

import requests
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def print_test_header(test_name):
    """Kiírja a teszt nevét formázott módon"""
    print(f"\n{'='*60}")
    print(f"🎨 {test_name}")
    print(f"{'='*60}")

def print_success(message):
    """Sikeres teszt üzenet"""
    print(f"✅ {message}")

def print_error(message):
    """Hiba üzenet"""
    print(f"❌ {message}")

def print_info(message):
    """Info üzenet"""
    print(f"💡 {message}")

def test_enhanced_preview_cards():
    """Teszteli az enhanced preview kártyák CSS-ét"""
    print_test_header("Enhanced Preview Cards CSS Test")
    
    css_files = [
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/pages/student/SemesterCentricOnboarding.css"
    ]
    
    required_classes = [
        'specialization-preview-enhanced',
        'spec-preview-card', 
        'player-track',
        'coach-track',
        'internship-track',
        'spec-card-header',
        'spec-icon-large',
        'spec-highlights',
        'highlight-item',
        'spec-track-info'
    ]
    
    all_found = True
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for class_name in required_classes:
                if f'.{class_name}' in content:
                    print_success(f"Preview: {class_name} ✓")
                else:
                    print_error(f"Preview: {class_name} hiányzik")
                    all_found = False
                    
        except Exception as e:
            print_error(f"CSS fájl olvasási hiba: {e}")
            all_found = False
    
    return all_found

def test_enhanced_selection_cards():
    """Teszteli az enhanced selection kártyák CSS-ét"""
    print_test_header("Enhanced Selection Cards CSS Test")
    
    css_files = [
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/components/onboarding/ParallelSpecializationSelector.css"
    ]
    
    required_classes = [
        'specialization-options-enhanced',
        'enhanced-specialization-card',
        'enhanced-spec-header',
        'enhanced-spec-icon',
        'enhanced-spec-title',
        'enhanced-selection-status',
        'status-badge',
        'enhanced-spec-content',
        'enhanced-track-highlights',
        'track-highlight',
        'enhanced-track-info',
        'track-detail',
        'enhanced-requirements',
        'requirement-item',
        'enhanced-card-action',
        'track-select-btn'
    ]
    
    all_found = True
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for class_name in required_classes:
                if f'.{class_name}' in content:
                    print_success(f"Selection: {class_name} ✓")
                else:
                    print_error(f"Selection: {class_name} hiányzik")
                    all_found = False
                    
        except Exception as e:
            print_error(f"CSS fájl olvasási hiba: {e}")
            all_found = False
    
    return all_found

def test_track_equal_representation():
    """Teszteli, hogy a három track egyenrangúan jelenik-e meg"""
    print_test_header("Track Equal Representation Test")
    
    js_file = "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/pages/student/SemesterCentricOnboarding.js"
    
    try:
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ellenőrizzük az egyenrangú megjelenítést
        checks = {
            'Player Track részletei': 'Player Track' in content and 'GānCuju™️©️ Játékos Specializáció' in content,
            'Coach Track részletei': 'Coach Track' in content and 'LFA Edzői Specializáció' in content,
            'Internship Track részletei': 'Internship Track' in content and 'LFA Gyakornoki Program' in content,
            'Minden track highlight': 'spec-highlights' in content and 'highlight-item' in content,
            'Track-specifikus ikonok': 'spec-icon-large' in content and '⚽' in content and '👨‍🏫' in content and '💼' in content,
            'Egyenrangú kártya struktúra': 'spec-preview-card' in content and 'spec-card-header' in content
        }
        
        all_passed = True
        for check_name, result in checks.items():
            if result:
                print_success(f"{check_name}: ✓")
            else:
                print_error(f"{check_name}: hiányzik")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print_error(f"JS fájl olvasási hiba: {e}")
        return False

def test_responsive_design():
    """Teszteli a reszponzív design elemeket"""
    print_test_header("Responsive Design Test")
    
    css_files = [
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/pages/student/SemesterCentricOnboarding.css",
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/components/onboarding/ParallelSpecializationSelector.css"
    ]
    
    responsive_checks = [
        'specialization-preview-enhanced',
        'enhanced-specialization-card',
        'enhanced-spec-header',
        'enhanced-spec-icon',
        'track-detail',
        '@media (max-width: 768px)'
    ]
    
    all_responsive = True
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            has_mobile_styles = '@media (max-width: 768px)' in content
            if has_mobile_styles:
                print_success(f"Mobil stílusok: {css_file.split('/')[-1]} ✓")
                
                # Ellenőrizzük az enhanced elemek mobil stílusait
                for check in responsive_checks:
                    if check in content:
                        print_success(f"  - {check}: ✓")
                    else:
                        print_error(f"  - {check}: hiányzik")
                        all_responsive = False
            else:
                print_error(f"Nincs mobil stílus: {css_file.split('/')[-1]}")
                all_responsive = False
                
        except Exception as e:
            print_error(f"CSS fájl olvasási hiba: {e}")
            all_responsive = False
    
    return all_responsive

def test_ux_improvements():
    """Teszteli a UX fejlesztéseket"""
    print_test_header("UX Improvements Test")
    
    # Ellenőrizzük a ParallelSpecializationSelector komponens enhanced verzióját
    js_file = "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/components/onboarding/ParallelSpecializationSelector.js"
    
    try:
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ux_checks = {
            'Enhanced card layout': 'specialization-options-enhanced' in content,
            'Track-specific styling': 'trackType.toLowerCase()' in content,
            'Status indicators': 'enhanced-selection-status' in content,
            'Track highlights': 'enhanced-track-highlights' in content,
            'Requirements display': 'enhanced-requirements' in content,
            'Action buttons': 'enhanced-card-action' in content,
            'Interactive feedback': 'track-select-btn' in content,
            'Consistent iconography': 'spec.specialization_type === \'PLAYER\' ? \'⚽\'' in content
        }
        
        all_ux_passed = True
        for check_name, result in ux_checks.items():
            if result:
                print_success(f"UX: {check_name} ✓")
            else:
                print_error(f"UX: {check_name} hiányzik")
                all_ux_passed = False
        
        return all_ux_passed
        
    except Exception as e:
        print_error(f"JS fájl olvasási hiba: {e}")
        return False

def test_visual_hierarchy():
    """Teszteli a vizuális hierarchiát"""
    print_test_header("Visual Hierarchy Test")
    
    css_files = [
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/pages/student/SemesterCentricOnboarding.css",
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/components/onboarding/ParallelSpecializationSelector.css"
    ]
    
    hierarchy_checks = [
        'font-size: 1.4rem',  # H4 címek
        'font-weight: 800',   # Erős hangsúlyok
        'border-radius: 20px', # Kerekített sarkok
        'box-shadow:',        # Árnyékok
        'transform: translateY', # Hover animációk
        'transition: all',    # Smooth átmenetek
        'linear-gradient',    # Gradiensek
        'hover:'              # Hover állapotok
    ]
    
    all_hierarchy = True
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_name = css_file.split('/')[-1]
            print_info(f"Elemzés: {file_name}")
            
            for check in hierarchy_checks:
                if check in content:
                    print_success(f"  - {check}: ✓")
                else:
                    print_error(f"  - {check}: hiányzik")
                    all_hierarchy = False
                    
        except Exception as e:
            print_error(f"CSS fájl olvasási hiba: {e}")
            all_hierarchy = False
    
    return all_hierarchy

def test_backend_integration():
    """Teszteli a backend integráció működését"""
    print_test_header("Backend Integration Test")
    
    try:
        # Backend health check
        response = requests.get(f"{BASE_URL}/api/v1/debug/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend működik")
            
            # Frontend health check
            frontend_response = requests.get(FRONTEND_URL, timeout=5)
            if frontend_response.status_code == 200:
                print_success("Frontend elérhető")
                return True
            else:
                print_error(f"Frontend nem elérhető: {frontend_response.status_code}")
                return False
        else:
            print_error(f"Backend nem működik: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Backend/Frontend kapcsolat hiba: {e}")
        return False

def run_enhanced_ux_ui_tests():
    """Futtatja az összes UX/UI tesztet"""
    print(f"""
🎨 Enhanced UX/UI Test Suite
============================
Időpont: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Ez a teszt suite ellenőrzi az onboarding UX/UI fejlesztéseit:
✨ Egyenrangú szakirány megjelenítés
🎯 Átlátható kártya elrendezés
🖥️  Intuitív felhasználói élmény  
📱 Reszponzív design
🎭 Vizuális hierarchia
""")
    
    tests = [
        test_enhanced_preview_cards,
        test_enhanced_selection_cards,
        test_track_equal_representation,
        test_responsive_design,
        test_ux_improvements,
        test_visual_hierarchy,
        test_backend_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print_error(f"Teszt futtatási hiba: {e}")
    
    # Összegzés
    print(f"\n{'='*60}")
    print(f"📊 UX/UI TESZT ÖSSZEGZÉS")
    print(f"{'='*60}")
    print(f"✅ Sikeres tesztek: {passed}/{total}")
    print(f"❌ Sikertelen tesztek: {total - passed}/{total}")
    
    if passed == total:
        print(f"\n🎉 MINDEN UX/UI TESZT SIKERES!")
        print(f"Az onboarding oldal UX/UI fejlesztései megfelelően működnek:")
        print(f"  ✨ Egyenrangú szakirány megjelenítés")
        print(f"  🎯 Átlátható kártya elrendezés")
        print(f"  🖥️  Intuitív felhasználói élmény")
        print(f"  📱 Reszponzív design minden eszközön")
        print(f"  🎭 Professzionális vizuális hierarchia")
    else:
        print(f"\n⚠️  VANNAK JAVÍTANDÓ ELEMEK!")
        print(f"Néhány UX/UI teszt sikertelen, ellenőrizd a részleteket fent.")
    
    print(f"\n🔗 Tesztelési URL-ek:")
    print(f"  - Enhanced Onboarding: {FRONTEND_URL}/student/semester-onboarding")
    print(f"  - Backend API: {BASE_URL}")
    print(f"  - Status Dashboard: {BASE_URL}/docs")
    
    return passed == total

if __name__ == "__main__":
    success = run_enhanced_ux_ui_tests()
    exit(0 if success else 1)