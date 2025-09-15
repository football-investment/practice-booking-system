#!/usr/bin/env python3
"""
Theme Consistency Audit Tool
Analyzes all React pages for theme implementation consistency
"""

import os
import re
import json
from pathlib import Path


def find_react_pages():
    """Find all React page components"""
    pages_dir = Path("frontend/src/pages")
    react_files = []
    
    for root, dirs, files in os.walk(pages_dir):
        for file in files:
            if file.endswith('.js') or file.endswith('.jsx'):
                react_files.append(os.path.join(root, file))
    
    return react_files


def analyze_theme_implementation(file_path):
    """Analyze a single file for theme implementation"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analysis = {
            'file': file_path.replace('frontend/src/', ''),
            'has_theme_state': False,
            'has_color_scheme_state': False,
            'has_theme_effect': False,
            'has_theme_ui': False,
            'theme_patterns': [],
            'issues': []
        }
        
        # Check for theme state (more flexible patterns)
        if re.search(r'useState.*theme|theme.*useState|\[theme,', content, re.IGNORECASE):
            analysis['has_theme_state'] = True
            analysis['theme_patterns'].append('useState theme')
            
        if re.search(r'useState.*colorScheme|colorScheme.*useState|\[colorScheme,', content, re.IGNORECASE):
            analysis['has_color_scheme_state'] = True
            analysis['theme_patterns'].append('useState colorScheme')
        
        # Check for theme useEffect (look for theme logic inside useEffect)
        if re.search(r'useEffect.*\[.*theme.*\]|\[.*theme.*\].*useEffect|data-theme.*=|setAttribute.*theme', content, re.IGNORECASE):
            analysis['has_theme_effect'] = True
            analysis['theme_patterns'].append('useEffect theme')
            
        # Check for theme UI elements
        theme_ui_patterns = [
            r'setTheme',
            r'setColorScheme', 
            r'data-theme',
            r'data-color',
            r'theme.*button|button.*theme',
            r'theme.*toggle|toggle.*theme'
        ]
        
        for pattern in theme_ui_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis['has_theme_ui'] = True
                analysis['theme_patterns'].append(f'UI: {pattern}')
                break
        
        # Identify potential issues
        if analysis['has_theme_state'] and not analysis['has_theme_effect']:
            analysis['issues'].append('Has theme state but no useEffect to apply it')
            
        if analysis['has_theme_state'] and not analysis['has_theme_ui']:
            analysis['issues'].append('Has theme state but no UI to control it')
            
        # Check for duplicate theme logic
        theme_count = len([p for p in analysis['theme_patterns'] if 'useState theme' in p])
        if theme_count > 1:
            analysis['issues'].append('Multiple theme state declarations')
            
        return analysis
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'has_theme_state': False,
            'has_color_scheme_state': False,
            'has_theme_effect': False,
            'has_theme_ui': False,
            'theme_patterns': [],
            'issues': ['Could not analyze file']
        }


def categorize_by_role(file_path):
    """Categorize page by user role"""
    if '/student/' in file_path:
        return 'Student'
    elif '/instructor/' in file_path:
        return 'Instructor'
    elif '/admin/' in file_path:
        return 'Administrator'
    else:
        return 'Common'


def generate_audit_report():
    """Generate comprehensive theme audit report"""
    print("🎨 THEME CONSISTENCY AUDIT - Practice Booking System")
    print("=" * 70)
    
    react_files = find_react_pages()
    results = []
    
    for file_path in react_files:
        analysis = analyze_theme_implementation(file_path)
        analysis['role'] = categorize_by_role(file_path)
        results.append(analysis)
    
    # Organize by role
    roles = {'Student': [], 'Instructor': [], 'Administrator': [], 'Common': []}
    for result in results:
        roles[result['role']].append(result)
    
    # Generate report by role
    for role_name, role_files in roles.items():
        if not role_files:
            continue
            
        print(f"\n📋 {role_name.upper()} PAGES ANALYSIS")
        print("-" * 50)
        
        theme_pages = 0
        non_theme_pages = 0
        issues_count = 0
        
        for analysis in role_files:
            status = "✅" if analysis['has_theme_state'] else "❌"
            issues_str = f" ⚠️ {len(analysis['issues'])} issues" if analysis['issues'] else ""
            
            print(f"{status} {analysis['file']:<40} {issues_str}")
            
            if analysis['has_theme_state']:
                theme_pages += 1
            else:
                non_theme_pages += 1
                
            issues_count += len(analysis['issues'])
            
            # Show issues if any
            for issue in analysis['issues']:
                print(f"     • {issue}")
        
        print(f"\nSUMMARY: {theme_pages} with themes, {non_theme_pages} without, {issues_count} total issues")
    
    # Overall analysis
    print(f"\n🔍 OVERALL ANALYSIS")
    print("=" * 50)
    
    total_files = len(results)
    theme_files = len([r for r in results if r['has_theme_state']])
    no_theme_files = len([r for r in results if not r['has_theme_state']])
    total_issues = sum(len(r['issues']) for r in results)
    
    print(f"📊 Total Pages: {total_files}")
    print(f"✅ With Theme Support: {theme_files} ({theme_files/total_files*100:.1f}%)")
    print(f"❌ Without Theme Support: {no_theme_files} ({no_theme_files/total_files*100:.1f}%)")
    print(f"⚠️  Total Issues Found: {total_issues}")
    
    # Consistency check
    print(f"\n🎯 CONSISTENCY ISSUES")
    print("-" * 30)
    
    if no_theme_files > 0:
        print(f"❌ CRITICAL: {no_theme_files} pages lack theme support")
        print("   → Users cannot change themes on these pages")
    
    duplicate_logic_files = [r for r in results if 'Multiple theme state declarations' in r.get('issues', [])]
    if duplicate_logic_files:
        print(f"⚠️  WARNING: {len(duplicate_logic_files)} pages have duplicate theme logic")
        print("   → Should use centralized theme context")
    
    incomplete_files = [r for r in results if r['has_theme_state'] and not r['has_theme_ui']]
    if incomplete_files:
        print(f"⚠️  WARNING: {len(incomplete_files)} pages have theme state but no UI controls")
        print("   → Users cannot change themes even though supported")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 30)
    print("1. Create centralized ThemeContext to eliminate code duplication")
    print("2. Add theme support to pages that currently lack it")
    print("3. Ensure all theme-capable pages have UI controls")
    print("4. Implement consistent theme switcher component")
    
    # Save detailed results
    with open('theme_audit_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: theme_audit_results.json")


if __name__ == "__main__":
    if not os.path.exists("frontend/src/pages"):
        print("❌ Error: frontend/src/pages directory not found")
        print("Please run this script from the project root directory")
        exit(1)
    
    generate_audit_report()