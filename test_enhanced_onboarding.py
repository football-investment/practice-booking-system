#!/usr/bin/env python3
"""
Enhanced Onboarding Test Script
=====================================

Ez a script teszteli az onboarding folyamat javításait:
1. Automatikusan betöltött adatok reszponzív megjelenítése
2. Track szint és aktuális állapot egyértelmű megjelenítése

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
    print(f"🧪 {test_name}")
    print(f"{'='*60}")

def print_success(message):
    """Sikeres teszt üzenet"""
    print(f"✅ {message}")

def print_error(message):
    """Hiba üzenet"""
    print(f"❌ {message}")

def test_backend_health():
    """Teszteli a backend működését"""
    print_test_header("Backend Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/debug/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend működik és elérhető")
            return True
        else:
            print_error(f"Backend nem válaszol megfelelően: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Backend nem elérhető: {e}")
        return False

def test_auto_data_service():
    """Teszteli az automatikus adatbetöltési szolgáltatást"""
    print_test_header("Auto Data Service Test")
    
    try:
        # Teszteljük az auto-data endpoint-ot
        response = requests.get(f"{BASE_URL}/api/v1/users/1/auto-data", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Auto data service működik")
            
            # Ellenőrizzük az adatstruktúrát
            expected_fields = [
                'nickname', 'phone', 'date_of_birth', 
                'emergency_contact', 'emergency_phone', 'medical_notes'
            ]
            
            for field in expected_fields:
                if field in data:
                    print_success(f"  - {field}: ✓")
                else:
                    print_error(f"  - {field}: hiányzik")
            
            return True
        else:
            print_error(f"Auto data service hiba: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Auto data service teszt sikertelen: {e}")
        return False

def test_specialization_dashboard():
    """Teszteli a specializáció dashboard funkcionalitást"""
    print_test_header("Specialization Dashboard Test")
    
    try:
        # Teszteljük a parallel specializations dashboard-ot
        response = requests.get(f"{BASE_URL}/api/v1/parallel-specializations/dashboard", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Specialization dashboard működik")
            
            # Ellenőrizzük az enhanced track információkat
            if 'active_specializations' in data:
                print_success("  - Active specializations: ✓")
                
                for spec in data.get('active_specializations', []):
                    if 'current_level' in spec and 'max_achieved_level' in spec:
                        print_success(f"    - {spec.get('specialization_type', 'N/A')}: Level {spec['current_level']}/{spec['max_achieved_level']}")
                    else:
                        print_error(f"    - {spec.get('specialization_type', 'N/A')}: hiányzó level adatok")
            
            if 'current_semester' in data:
                print_success(f"  - Current semester: {data['current_semester']}")
            
            return True
        else:
            print_error(f"Specialization dashboard hiba: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Specialization dashboard teszt sikertelen: {e}")
        return False

def test_frontend_accessibility():
    """Teszteli a frontend elérhetőségét"""
    print_test_header("Frontend Accessibility Test")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print_success("Frontend elérhető és működik")
            return True
        else:
            print_error(f"Frontend nem válaszol megfelelően: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Frontend nem elérhető: {e}")
        return False

def test_css_enhancements():
    """Teszteli a CSS fejlesztések betöltését"""
    print_test_header("CSS Enhancements Test")
    
    # CSS fájlok ellenőrzése
    css_files = [
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/pages/student/SemesterCentricOnboarding.css",
        "/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Invetsment - Internship/practice_booking_system/frontend/src/components/onboarding/CurrentSpecializationStatus.css"
    ]
    
    enhanced_classes = [
        'auto-data-preview',
        'enhanced-level-display', 
        'level-badge-container',
        'current-level-badge',
        'visual-progress-container',
        'track-details'
    ]
    
    all_found = True
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for class_name in enhanced_classes:
                if f'.{class_name}' in content:
                    print_success(f"  - {class_name}: ✓")
                else:
                    print_error(f"  - {class_name}: hiányzik")
                    all_found = False
                    
        except Exception as e:
            print_error(f"CSS fájl olvasási hiba ({css_file}): {e}")
            all_found = False
    
    return all_found

def run_all_tests():
    """Futtatja az összes tesztet"""
    print(f"""
🎯 Enhanced Onboarding Test Suite
==================================
Időpont: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Ez a teszt suite ellenőrzi az onboarding folyamat javításait:
1. ✨ Automatikusan betöltött adatok reszponzív megjelenítése
2. 🎯 Track szint és aktuális állapot egyértelmű megjelenítése
""")
    
    tests = [
        test_backend_health,
        test_frontend_accessibility,
        test_auto_data_service,
        test_specialization_dashboard,
        test_css_enhancements
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
    print(f"📊 TESZT ÖSSZEGZÉS")
    print(f"{'='*60}")
    print(f"✅ Sikeres tesztek: {passed}/{total}")
    print(f"❌ Sikertelen tesztek: {total - passed}/{total}")
    
    if passed == total:
        print(f"\n🎉 MINDEN TESZT SIKERES!")
        print(f"Az onboarding folyamat javításai megfelelően működnek.")
    else:
        print(f"\n⚠️  VAN HIBA!")
        print(f"Néhány teszt sikertelen, ellenőrizd a részleteket fent.")
    
    print(f"\n🔗 Tesztelési URL-ek:")
    print(f"  - Backend: {BASE_URL}")
    print(f"  - Frontend: {FRONTEND_URL}")
    print(f"  - Onboarding: {FRONTEND_URL}/student/semester-onboarding")

if __name__ == "__main__":
    run_all_tests()