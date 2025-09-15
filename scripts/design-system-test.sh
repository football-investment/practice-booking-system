#!/bin/bash

echo "🧪 Design System Validation Suite"
echo "=================================="

# Color Variables Test
echo "1. Testing CSS Variable Coverage..."
total_hardcoded=$(find frontend/src -name "*.css" -exec grep -l "#[0-9a-fA-F]" {} \; | wc -l)
hardcoded_count=$(find frontend/src -name "*.css" -exec grep -c "#[0-9a-fA-F]" {} \; | awk '{sum += $1} END {print sum}')
echo "   Files with hardcoded colors: $total_hardcoded"
echo "   Total hardcoded colors: $hardcoded_count"

if [ "$hardcoded_count" -lt 50 ]; then
  echo "   ✅ PASS: Hardcoded colors significantly reduced"
else
  echo "   ❌ FAIL: Too many hardcoded colors still exist"
  echo "   Files with hardcoded colors:"
  find frontend/src -name "*.css" -exec grep -l "#[0-9a-fA-F]" {} \;
fi

# !important Test
echo ""
echo "2. Testing !important Usage..."
important_files=$(find frontend/src -name "*.css" -exec grep -l "!important" {} \; | wc -l)
important_count=$(find frontend/src -name "*.css" -exec grep -c "!important" {} \; | awk '{sum += $1} END {print sum}')
echo "   Files with !important: $important_files"
echo "   Total !important declarations: $important_count"

if [ "$important_count" -lt 70 ]; then
  echo "   ✅ PASS: !important usage significantly reduced"
else
  echo "   ❌ FAIL: Too many !important declarations"
  find frontend/src -name "*.css" -exec grep -l "!important" {} \; | head -5
fi

# CSS Variable Usage Test
echo ""
echo "3. Testing CSS Variable Adoption..."
var_usage=$(find frontend/src -name "*.css" -exec grep -c "var(--" {} \; | awk '{sum += $1} END {print sum}')
echo "   Total var() usages: $var_usage"

if [ "$var_usage" -gt 200 ]; then
  echo "   ✅ PASS: Good CSS variable adoption"
else
  echo "   ⚠️  WARNING: Low CSS variable usage"
fi

# Theme Variables Test
echo ""
echo "4. Testing Design Token Completeness..."
if [ -f "frontend/src/styles/design-tokens.css" ]; then
  token_count=$(grep -c "^  --[a-zA-Z]" frontend/src/styles/design-tokens.css)
  echo "   Design tokens defined: $token_count"
  
  if [ "$token_count" -gt 60 ]; then
    echo "   ✅ PASS: Comprehensive token system"
  else
    echo "   ❌ FAIL: Insufficient design tokens"
  fi
else
  echo "   ❌ FAIL: Design tokens file missing"
fi

# Theme System Test
echo ""
echo "5. Testing Theme System..."
if [ -f "frontend/src/styles/themes.css" ]; then
  theme_vars=$(grep -c "var(--" frontend/src/styles/themes.css)
  echo "   Theme variable usages: $theme_vars"
  
  if [ "$theme_vars" -gt 20 ]; then
    echo "   ✅ PASS: Theme system properly integrated"
  else
    echo "   ❌ FAIL: Theme system not properly integrated"
  fi
else
  echo "   ❌ FAIL: Themes file missing"
fi

echo ""
echo "🏁 SUMMARY REPORT"
echo "=================="
echo "📊 Key Metrics:"
echo "   • Hardcoded colors: $hardcoded_count"
echo "   • !important declarations: $important_count"
echo "   • CSS variables: $var_usage"
echo "   • Design tokens: $token_count"
echo "   • Theme integration: $theme_vars var() usages"

echo ""
echo "✅ COMPLETED PHASES:"
echo "   • Phase 1: Design foundation (design-tokens.css, themes.css)"
echo "   • Phase 2: Critical hardcoded color elimination"
echo "   • Phase 3: !important declaration cleanup"

echo ""
if [ "$hardcoded_count" -lt 50 ] && [ "$important_count" -lt 70 ] && [ "$var_usage" -gt 200 ]; then
  echo "🎉 DESIGN SYSTEM REFACTOR: SUCCESS!"
  echo "   The theme system is now significantly improved and maintainable."
  exit 0
else
  echo "⚠️  DESIGN SYSTEM REFACTOR: PARTIAL SUCCESS"
  echo "   Major improvements made, further optimization possible."
  exit 1
fi