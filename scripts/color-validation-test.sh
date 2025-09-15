#!/bin/bash

echo "🎨 Color Palette Validation"
echo "=========================="

# Check exact color matches
check_color() {
    local file=$1
    local expected_color=$2
    local color_name=$3
    
    if grep -q "$expected_color" "$file"; then
        echo "✅ $color_name: $expected_color found in $file"
    else
        echo "❌ $color_name: $expected_color NOT found in $file"
        echo "   Searching for similar colors:"
        grep -n "#[0-9A-Fa-f]" "$file" | grep -i "$color_name" | head -3
    fi
}

echo "1. Testing Brand Purple Colors..."
check_color "frontend/src/styles/design-tokens.css" "#8B5FBF" "brand-purple-500"
check_color "frontend/src/styles/design-tokens.css" "#6A4C93" "brand-purple-600"

echo ""
echo "2. Testing Semantic Colors..."
check_color "frontend/src/styles/design-tokens.css" "#00D25B" "color-success (Bio Green)"
check_color "frontend/src/styles/design-tokens.css" "#FF9500" "color-warning (Energy Orange)"
check_color "frontend/src/styles/design-tokens.css" "#FF3B30" "color-error (iOS Red)"
check_color "frontend/src/styles/design-tokens.css" "#0084FF" "color-info (Trust Blue)"

echo ""
echo "3. Testing Theme Colors..."
check_color "frontend/src/styles/themes.css" "#0084FF" "blue theme primary"
check_color "frontend/src/styles/themes.css" "#00D25B" "green theme primary"
check_color "frontend/src/styles/themes.css" "#FF3B30" "red theme primary"
check_color "frontend/src/styles/themes.css" "#FF9500" "orange theme primary"

echo ""
echo "4. Testing 2025 New Themes..."
check_color "frontend/src/styles/themes.css" "#00FF88" "cyber sports primary"
check_color "frontend/src/styles/themes.css" "#FF10F0" "cyber sports secondary"
check_color "frontend/src/styles/themes.css" "#40E0D0" "ocean breeze secondary"
check_color "frontend/src/styles/themes.css" "#FF6B35" "sunset athletic primary"

echo ""
echo "5. Testing Accessible Themes Override..."
accessible_purple=$(grep -A 10 '\[data-theme="light"\]\[data-color="purple"\]' frontend/src/styles/accessible-themes.css | grep -- "--color-primary" | head -1)
if echo "$accessible_purple" | grep -q "#8B5FBF"; then
    echo "✅ Accessible themes use correct purple: #8B5FBF"
else
    echo "❌ Accessible themes NOT using correct purple"
    echo "   Found: $accessible_purple"
fi

echo ""
echo "6. Testing All Accessible Themes Colors..."
check_color "frontend/src/styles/accessible-themes.css" "#8B5FBF" "accessible purple theme"
check_color "frontend/src/styles/accessible-themes.css" "#0084FF" "accessible blue theme"
check_color "frontend/src/styles/accessible-themes.css" "#00D25B" "accessible green theme"
check_color "frontend/src/styles/accessible-themes.css" "#FF3B30" "accessible red theme"
check_color "frontend/src/styles/accessible-themes.css" "#FF9500" "accessible orange theme"

echo ""
echo "7. Testing NEW 2025 Themes in Accessible CSS..."
check_color "frontend/src/styles/accessible-themes.css" "#00FF88" "cyber sports theme"
check_color "frontend/src/styles/accessible-themes.css" "#FF10F0" "cyber pink secondary"
check_color "frontend/src/styles/accessible-themes.css" "#40E0D0" "ocean turquoise"
check_color "frontend/src/styles/accessible-themes.css" "#FF6B35" "sunset orange"

echo ""
echo "8. Checking Theme Picker UI Components..."
if grep -q "cyber" "frontend/src/contexts/ThemeContext.js"; then
    echo "✅ ThemeContext includes new color schemes"
else
    echo "❌ ThemeContext missing new color schemes"
fi

if grep -q "Cyber Sports" "frontend/src/components/common/AppHeader.js"; then
    echo "✅ AppHeader includes new theme UI"
else
    echo "❌ AppHeader missing new theme UI"
fi

echo ""
echo "🏁 Color Validation Complete"