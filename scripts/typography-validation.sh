#!/bin/bash

echo "🔤 Typography & Readability Validation - 2025 Standards"
echo "======================================================="

# Check for modern typography tokens usage
check_typography_usage() {
    local file_pattern=$1
    local description=$2
    
    echo ""
    echo "📝 $description"
    echo "----------------------------------------"
    
    # Count hardcoded font sizes (bad practice)
    hardcoded_fonts=$(grep -r "font-size:\s*[0-9.]\+\(px\|rem\)" $file_pattern 2>/dev/null | wc -l)
    echo "❌ Hardcoded font-sizes found: $hardcoded_fonts"
    
    # Count design token usage (good practice)
    token_usage=$(grep -r "font-size:\s*var(--text-" $file_pattern 2>/dev/null | wc -l)
    echo "✅ Design token usage: $token_usage"
    
    # Check for minimum font sizes (accessibility)
    small_fonts=$(grep -r "font-size:\s*\(0\.\?[0-7][0-9]*\|[0-9]\|1[01]\)px" $file_pattern 2>/dev/null | wc -l)
    echo "⚠️  Fonts smaller than 12px: $small_fonts"
    
    # Check for line-height usage
    line_height_usage=$(grep -r "line-height:\s*var(--leading-" $file_pattern 2>/dev/null | wc -l)
    echo "✅ Line-height tokens: $line_height_usage"
    
    # Check for letter-spacing usage
    tracking_usage=$(grep -r "letter-spacing:\s*var(--tracking-" $file_pattern 2>/dev/null | wc -l)
    echo "✅ Letter-spacing tokens: $tracking_usage"
}

# Check design system files
echo "1. Design System Core Files"
check_typography_usage "frontend/src/styles/*.css" "Design system files"

echo ""
echo "2. Component Files"
check_typography_usage "frontend/src/components/**/*.css" "Component stylesheets"

echo ""
echo "3. Page Files" 
check_typography_usage "frontend/src/pages/**/*.css" "Page stylesheets"

echo ""
echo "4. Typography Token Availability Check"
echo "----------------------------------------"

# Check if new typography tokens are defined
if grep -q "text-5xl" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Extended type scale (text-5xl) available"
else
    echo "❌ Extended type scale missing"
fi

if grep -q "tracking-tighter" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Letter-spacing tokens available"
else
    echo "❌ Letter-spacing tokens missing"
fi

if grep -q "leading-loose" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Extended line-height scale available"
else
    echo "❌ Extended line-height scale missing"
fi

if grep -q "font-black" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Extended font-weight scale available"
else
    echo "❌ Extended font-weight scale missing"
fi

echo ""
echo "5. Accessibility Compliance Check"
echo "----------------------------------------"

# Check for minimum contrast ratios in accessible themes
purple_contrast=$(grep -A 10 'data-theme="light"\[data-color="purple"\]' frontend/src/styles/accessible-themes.css | grep "text-primary" | head -1)
if echo "$purple_contrast" | grep -q "#2d3748"; then
    echo "✅ Purple theme uses high-contrast text (#2d3748)"
else
    echo "⚠️  Purple theme may have contrast issues"
fi

# Check for Inter font inclusion
if grep -q "Inter" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Modern font stack includes Inter"
else
    echo "⚠️  Consider adding Inter font for better readability"
fi

echo ""
echo "6. 2025 Typography Trend Compliance"
echo "----------------------------------------"

# Check base font size (should be 18px+ for 2025 trends)
if grep -q "text-base.*1.125rem" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Base font size is 18px (2025 standard)"
else
    echo "⚠️  Base font size should be 18px for optimal readability"
fi

# Check minimum small font size (should be 14px+ for accessibility)
if grep -q "text-xs.*0.875rem" "frontend/src/styles/design-tokens.css"; then
    echo "✅ Minimum font size is 14px (accessibility compliant)"
else
    echo "❌ Minimum font size below 14px (accessibility issue)"
fi

echo ""
echo "🎯 TYPOGRAPHY MODERNIZATION SCORE"
echo "================================="

# Calculate scores
total_files=$(find frontend/src -name "*.css" | wc -l)
token_files=$(grep -l "var(--text-" frontend/src/**/*.css 2>/dev/null | wc -l)
modern_percentage=$(( (token_files * 100) / total_files ))

echo "📊 Design Token Adoption: $modern_percentage% ($token_files/$total_files files)"

if [ $modern_percentage -ge 80 ]; then
    echo "🏆 EXCELLENT - Typography system is modern and consistent"
elif [ $modern_percentage -ge 60 ]; then
    echo "🥈 GOOD - Most components use design tokens"  
elif [ $modern_percentage -ge 40 ]; then
    echo "🥉 FAIR - Partial design token adoption"
else
    echo "⚠️  NEEDS IMPROVEMENT - Low design token usage"
fi

echo ""
echo "🏁 Typography Validation Complete"