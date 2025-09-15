#!/bin/bash

echo "🔄 Typography Migration Script - 2025 Design Tokens"
echo "==================================================="

# Typography mapping for automatic replacement
declare -A FONT_SIZE_MAP=(
    # 2025 optimized mappings
    ["0.7rem"]="var(--text-xs)"    # 11.2px → 14px (accessibility improvement)
    ["0.75rem"]="var(--text-xs)"   # 12px → 14px (accessibility improvement)
    ["0.8rem"]="var(--text-xs)"    # 12.8px → 14px (accessibility improvement)
    ["0.85rem"]="var(--text-xs)"   # 13.6px → 14px (accessibility improvement)
    ["0.875rem"]="var(--text-xs)"  # 14px → 14px (exact match)
    ["0.9rem"]="var(--text-sm)"    # 14.4px → 16px (improved readability)
    ["0.95rem"]="var(--text-sm)"   # 15.2px → 16px (improved readability)
    ["1rem"]="var(--text-sm)"      # 16px → 16px (kept as small)
    ["1.1rem"]="var(--text-base)"  # 17.6px → 18px (improved readability)
    ["1.125rem"]="var(--text-base)" # 18px → 18px (exact match)
    ["1.2rem"]="var(--text-lg)"    # 19.2px → 20px (better hierarchy)
    ["1.25rem"]="var(--text-lg)"   # 20px → 20px (exact match)
    ["1.3rem"]="var(--text-xl)"    # 20.8px → 22px (enhanced visibility)
    ["1.375rem"]="var(--text-xl)"  # 22px → 22px (exact match)
    ["1.4rem"]="var(--text-xl)"    # 22.4px → 22px (close match)
    ["1.5rem"]="var(--text-2xl)"   # 24px → 26px (improved hierarchy)
    ["1.625rem"]="var(--text-2xl)" # 26px → 26px (exact match)
    ["1.6rem"]="var(--text-2xl)"   # 25.6px → 26px (close match)
    ["1.7rem"]="var(--text-2xl)"   # 27.2px → 26px (close match)
    ["1.8rem"]="var(--text-3xl)"   # 28.8px → 32px (stronger hierarchy)
    ["1.875rem"]="var(--text-3xl)" # 30px → 32px (improved hierarchy)
    ["2rem"]="var(--text-3xl)"     # 32px → 32px (exact match)
    ["2.2rem"]="var(--text-4xl)"   # 35.2px → 40px (stronger impact)
    ["2.25rem"]="var(--text-4xl)"  # 36px → 40px (improved hierarchy)
    ["2.5rem"]="var(--text-4xl)"   # 40px → 40px (exact match)
    ["3rem"]="var(--text-5xl)"     # 48px → 48px (exact match)
)

declare -A FONT_WEIGHT_MAP=(
    ["300"]="var(--font-light)"
    ["400"]="var(--font-normal)"
    ["500"]="var(--font-medium)"
    ["600"]="var(--font-semibold)"
    ["700"]="var(--font-bold)"
    ["800"]="var(--font-extrabold)"
    ["900"]="var(--font-black)"
)

declare -A LINE_HEIGHT_MAP=(
    ["1.2"]="var(--leading-tight)"
    ["1.25"]="var(--leading-tight)"
    ["1.3"]="var(--leading-snug)"
    ["1.375"]="var(--leading-snug)"
    ["1.4"]="var(--leading-normal)"
    ["1.5"]="var(--leading-normal)"
    ["1.6"]="var(--leading-relaxed)"
    ["1.625"]="var(--leading-relaxed)"
    ["1.7"]="var(--leading-loose)"
    ["1.75"]="var(--leading-loose)"
)

# Function to migrate a single file
migrate_file() {
    local file=$1
    local backup_file="${file}.backup"
    
    echo "🔄 Migrating: $file"
    
    # Create backup
    cp "$file" "$backup_file"
    
    # Replace font-size values
    for size in "${!FONT_SIZE_MAP[@]}"; do
        sed -i '' "s/font-size: ${size}/font-size: ${FONT_SIZE_MAP[$size]}/g" "$file"
        sed -i '' "s/font-size:${size}/font-size: ${FONT_SIZE_MAP[$size]}/g" "$file"
    done
    
    # Replace font-weight values
    for weight in "${!FONT_WEIGHT_MAP[@]}"; do
        sed -i '' "s/font-weight: ${weight}/font-weight: ${FONT_WEIGHT_MAP[$weight]}/g" "$file"
        sed -i '' "s/font-weight:${weight}/font-weight: ${FONT_WEIGHT_MAP[$weight]}/g" "$file"
    done
    
    # Replace line-height values
    for height in "${!LINE_HEIGHT_MAP[@]}"; do
        sed -i '' "s/line-height: ${height}/line-height: ${LINE_HEIGHT_MAP[$height]}/g" "$file"
        sed -i '' "s/line-height:${height}/line-height: ${LINE_HEIGHT_MAP[$height]}/g" "$file"
    done
    
    echo "   ✅ Migration complete for $file"
}

# Function to show migration stats
show_stats() {
    local file=$1
    echo "📊 Stats for $file:"
    
    local hardcoded_before=$(grep -c "font-size: [0-9.]\+rem" "${file}.backup" 2>/dev/null || echo "0")
    local hardcoded_after=$(grep -c "font-size: [0-9.]\+rem" "$file" 2>/dev/null || echo "0")
    local tokens_after=$(grep -c "font-size: var(--text-" "$file" 2>/dev/null || echo "0")
    
    echo "   Before: $hardcoded_before hardcoded font-sizes"
    echo "   After:  $hardcoded_after hardcoded, $tokens_after design tokens"
    
    local improvement=$(( hardcoded_before - hardcoded_after ))
    echo "   ✅ Improved: $improvement font-sizes migrated"
    echo ""
}

# Main migration
if [ "$1" = "all" ]; then
    echo "🎯 Migrating ALL component files..."
    
    # Find all CSS files in components and pages
    find frontend/src -name "*.css" -not -path "*/styles/*" | while read file; do
        migrate_file "$file"
        show_stats "$file"
    done
    
elif [ "$1" = "priority" ]; then
    echo "🎯 Migrating PRIORITY files (highest impact)..."
    
    # Priority files with most hardcoded font-sizes
    priority_files=(
        "frontend/src/pages/student/StudentDashboard.css"
        "frontend/src/pages/instructor/InstructorDashboard.css"
        "frontend/src/pages/instructor/InstructorAttendance.css"
        "frontend/src/pages/student/QuizResult.css"
        "frontend/src/pages/instructor/InstructorStudents.css"
        "frontend/src/pages/student/MyProjects.css"
        "frontend/src/pages/student/ProjectProgress.css"
        "frontend/src/pages/instructor/InstructorFeedback.css"
        "frontend/src/pages/student/FeedbackPage.css"
        "frontend/src/pages/instructor/InstructorProjects.css"
    )
    
    for file in "${priority_files[@]}"; do
        if [ -f "$file" ]; then
            migrate_file "$file"
            show_stats "$file"
        else
            echo "⚠️  File not found: $file"
        fi
    done
    
elif [ -n "$1" ]; then
    echo "🎯 Migrating single file: $1"
    if [ -f "$1" ]; then
        migrate_file "$1"
        show_stats "$1"
    else
        echo "❌ File not found: $1"
        exit 1
    fi
else
    echo "❓ Usage:"
    echo "  $0 priority              # Migrate top 10 priority files"
    echo "  $0 all                   # Migrate all component files"
    echo "  $0 path/to/file.css      # Migrate specific file"
    exit 1
fi

echo "🏁 Typography Migration Complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Test visual consistency across themes"
echo "   2. Run: ./scripts/typography-validation.sh"
echo "   3. Check components in browser"
echo "   4. Commit changes if satisfied"