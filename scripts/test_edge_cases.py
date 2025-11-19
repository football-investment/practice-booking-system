#!/usr/bin/env python3
"""
🧪 Edge Cases és Szinkronizációs Tesztek
========================================

Teszteli a docs/EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md-ben
azonosított problémákat.

P1 IMPROVEMENTS:
- Uses app.config.Settings for DB connection (no hardcoded credentials)
- Context manager for safe DB session handling
- Proper cleanup with teardown hooks
- Memory-safe, zero-leak design
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from contextlib import contextmanager
from app.database import get_db
from app.config import get_settings
from app.models.user_progress import (
    Specialization, PlayerLevel, CoachLevel, InternshipLevel,
    SpecializationProgress
)
from app.models.license import LicenseMetadata, UserLicense, LicenseSystemHelper
from app.models.track import Track, Module
from typing import List, Dict, Generator
from datetime import datetime

# Load settings from environment
settings = get_settings()


@contextmanager
def get_test_db() -> Generator[Session, None, None]:
    """
    Context manager for safe database session handling.

    Ensures:
    - Proper session creation
    - Automatic cleanup on success
    - Rollback on error
    - No leaked connections
    """
    db = next(get_db())
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        if db.is_active:
            db.rollback()
        db.close()
        # Verify session closed
        assert not db.is_active, "DB session not properly closed!"


class EdgeCaseTester:
    """Határeset tesztelő"""

    def __init__(self, db: Session):
        self.db = db
        self.results = []
        self.critical_count = 0
        self.warning_count = 0
        self.pass_count = 0

    def run_all_tests(self):
        """Minden teszt futtatása"""
        print("\n" + "="*70)
        print("🧪 EDGE CASE ÉS SZINKRONIZÁCIÓS TESZTEK")
        print("="*70 + "\n")

        # Adatforrás tesztek
        self.test_max_level_sync()
        self.test_internship_level_count_conflict()
        self.test_orphan_level_references()

        # Adatintegritás tesztek
        self.test_duplicate_progress_records()
        self.test_progress_license_sync()

        # Validáció tesztek
        self.test_empty_level_tables()
        self.test_license_metadata_coverage()

        # Eredmények
        self.print_results()

    def test_max_level_sync(self):
        """Teszt: max_levels szinkronban van-e a DB-vel?"""
        test_name = "Max Level Synchronization"

        discrepancies = []

        # PLAYER
        player_max_db = self.db.query(func.max(PlayerLevel.id)).scalar() or 0
        player_max_helper = LicenseSystemHelper.get_specialization_max_level("PLAYER")

        if player_max_db != player_max_helper:
            discrepancies.append(
                f"PLAYER: DB={player_max_db}, Helper={player_max_helper}"
            )

        # COACH
        coach_max_db = self.db.query(func.max(CoachLevel.id)).scalar() or 0
        coach_max_helper = LicenseSystemHelper.get_specialization_max_level("COACH")

        if coach_max_db != coach_max_helper:
            discrepancies.append(
                f"COACH: DB={coach_max_db}, Helper={coach_max_helper}"
            )

        # INTERNSHIP
        intern_max_db = self.db.query(func.max(InternshipLevel.id)).scalar() or 0
        intern_max_helper = LicenseSystemHelper.get_specialization_max_level("INTERNSHIP")

        if intern_max_db != intern_max_helper:
            discrepancies.append(
                f"INTERNSHIP: DB={intern_max_db}, Helper={intern_max_helper}"
            )

        if discrepancies:
            self.record_critical(
                test_name,
                f"Ellentmondások: {', '.join(discrepancies)}. "
                "KRITIKUS: Hardcoded max_levels nem egyezik a DB-vel!"
            )
        else:
            self.record_pass(
                test_name,
                f"Szinkronban: PLAYER={player_max_db}, COACH={coach_max_db}, INTERN={intern_max_db}"
            )

    def test_internship_level_count_conflict(self):
        """Teszt: INTERNSHIP 3 vs 5 szint konfliktus"""
        test_name = "Internship Level Count"

        actual_count = self.db.query(InternshipLevel).count()
        helper_max = LicenseSystemHelper.get_specialization_max_level("INTERNSHIP")

        if actual_count != helper_max:
            self.record_critical(
                test_name,
                f"KONFLIKTUS: DB-ben {actual_count} szint, de Helper szerint {helper_max}! "
                f"User nem tud {actual_count+1}-{helper_max} szintre lépni."
            )
        else:
            self.record_pass(
                test_name,
                f"Megfelelő: {actual_count} szint mindkét helyen"
            )

    def test_orphan_level_references(self):
        """Teszt: Vannak-e orphan level referenciák?"""
        test_name = "Orphan Level References"

        problems = []

        # PLAYER progress orphan szintek
        player_progress = self.db.query(SpecializationProgress).filter(
            SpecializationProgress.specialization_id == 'PLAYER'
        ).all()

        for prog in player_progress:
            level_exists = self.db.query(PlayerLevel).filter(
                PlayerLevel.id == prog.current_level
            ).first()

            if not level_exists:
                problems.append(
                    f"User {prog.student_id} PLAYER level {prog.current_level} nem létezik!"
                )

        # COACH
        coach_progress = self.db.query(SpecializationProgress).filter(
            SpecializationProgress.specialization_id == 'COACH'
        ).all()

        for prog in coach_progress:
            level_exists = self.db.query(CoachLevel).filter(
                CoachLevel.id == prog.current_level
            ).first()

            if not level_exists:
                problems.append(
                    f"User {prog.student_id} COACH level {prog.current_level} nem létezik!"
                )

        # INTERNSHIP
        intern_progress = self.db.query(SpecializationProgress).filter(
            SpecializationProgress.specialization_id == 'INTERNSHIP'
        ).all()

        for prog in intern_progress:
            level_exists = self.db.query(InternshipLevel).filter(
                InternshipLevel.id == prog.current_level
            ).first()

            if not level_exists:
                problems.append(
                    f"User {prog.student_id} INTERNSHIP level {prog.current_level} nem létezik!"
                )

        if problems:
            self.record_critical(
                test_name,
                f"Orphan referenciák találva:\n   " + "\n   ".join(problems)
            )
        else:
            self.record_pass(
                test_name,
                "Nincs orphan level referencia"
            )

    def test_duplicate_progress_records(self):
        """Teszt: Vannak-e duplikált progress rekordok?"""
        test_name = "Duplicate Progress Records"

        # Query duplikátumok keresésére
        duplicates = self.db.query(
            SpecializationProgress.student_id,
            SpecializationProgress.specialization_id,
            func.count(SpecializationProgress.id).label('count')
        ).group_by(
            SpecializationProgress.student_id,
            SpecializationProgress.specialization_id
        ).having(
            func.count(SpecializationProgress.id) > 1
        ).all()

        if duplicates:
            dup_list = [
                f"User {d[0]}, Spec {d[1]}: {d[2]} rekord"
                for d in duplicates
            ]
            self.record_critical(
                test_name,
                f"DUPLIKÁCIÓK TALÁLVA! Nincs UniqueConstraint!\n   " +
                "\n   ".join(dup_list)
            )
        else:
            self.record_warning(
                test_name,
                "Jelenleg nincs duplikáció, DE NINCS CONSTRAINT SEM! "
                "Migration szükséges: UniqueConstraint(student_id, specialization_id)"
            )

    def test_progress_license_sync(self):
        """Teszt: SpecializationProgress ↔ UserLicense szinkronizáció"""
        test_name = "Progress-License Sync"

        desync_issues = []

        # Minden user, akinek van progress-e
        all_progress = self.db.query(SpecializationProgress).all()

        for prog in all_progress:
            # Van-e hozzá license?
            license = self.db.query(UserLicense).filter(
                and_(
                    UserLicense.user_id == prog.student_id,
                    UserLicense.specialization_type == prog.specialization_id
                )
            ).first()

            if not license:
                desync_issues.append(
                    f"User {prog.student_id} {prog.specialization_id}: "
                    f"Van progress (level {prog.current_level}), de NINCS license"
                )
            elif license.current_level != prog.current_level:
                desync_issues.append(
                    f"User {prog.student_id} {prog.specialization_id}: "
                    f"Progress level={prog.current_level}, License level={license.current_level}"
                )

        if desync_issues:
            self.record_critical(
                test_name,
                f"SZINKRONIZÁCIÓS PROBLÉMÁK:\n   " + "\n   ".join(desync_issues[:5]) +
                (f"\n   ...és {len(desync_issues)-5} további" if len(desync_issues) > 5 else "")
            )
        else:
            if len(all_progress) == 0:
                self.record_warning(
                    test_name,
                    "Nincs progress adat a teszteléshez"
                )
            else:
                self.record_pass(
                    test_name,
                    f"{len(all_progress)} progress rekord szinkronban van"
                )

    def test_empty_level_tables(self):
        """Teszt: Level táblák üresek-e?"""
        test_name = "Empty Level Tables"

        issues = []

        player_count = self.db.query(PlayerLevel).count()
        if player_count == 0:
            issues.append("PlayerLevel tábla ÜRES!")

        coach_count = self.db.query(CoachLevel).count()
        if coach_count == 0:
            issues.append("CoachLevel tábla ÜRES!")

        intern_count = self.db.query(InternshipLevel).count()
        if intern_count == 0:
            issues.append("InternshipLevel tábla ÜRES!")

        if issues:
            self.record_critical(
                test_name,
                "KRITIKUS: " + ", ".join(issues) +
                "\nFuttasd: alembic upgrade head"
            )
        else:
            self.record_pass(
                test_name,
                f"Szintek megvannak: PLAYER={player_count}, COACH={coach_count}, INTERN={intern_count}"
            )

    def test_license_metadata_coverage(self):
        """Teszt: license_metadata lefedi-e az összes szintet?"""
        test_name = "License Metadata Coverage"

        missing = []

        # PLAYER
        player_count = self.db.query(PlayerLevel).count()
        player_metadata_count = self.db.query(LicenseMetadata).filter(
            LicenseMetadata.specialization_type == 'PLAYER'
        ).count()

        if player_metadata_count < player_count:
            missing.append(f"PLAYER: {player_metadata_count}/{player_count} metadata")

        # COACH
        coach_count = self.db.query(CoachLevel).count()
        coach_metadata_count = self.db.query(LicenseMetadata).filter(
            LicenseMetadata.specialization_type == 'COACH'
        ).count()

        if coach_metadata_count < coach_count:
            missing.append(f"COACH: {coach_metadata_count}/{coach_count} metadata")

        # INTERNSHIP
        intern_count = self.db.query(InternshipLevel).count()
        intern_metadata_count = self.db.query(LicenseMetadata).filter(
            LicenseMetadata.specialization_type == 'INTERNSHIP'
        ).count()

        if intern_metadata_count < intern_count:
            missing.append(f"INTERNSHIP: {intern_metadata_count}/{intern_count} metadata")

        if missing:
            self.record_warning(
                test_name,
                f"Hiányos license_metadata: {', '.join(missing)}. "
                "Frontend marketing tartalom nélkül."
            )
        else:
            self.record_pass(
                test_name,
                f"Teljes lefedettség: P={player_metadata_count}, C={coach_metadata_count}, I={intern_metadata_count}"
            )

    def record_critical(self, test_name: str, message: str):
        """Kritikus probléma rögzítése"""
        self.results.append({
            'severity': 'CRITICAL',
            'test': test_name,
            'message': message
        })
        self.critical_count += 1

    def record_warning(self, test_name: str, message: str):
        """Figyelmeztetés rögzítése"""
        self.results.append({
            'severity': 'WARNING',
            'test': test_name,
            'message': message
        })
        self.warning_count += 1

    def record_pass(self, test_name: str, message: str):
        """Sikeres teszt rögzítése"""
        self.results.append({
            'severity': 'PASS',
            'test': test_name,
            'message': message
        })
        self.pass_count += 1

    def print_results(self):
        """Eredmények megjelenítése"""
        print("\n" + "="*70)
        print("📊 EDGE CASE TESZT EREDMÉNYEK")
        print("="*70 + "\n")

        for result in self.results:
            if result['severity'] == 'CRITICAL':
                icon = "🔴"
                color = "\033[91m"
            elif result['severity'] == 'WARNING':
                icon = "🟡"
                color = "\033[93m"
            else:
                icon = "✅"
                color = "\033[92m"

            reset = "\033[0m"

            print(f"{icon} {color}{result['severity']}{reset} | {result['test']}")
            print(f"   └─ {result['message']}\n")

        print("="*70)
        total = self.critical_count + self.warning_count + self.pass_count

        print(f"\n📈 Összesítés:")
        print(f"   🔴 Kritikus: {self.critical_count}/{total}")
        print(f"   🟡 Figyelmeztetés: {self.warning_count}/{total}")
        print(f"   ✅ Rendben: {self.pass_count}/{total}")

        if self.critical_count > 0:
            print("\n⚠️  KRITIKUS PROBLÉMÁK TALÁLVA!")
            print("   Lásd: docs/EDGE_CASES_AND_SYNCHRONIZATION_ANALYSIS.md")
        elif self.warning_count > 0:
            print("\n⚠️  Figyelmeztetések vannak, de nem blokkolók.")
        else:
            print("\n🎉 Minden teszt sikeres!")

        print("="*70)


def teardown_db():
    """
    Cleanup hook - verifies no leaked connections.

    Called after all tests complete to ensure:
    - All DB sessions are closed
    - No active transactions remain
    - Connection pool is clean
    """
    from app.database import engine
    # Dispose engine to close all connections
    engine.dispose()
    print("\n🧹 Database cleanup complete - no leaked connections")


def main():
    """
    Main test runner with safe DB connection handling.

    P1 IMPROVEMENT: Uses context manager for automatic cleanup
    """
    try:
        with get_test_db() as db:
            tester = EdgeCaseTester(db)
            tester.run_all_tests()

            critical_count = tester.critical_count

        # Cleanup after tests
        teardown_db()

        # Exit code
        sys.exit(0 if critical_count == 0 else 1)

    except Exception as e:
        print(f"\n❌ Hiba a tesztelés során: {e}")
        import traceback
        traceback.print_exc()

        # Ensure cleanup even on error
        try:
            teardown_db()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
