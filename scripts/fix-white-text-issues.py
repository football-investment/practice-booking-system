#!/usr/bin/env python3
"""
Kritikus betűszín kontraszthiba javító script
Javítja a fehér szöveg/fehér háttér problémákat
"""

import re
import os

# Problémás fájlok és sorok
FIXES = {
    'frontend/src/pages/admin/ProjectManagement.css': [
        (220, r'color: white;', 'background: var(--color-primary, #8B5FBF);  /* HOZZÁADVA: háttér */\n  color: var(--text-accent, white);           /* JAVÍTVA: design token */')
    ],
    'frontend/src/pages/instructor/InstructorProjectDetails.css': [
        (247, r'color: white;', 'background: var(--color-primary, #8B5FBF);  /* HOZZÁADVA: háttér */\n  color: var(--text-accent, white);           /* JAVÍTVA: design token */')
    ],
    'frontend/src/pages/instructor/InstructorStudentProgress.css': [
        (224, r'color: white;', 'background: var(--color-primary, #8B5FBF);  /* HOZZÁADVA: háttér */\n  color: var(--text-accent, white);           /* JAVÍTVA: design token */')
    ],
    'frontend/src/pages/instructor/InstructorProgressReport.css': [
        (345, r'color: white;', 'background: var(--color-primary, #8B5FBF);  /* HOZZÁADVA: háttér */\n  color: var(--text-accent, white);           /* JAVÍTVA: design token */')
    ],
    'frontend/src/pages/instructor/InstructorDashboard.css': [
        (364, r'color: white;', 'background: var(--color-primary, #8B5FBF);  /* HOZZÁADVA: háttér */\n  color: var(--text-accent, white);           /* JAVÍTVA: design token */')
    ]
}

def fix_file(filepath, fixes):
    """Egy fájl javítása"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        changes_made = 0
        for line_num, old_pattern, new_text in fixes:
            if line_num <= len(lines):
                line_index = line_num - 1
                old_line = lines[line_index]
                
                # Ellenőrzi, hogy a sor tartalmazza-e a problémás mintát
                if re.search(old_pattern, old_line):
                    # Megtartja az indentációt
                    indent = re.match(r'^(\s*)', old_line).group(1)
                    
                    # Lecseréli a sort
                    lines[line_index] = f"{indent}{new_text}\n"
                    changes_made += 1
                    print(f"  ✅ Javítva {line_num}. sor: {old_line.strip()} -> {new_text}")
        
        if changes_made > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"  📁 {filepath}: {changes_made} változtatás mentve")
        
        return changes_made
    
    except Exception as e:
        print(f"  ❌ Hiba {filepath}: {e}")
        return 0

def main():
    print("🔧 KRITIKUS BETŰSZÍN PROBLÉMÁK JAVÍTÁSA")
    print("=" * 50)
    
    total_fixes = 0
    
    for filepath, file_fixes in FIXES.items():
        print(f"\n📁 Javítás: {filepath}")
        if os.path.exists(filepath):
            fixes_made = fix_file(filepath, file_fixes)
            total_fixes += fixes_made
        else:
            print(f"  ⚠️  Fájl nem található: {filepath}")
    
    print(f"\n🎯 ÖSSZEGZÉS:")
    print(f"   📊 Javított fájlok: {len(FIXES)}")
    print(f"   🔧 Összes javítás: {total_fixes}")
    
    if total_fixes > 0:
        print(f"\n✅ SIKERES! Minden kritikus kontrasztprobléma javítva!")
        print(f"   🌟 Most már minden szöveg olvasható lesz!")
    else:
        print(f"\n❌ Nem sikerült javítani a problémákat")

if __name__ == "__main__":
    main()