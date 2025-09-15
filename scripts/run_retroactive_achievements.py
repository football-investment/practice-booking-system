#!/usr/bin/env python3
"""
Egyszerű Visszamenőleges Achievement Futtatószkrip
==================================================

Automatikusan futtatja a visszamenőleges achievement érvényesítést
minden meglévő felhasználóra.

Használat:
    PYTHONPATH=. python3 scripts/run_retroactive_achievements.py

Vagy interaktív mód:
    PYTHONPATH=. python3 scripts/run_retroactive_achievements.py --interactive
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.retroactive_achievements import RetroactiveAchievementProcessor
from app.database import get_db


def run_retroactive(dry_run=False, interactive=False):
    """Futtatja a visszamenőleges achievement érvényesítést"""
    
    if interactive:
        print("🚀 VISSZAMENŐLEGES ACHIEVEMENT ÉRVÉNYESÍTŐ")
        print("=" * 60)
        print()
        
        # Confirm before processing
        response = input("Biztosan futtatni szeretnéd a visszamenőleges érvényesítést? (y/N): ")
        if response.lower() not in ['y', 'yes', 'igen', 'i']:
            print("❌ Megszakítva.")
            return
        
        # Ask for dry run
        dry_run_response = input("Dry run mód? (csak előnézet, nincs változtatás) (y/N): ")
        dry_run = dry_run_response.lower() in ['y', 'yes', 'igen', 'i']
    
    db = next(get_db())
    
    try:
        processor = RetroactiveAchievementProcessor(db)
        stats = processor.process_all_users(dry_run=dry_run)
        
        if not dry_run and stats['achievements_awarded'] > 0:
            print(f"\n🎉 SIKERES FELDOLGOZÁS!")
            print(f"🏆 {stats['achievements_awarded']} új achievement odaítélve")
            print(f"⭐ {stats['xp_awarded']} XP odaítélve")
            print(f"👥 {stats['users_processed']} felhasználó frissítve")
            
        elif dry_run:
            print(f"\n🔍 DRY RUN EREDMÉNYEK:")
            print(f"🏆 {stats['achievements_awarded']} achievement kerülne odaítélésre")
            print(f"⭐ {stats['xp_awarded']} XP kerülne odaítélésre")
            print(f"👥 {stats['users_processed']} felhasználó érintett")
            
        return stats
            
    except Exception as e:
        print(f"❌ Kritikus hiba: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Főfüggvény parancssori argumentumokkal"""
    parser = argparse.ArgumentParser(
        description='Visszamenőleges Achievement Érvényesítő',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Csak előnézet, nincs tényleges változtatás'
    )
    
    parser.add_argument(
        '--interactive', 
        action='store_true', 
        help='Interaktív mód megerősítéssel'
    )
    
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Automatikus futtatás megerősítés nélkül (NEM dry-run)'
    )
    
    args = parser.parse_args()
    
    if args.force and args.dry_run:
        print("❌ Hiba: --force és --dry-run nem használható egyszerre")
        sys.exit(1)
        
    if args.interactive:
        run_retroactive(interactive=True)
    elif args.force:
        print("🚨 AUTOMATIKUS FUTTATÁS - MEGERŐSÍTÉS NÉLKÜL")
        run_retroactive(dry_run=False)
    else:
        print("🔍 DRY RUN MÓD (alapértelmezett)")
        print("Használd --force vagy --interactive kapcsolókat éles futtatáshoz")
        print()
        run_retroactive(dry_run=True)


if __name__ == "__main__":
    main()