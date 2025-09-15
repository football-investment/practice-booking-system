#!/usr/bin/env python3
"""
Typography Migration Script - 2025 Design Tokens
Converts hardcoded font-sizes to design tokens in CSS files
"""

import re
import glob
import os
from typing import Dict, List, Tuple

# Font size mapping for modern accessibility and readability
FONT_SIZE_MAPPINGS = {
    # Small sizes (12-14px) → Accessibility minimum (14px)
    '0.7rem': 'var(--text-xs)',    # 11.2px → 14px
    '0.75rem': 'var(--text-xs)',   # 12px → 14px  
    '0.8rem': 'var(--text-xs)',    # 12.8px → 14px
    '0.85rem': 'var(--text-xs)',   # 13.6px → 14px
    '0.875rem': 'var(--text-xs)',  # 14px → 14px
    
    # Medium-small sizes (15-16px) → Standard small (16px)
    '0.9rem': 'var(--text-sm)',    # 14.4px → 16px
    '0.95rem': 'var(--text-sm)',   # 15.2px → 16px
    '1rem': 'var(--text-sm)',      # 16px → 16px
    
    # Body sizes (17-18px) → Enhanced readability (18px)
    '1.1rem': 'var(--text-base)',  # 17.6px → 18px
    '1.125rem': 'var(--text-base)', # 18px → 18px
    
    # Comfortable reading (19-20px) → 20px
    '1.2rem': 'var(--text-lg)',    # 19.2px → 20px
    '1.25rem': 'var(--text-lg)',   # 20px → 20px
    
    # Enhanced visibility (21-22px) → 22px
    '1.3rem': 'var(--text-xl)',    # 20.8px → 22px
    '1.375rem': 'var(--text-xl)',  # 22px → 22px
    '1.4rem': 'var(--text-xl)',    # 22.4px → 22px
    
    # Improved hierarchy (24-26px) → 26px
    '1.5rem': 'var(--text-2xl)',   # 24px → 26px
    '1.625rem': 'var(--text-2xl)', # 26px → 26px
    '1.6rem': 'var(--text-2xl)',   # 25.6px → 26px
    '1.7rem': 'var(--text-2xl)',   # 27.2px → 26px
    
    # Strong hierarchy (28-32px) → 32px
    '1.8rem': 'var(--text-3xl)',   # 28.8px → 32px
    '1.875rem': 'var(--text-3xl)', # 30px → 32px
    '2rem': 'var(--text-3xl)',     # 32px → 32px
    
    # Impact sizes (35-40px) → 40px
    '2.2rem': 'var(--text-4xl)',   # 35.2px → 40px
    '2.25rem': 'var(--text-4xl)',  # 36px → 40px
    '2.5rem': 'var(--text-4xl)',   # 40px → 40px
    
    # Display sizes (48px+) → 48px
    '3rem': 'var(--text-5xl)',     # 48px → 48px
}

FONT_WEIGHT_MAPPINGS = {
    '300': 'var(--font-light)',
    '400': 'var(--font-normal)', 
    '500': 'var(--font-medium)',
    '600': 'var(--font-semibold)',
    '700': 'var(--font-bold)',
    '800': 'var(--font-extrabold)',
    '900': 'var(--font-black)',
}

LINE_HEIGHT_MAPPINGS = {
    '1.2': 'var(--leading-tight)',
    '1.25': 'var(--leading-tight)',
    '1.3': 'var(--leading-snug)',
    '1.375': 'var(--leading-snug)',
    '1.4': 'var(--leading-normal)',
    '1.5': 'var(--leading-normal)',
    '1.6': 'var(--leading-relaxed)',
    '1.625': 'var(--leading-relaxed)',
    '1.7': 'var(--leading-loose)',
    '1.75': 'var(--leading-loose)',
}

def migrate_typography_in_content(content: str) -> Tuple[str, int]:
    """Migrate typography in CSS content"""
    changes = 0
    
    # Replace font-size
    for old_size, new_token in FONT_SIZE_MAPPINGS.items():
        patterns = [
            f'font-size: {old_size}',
            f'font-size:{old_size}',
        ]
        for pattern in patterns:
            if pattern in content:
                content = content.replace(pattern, f'font-size: {new_token}')
                changes += 1
    
    # Replace font-weight
    for old_weight, new_token in FONT_WEIGHT_MAPPINGS.items():
        patterns = [
            f'font-weight: {old_weight}',
            f'font-weight:{old_weight}',
        ]
        for pattern in patterns:
            if pattern in content:
                content = content.replace(pattern, f'font-weight: {new_token}')
                changes += 1
                
    # Replace line-height
    for old_height, new_token in LINE_HEIGHT_MAPPINGS.items():
        patterns = [
            f'line-height: {old_height}',
            f'line-height:{old_height}',
        ]
        for pattern in patterns:
            if pattern in content:
                content = content.replace(pattern, f'line-height: {new_token}')
                changes += 1
    
    return content, changes

def migrate_file(file_path: str) -> dict:
    """Migrate a single CSS file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Count original hardcoded values
        original_font_sizes = len(re.findall(r'font-size:\s*[0-9.]+rem', original_content))
        original_weights = len(re.findall(r'font-weight:\s*[0-9]+', original_content))
        original_heights = len(re.findall(r'line-height:\s*[0-9.]+', original_content))
        
        # Migrate content
        new_content, changes = migrate_typography_in_content(original_content)
        
        # Count new token usage
        new_font_tokens = len(re.findall(r'font-size:\s*var\(--text-', new_content))
        new_weight_tokens = len(re.findall(r'font-weight:\s*var\(--font-', new_content))
        new_height_tokens = len(re.findall(r'line-height:\s*var\(--leading-', new_content))
        
        # Count remaining hardcoded
        remaining_font_sizes = len(re.findall(r'font-size:\s*[0-9.]+rem', new_content))
        remaining_weights = len(re.findall(r'font-weight:\s*[0-9]+', new_content))
        remaining_heights = len(re.findall(r'line-height:\s*[0-9.]+', new_content))
        
        # Write back if changes were made
        if changes > 0:
            # Create backup
            backup_path = f"{file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        
        return {
            'file': file_path,
            'changes': changes,
            'original': {
                'font_sizes': original_font_sizes,
                'weights': original_weights, 
                'heights': original_heights,
            },
            'migrated': {
                'font_tokens': new_font_tokens,
                'weight_tokens': new_weight_tokens,
                'height_tokens': new_height_tokens,
            },
            'remaining': {
                'font_sizes': remaining_font_sizes,
                'weights': remaining_weights,
                'heights': remaining_heights,
            }
        }
        
    except Exception as e:
        return {
            'file': file_path,
            'error': str(e),
            'changes': 0
        }

def main():
    import sys
    print("🔄 Typography Migration Script - 2025 Design Tokens")
    print("=" * 55)
    
    # Default priority files (already migrated)
    default_files = [
        'frontend/src/pages/student/StudentDashboard.css',
        'frontend/src/pages/instructor/InstructorDashboard.css', 
        'frontend/src/pages/instructor/InstructorAttendance.css',
        'frontend/src/pages/student/QuizResult.css',
        'frontend/src/pages/instructor/InstructorStudents.css'
    ]
    
    # Check for command line arguments to process additional files
    if len(sys.argv) > 1 and '--files' in sys.argv:
        files_index = sys.argv.index('--files') + 1
        if files_index < len(sys.argv):
            additional_files = sys.argv[files_index].split(',')
            priority_files = default_files + additional_files
        else:
            priority_files = default_files
    elif len(sys.argv) > 1 and sys.argv[1] not in ['--analyze', '--migrate']:
        # Custom file list provided
        priority_files = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    else:
        priority_files = default_files
    
    total_changes = 0
    successful_migrations = 0
    
    for file_path in priority_files:
        if os.path.exists(file_path):
            print(f"\n🔄 Processing: {file_path}")
            result = migrate_file(file_path)
            
            if 'error' in result:
                print(f"   ❌ Error: {result['error']}")
                continue
                
            successful_migrations += 1
            total_changes += result['changes']
            
            print(f"   📊 Original: {result['original']['font_sizes']} font-sizes, "
                  f"{result['original']['weights']} weights, "
                  f"{result['original']['heights']} line-heights")
                  
            print(f"   ✅ Migrated: {result['migrated']['font_tokens']} font tokens, "
                  f"{result['migrated']['weight_tokens']} weight tokens, "
                  f"{result['migrated']['height_tokens']} height tokens")
                  
            print(f"   📉 Remaining: {result['remaining']['font_sizes']} hardcoded font-sizes")
            print(f"   🎯 Changes made: {result['changes']}")
            
        else:
            print(f"\n⚠️  File not found: {file_path}")
    
    print(f"\n🏁 Migration Complete!")
    print(f"📈 Total changes: {total_changes}")
    print(f"📁 Files processed: {successful_migrations}/{len(priority_files)}")
    
    if total_changes > 0:
        print(f"\n📝 Next steps:")
        print(f"   1. Test visual consistency: open http://localhost:3000")
        print(f"   2. Run validation: ./scripts/typography-validation.sh") 
        print(f"   3. Check all 8 color themes work correctly")

if __name__ == '__main__':
    main()