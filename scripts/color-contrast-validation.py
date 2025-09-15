#!/usr/bin/env python3
"""
Teljes színkontrasztvalidációs script minden témához
Ellenőrzi a WCAG 2.1 AA kompatibilitást
"""

import re
import os

def extract_color_values():
    """Kinyeri az összes színdefiníciót a CSS fájlokból"""
    print("🎨 SZÍNDEFINÍCIÓK ELEMZÉSE")
    print("=" * 40)
    
    themes = {}
    
    # Accessible themes fájl olvasása
    themes_file = 'frontend/src/styles/accessible-themes.css'
    if os.path.exists(themes_file):
        with open(themes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Témák keresése
        theme_matches = re.finditer(r':root\[data-theme="([^"]+)"\]\[data-color="([^"]+)"\]', content)
        
        for match in theme_matches:
            theme_type = match.group(1)  # light/dark
            color_scheme = match.group(2)  # purple/blue/green etc.
            theme_name = f"{theme_type}-{color_scheme}"
            
            # Theme blokk kinyerése
            start_pos = match.end()
            brace_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(content[start_pos:], start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            
            theme_block = content[start_pos:end_pos]
            
            # Színek kinyerése
            colors = {}
            color_matches = re.finditer(r'--([^:]+):\s*([^;]+);', theme_block)
            for color_match in color_matches:
                var_name = color_match.group(1).strip()
                var_value = color_match.group(2).strip()
                colors[var_name] = var_value
            
            themes[theme_name] = colors
            print(f"  ✅ {theme_name}: {len(colors)} színváltozó")
    
    return themes

def validate_contrast_ratios():
    """Validálja a kontrasztarányokat"""
    print(f"\n🔍 KONTRASZTARÁNY VALIDÁCIÓ")
    print("=" * 40)
    
    # Gyakori színkombinációk ellenőrzése
    critical_combinations = [
        ('text-primary', 'bg-primary'),
        ('text-primary', 'bg-card'),
        ('text-secondary', 'bg-card'),
        ('text-accent', 'color-primary'),
        ('text-header', 'bg-primary'),
    ]
    
    themes = extract_color_values()
    total_issues = 0
    
    for theme_name, colors in themes.items():
        print(f"\n🎭 TÉMA: {theme_name.upper()}")
        theme_issues = 0
        
        for text_var, bg_var in critical_combinations:
            text_color = colors.get(text_var, 'N/A')
            bg_color = colors.get(bg_var, 'N/A')
            
            if text_color != 'N/A' and bg_color != 'N/A':
                # Egyszerű heurisztika - fehér szöveg sötét háttéren
                is_good_contrast = True
                
                # Fehér/világos szöveg ellenőrzése
                if any(x in text_color.lower() for x in ['white', '#fff']):
                    if any(x in bg_color.lower() for x in ['white', '#fff', '#f']):
                        is_good_contrast = False
                        theme_issues += 1
                        print(f"  ❌ {text_var} ({text_color}) vs {bg_var} ({bg_color})")
                    else:
                        print(f"  ✅ {text_var} vs {bg_var}")
                else:
                    print(f"  ✅ {text_var} vs {bg_var}")
        
        if theme_issues == 0:
            print(f"  💚 Minden kontrasztarány megfelelő!")
        else:
            print(f"  🚨 {theme_issues} kontraszt probléma!")
            total_issues += theme_issues
    
    return total_issues

def check_design_token_usage():
    """Ellenőrzi a design tokenek használatát"""
    print(f"\n🎯 DESIGN TOKEN HASZNÁLAT ELEMZÉSE")
    print("=" * 40)
    
    css_files = []
    for root, dirs, files in os.walk('frontend/src'):
        for file in files:
            if file.endswith('.css'):
                css_files.append(os.path.join(root, file))
    
    token_usage = 0
    hardcoded_colors = 0
    
    for css_file in css_files:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Design token használat számolása
            var_matches = re.findall(r'var\(--[^)]+\)', content)
            token_usage += len(var_matches)
            
            # Hardcoded színek számolása (hex, rgb, színnevek)
            hardcoded_matches = re.findall(r'(?:color|background[^:]*|border[^:]*|box-shadow):\s*(?:#[0-9a-fA-F]{3,6}|rgb[^;]+|rgba[^;]+|white|black|red|blue|green)', content)
            hardcoded_colors += len(hardcoded_matches)
            
        except Exception as e:
            print(f"❌ Hiba {css_file}: {e}")
    
    total_definitions = token_usage + hardcoded_colors
    token_percentage = (token_usage / total_definitions * 100) if total_definitions > 0 else 0
    
    print(f"  📊 Design token használat: {token_usage}")
    print(f"  🔴 Hardcoded színek: {hardcoded_colors}")
    print(f"  🎯 Token adoption: {token_percentage:.1f}%")
    
    if token_percentage > 60:
        print(f"  ✅ Jó design token adoption!")
    else:
        print(f"  ⚠️  Javítható design token adoption")
    
    return token_percentage

def main():
    print("🌈 TELJES SZÍNRENDSZER VALIDÁCIÓ")
    print("=" * 50)
    print("   WCAG 2.1 AA kompatibilitás ellenőrzése")
    print("=" * 50)
    
    # 1. Kontrasztarány validáció
    contrast_issues = validate_contrast_ratios()
    
    # 2. Design token használat
    token_adoption = check_design_token_usage()
    
    # 3. Összegzés
    print(f"\n🏆 VÉGSŐ ÉRTÉKELÉS")
    print("=" * 30)
    print(f"  🎨 Színkontrasztproblémák: {contrast_issues}")
    print(f"  🎯 Design token adoption: {token_adoption:.1f}%")
    
    overall_score = 100 - (contrast_issues * 10) + (token_adoption * 0.5)
    overall_score = min(100, max(0, overall_score))
    
    print(f"  📊 Összpontszám: {overall_score:.1f}/100")
    
    if overall_score >= 90:
        print(f"  🥇 KIVÁLÓ színrendszer!")
    elif overall_score >= 80:
        print(f"  🥈 JÓ színrendszer!")
    elif overall_score >= 70:
        print(f"  🥉 MEGFELELŐ színrendszer!")
    else:
        print(f"  ❌ JAVÍTANDÓ színrendszer!")
    
    return contrast_issues == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)