#!/usr/bin/env python3
"""
WCAG 2.1 Contrast Ratio Analysis Tool
Analyzes the existing theme colors for accessibility compliance
"""

import math


def hex_to_rgb(hex_color):
    """Convert hex color to RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_luminance(rgb):
    """Convert RGB to relative luminance (0-1)"""
    def gamma_correct(component):
        component = component / 255.0
        if component <= 0.03928:
            return component / 12.92
        else:
            return pow((component + 0.055) / 1.055, 2.4)
    
    r, g, b = rgb
    return 0.2126 * gamma_correct(r) + 0.7152 * gamma_correct(g) + 0.0722 * gamma_correct(b)


def contrast_ratio(color1_hex, color2_hex):
    """Calculate contrast ratio between two colors"""
    lum1 = rgb_to_luminance(hex_to_rgb(color1_hex))
    lum2 = rgb_to_luminance(hex_to_rgb(color2_hex))
    
    # Ensure lighter color is numerator
    if lum1 < lum2:
        lum1, lum2 = lum2, lum1
    
    return (lum1 + 0.05) / (lum2 + 0.05)


def wcag_compliance_check(ratio):
    """Check WCAG compliance levels"""
    if ratio >= 7.0:
        return "AAA (Enhanced)", "✅ Excellent"
    elif ratio >= 4.5:
        return "AA (Standard)", "✅ Good"  
    elif ratio >= 3.0:
        return "AA Large Text Only", "⚠️ Limited"
    else:
        return "FAIL", "❌ Poor"


def analyze_theme_colors():
    """Analyze the current theme color combinations"""
    
    print("🎨 WCAG 2.1 Contrast Ratio Analysis for Practice Booking System")
    print("=" * 70)
    
    # Current theme colors from themes.css
    light_theme = {
        "background": "#ffffff",  # bg-card white
        "text_primary": "#1a202c",  # text-primary
        "text_secondary": "#64748b",  # text-secondary  
        "primary": "#667eea",  # color-primary purple
        "secondary": "#764ba2",  # color-secondary purple
        "error": "#e53e3e",  # error-color
        "success": "#2f855a",  # success-color
        "warning": "#d97706",  # warning-color
    }
    
    dark_theme = {
        "background": "#28283c",  # bg-card dark (approx. from rgba(40, 40, 60))
        "text_primary": "#f8f9fa",  # text-primary dark
        "text_secondary": "#adb5bd",  # text-secondary dark
        "primary": "#8b5cf6",  # color-primary dark purple
        "secondary": "#7c3aed",  # color-secondary dark purple
        "error": "#ff6b6b",  # error-color dark
        "success": "#4ade80",  # success-color dark
        "warning": "#fbbf24",  # warning-color dark
    }
    
    print("\n📊 LIGHT THEME ANALYSIS")
    print("-" * 40)
    
    # Test critical combinations for light theme
    light_tests = [
        ("Primary text on background", light_theme["text_primary"], light_theme["background"]),
        ("Secondary text on background", light_theme["text_secondary"], light_theme["background"]),
        ("White text on primary button", "#ffffff", light_theme["primary"]),
        ("White text on secondary button", "#ffffff", light_theme["secondary"]),
        ("White text on success button", "#ffffff", light_theme["success"]),
        ("White text on error button", "#ffffff", light_theme["error"]),
        ("White text on warning button", "#ffffff", light_theme["warning"]),
        ("Primary text on error background", light_theme["text_primary"], "#fee2e2"),  # bg-error light
    ]
    
    for test_name, text_color, bg_color in light_tests:
        ratio = contrast_ratio(text_color, bg_color)
        compliance, status = wcag_compliance_check(ratio)
        print(f"{test_name:35} | {ratio:5.2f}:1 | {compliance:20} | {status}")
    
    print("\n🌙 DARK THEME ANALYSIS")
    print("-" * 40)
    
    # Test critical combinations for dark theme
    dark_tests = [
        ("Primary text on background", dark_theme["text_primary"], dark_theme["background"]),
        ("Secondary text on background", dark_theme["text_secondary"], dark_theme["background"]),
        ("White text on primary button", "#ffffff", dark_theme["primary"]),
        ("White text on secondary button", "#ffffff", dark_theme["secondary"]),
        ("White text on success button", "#ffffff", dark_theme["success"]),
        ("White text on error button", "#ffffff", dark_theme["error"]),
        ("White text on warning button", "#ffffff", dark_theme["warning"]),
        ("Dark text on card background", dark_theme["text_primary"], "#3c3c5c"),  # bg-card-hover approx
    ]
    
    for test_name, text_color, bg_color in dark_tests:
        ratio = contrast_ratio(text_color, bg_color)
        compliance, status = wcag_compliance_check(ratio)
        print(f"{test_name:35} | {ratio:5.2f}:1 | {compliance:20} | {status}")
    
    print("\n🎯 CRITICAL ACCESSIBILITY RECOMMENDATIONS")
    print("=" * 70)
    print("1. WCAG 2.1 AA Standard requires 4.5:1 for normal text")
    print("2. WCAG 2.1 AA Standard requires 3.0:1 for large text (18pt+ or 14pt+ bold)")
    print("3. WCAG 2.1 AAA Enhanced requires 7.0:1 for normal text")
    print("4. Test with actual users who have visual impairments")
    
    print("\n🔧 SPECIFIC IMPROVEMENTS NEEDED:")
    
    # Check specific problem areas
    warning_white_ratio = contrast_ratio("#ffffff", light_theme["warning"])
    if warning_white_ratio < 4.5:
        print(f"⚠️  WARNING: White text on warning background ({warning_white_ratio:.2f}:1) fails AA")
        print("   → Recommendation: Use darker warning color (#b45309) or dark text")
    
    # Check dark theme secondary text
    dark_secondary_ratio = contrast_ratio(dark_theme["text_secondary"], dark_theme["background"])
    if dark_secondary_ratio < 4.5:
        print(f"⚠️  DARK THEME: Secondary text contrast ({dark_secondary_ratio:.2f}:1) may be low")
        print("   → Recommendation: Use lighter secondary text color (#cbd5e1)")
    
    print("\n✅ STRENGTHS OF CURRENT IMPLEMENTATION:")
    print("• Comprehensive theme system with CSS variables")
    print("• Multiple color scheme options")
    print("• Auto theme with system preference detection")
    print("• Consistent color naming convention")


if __name__ == "__main__":
    analyze_theme_colors()