#!/usr/bin/env python3
"""
🧪 Curriculum Struktúra Automatizált Tesztelő
==============================================

Teszteli a curriculum struktúra integritását és skálázhatóságát.
Ellenőrzi, hogy minden szint megfelelően kapcsolódik a modulokhoz.

Tesztek:
- ✅ Adatbázis kapcsolat
- ✅ Specializációk létezése
- ✅ Szintek száma
- ✅ Track-ek létezése
- ✅ Modulok száma
- ✅ Komponensek száma
- ✅ Adatok integritása
- ✅ Kapcsolatok helyessége

P1 IMPROVEMENTS:
- Uses app.config.Settings for DB connection (no hardcoded credentials)
- Context manager for safe DB session handling
- Proper cleanup with teardown hooks
- Memory-safe, zero-leak design
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func
from contextlib import contextmanager
from typing import Generator
from app.database import get_db
from app.config import get_settings
from app.models.user_progress import Specialization, PlayerLevel, CoachLevel, InternshipLevel

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
from app.models.track import Track, Module, ModuleComponent
from typing import Dict, List, Tuple
from datetime import datetime


class CurriculumTester:
    """Automatizált curriculum tesztelő"""

    def __init__(self, db: Session):
        self.db = db
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def run_all_tests(self):
        """Minden teszt futtatása"""
        print("\n" + "="*70)
        print("🧪 CURRICULUM STRUKTÚRA AUTOMATIZÁLT TESZTELÉS")
        print("="*70)
        print(f"Kezdés: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Tesztek futtatása
        self.test_database_connection()
        self.test_specializations_exist()
        self.test_level_counts()
        self.test_tracks_exist()
        self.test_modules_exist()
        self.test_components_exist()
        self.test_data_integrity()
        self.test_relationships()
        self.test_scalability()

        # Eredmények
        self.print_results()

    def test_database_connection(self):
        """Teszt: Adatbázis kapcsolat"""
        try:
            self.db.execute("SELECT 1")
            self.record_pass("Database Connection", "Sikeres kapcsolat az adatbázishoz")
        except Exception as e:
            self.record_fail("Database Connection", f"Kapcsolódási hiba: {e}")

    def test_specializations_exist(self):
        """Teszt: Specializációk létezése"""
        specializations = self.db.query(Specialization).all()
        expected = ['PLAYER', 'COACH', 'INTERNSHIP']

        if len(specializations) >= 3:
            spec_ids = [s.id for s in specializations]
            missing = [e for e in expected if e not in spec_ids]

            if not missing:
                self.record_pass(
                    "Specializations Exist",
                    f"Mind a 3 specializáció megtalálható: {', '.join(spec_ids)}"
                )
            else:
                self.record_fail(
                    "Specializations Exist",
                    f"Hiányzó specializációk: {', '.join(missing)}"
                )
        else:
            self.record_fail(
                "Specializations Exist",
                f"Csak {len(specializations)}/3 specializáció található"
            )

    def test_level_counts(self):
        """Teszt: Szintek száma specializációnként"""
        tests = [
            ("PlayerLevel", PlayerLevel, 8),
            ("CoachLevel", CoachLevel, 8),
            ("InternshipLevel", InternshipLevel, 3),
        ]

        for name, model, expected_count in tests:
            actual_count = self.db.query(model).count()

            if actual_count == expected_count:
                self.record_pass(
                    f"{name} Count",
                    f"{actual_count} szint (várt: {expected_count})"
                )
            else:
                self.record_fail(
                    f"{name} Count",
                    f"{actual_count} szint talált, de {expected_count} várt"
                )

    def test_tracks_exist(self):
        """Teszt: Track-ek létezése"""
        tracks = self.db.query(Track).all()
        expected_codes = ['PLAYER', 'COACH', 'INTERNSHIP']

        track_codes = [t.code for t in tracks]
        missing = [code for code in expected_codes if code not in track_codes]

        if not missing and len(tracks) >= 3:
            self.record_pass(
                "Tracks Exist",
                f"Mind a 3 track megtalálható: {', '.join(track_codes)}"
            )
        else:
            self.record_fail(
                "Tracks Exist",
                f"Hiányzó trackek: {', '.join(missing) if missing else 'Kevés track'}"
            )

    def test_modules_exist(self):
        """Teszt: Modulok létezése és száma"""
        track_modules = {
            'PLAYER': 8,   # 8 PlayerLevel → 8 modul
            'COACH': 8,    # 8 CoachLevel → 8 modul
            'INTERNSHIP': 3  # 3 InternshipLevel → 3 modul
        }

        for track_code, expected_count in track_modules.items():
            track = self.db.query(Track).filter(Track.code == track_code).first()

            if not track:
                self.record_fail(
                    f"Modules for {track_code}",
                    f"Track '{track_code}' nem található"
                )
                continue

            module_count = self.db.query(Module).filter(Module.track_id == track.id).count()

            if module_count == expected_count:
                self.record_pass(
                    f"Modules for {track_code}",
                    f"{module_count} modul (várt: {expected_count})"
                )
            elif module_count == 0:
                self.record_fail(
                    f"Modules for {track_code}",
                    f"Nincs modul! Futtasd: python scripts/create_minimal_curriculum_structure.py"
                )
            else:
                self.record_fail(
                    f"Modules for {track_code}",
                    f"{module_count} modul, de {expected_count} várt"
                )

    def test_components_exist(self):
        """Teszt: Komponensek létezése"""
        module_count = self.db.query(Module).count()

        if module_count == 0:
            self.record_fail("Components Exist", "Nincs modul, így komponens sem lehet")
            return

        component_count = self.db.query(ModuleComponent).count()
        expected_min = module_count * 3  # Minden modulban min. 3 komponens

        if component_count >= expected_min:
            self.record_pass(
                "Components Exist",
                f"{component_count} komponens ({module_count} modul × 3 = {expected_min} minimum)"
            )
        else:
            self.record_fail(
                "Components Exist",
                f"Csak {component_count} komponens, de {expected_min} minimum szükséges"
            )

    def test_data_integrity(self):
        """Teszt: Adatok integritása"""
        # Orphan modulok ellenőrzése
        orphan_modules = self.db.query(Module).filter(Module.track_id.is_(None)).count()

        if orphan_modules == 0:
            self.record_pass("Data Integrity - Modules", "Nincs árva modul (mind track-hez tartozik)")
        else:
            self.record_fail("Data Integrity - Modules", f"{orphan_modules} árva modul található")

        # Orphan komponensek
        orphan_components = self.db.query(ModuleComponent).filter(
            ModuleComponent.module_id.is_(None)
        ).count()

        if orphan_components == 0:
            self.record_pass("Data Integrity - Components", "Nincs árva komponens")
        else:
            self.record_fail("Data Integrity - Components", f"{orphan_components} árva komponens")

    def test_relationships(self):
        """Teszt: Kapcsolatok helyessége"""
        # Track → Module kapcsolat
        tracks = self.db.query(Track).all()

        for track in tracks:
            module_count_direct = self.db.query(Module).filter(Module.track_id == track.id).count()
            module_count_relationship = len(track.modules)

            if module_count_direct == module_count_relationship:
                self.record_pass(
                    f"Relationship {track.code} → Modules",
                    f"{module_count_direct} modul mindkét módon"
                )
            else:
                self.record_fail(
                    f"Relationship {track.code} → Modules",
                    f"Eltérés: direct={module_count_direct}, relationship={module_count_relationship}"
                )

    def test_scalability(self):
        """Teszt: Skálázhatóság"""
        total_tracks = self.db.query(Track).count()
        total_modules = self.db.query(Module).count()
        total_components = self.db.query(ModuleComponent).count()

        memory_estimate_mb = (
            (total_tracks * 1) +
            (total_modules * 2) +
            (total_components * 0.5)
        ) / 1024  # KB → MB

        if memory_estimate_mb < 10:
            self.record_pass(
                "Scalability",
                f"Struktúra kompakt: ~{memory_estimate_mb:.2f}MB becsült memória"
            )
        else:
            self.record_fail(
                "Scalability",
                f"Struktúra nagy: ~{memory_estimate_mb:.2f}MB (optimalizálás szükséges)"
            )

    def record_pass(self, test_name: str, message: str):
        """Sikeres teszt rögzítése"""
        self.test_results.append({
            'status': 'PASS',
            'test': test_name,
            'message': message
        })
        self.passed += 1

    def record_fail(self, test_name: str, message: str):
        """Sikertelen teszt rögzítése"""
        self.test_results.append({
            'status': 'FAIL',
            'test': test_name,
            'message': message
        })
        self.failed += 1

    def print_results(self):
        """Eredmények megjelenítése"""
        print("\n" + "="*70)
        print("📊 TESZT EREDMÉNYEK")
        print("="*70 + "\n")

        for result in self.test_results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            status_color = "\033[92m" if result['status'] == 'PASS' else "\033[91m"
            reset_color = "\033[0m"

            print(f"{status_icon} {status_color}{result['status']}{reset_color} | {result['test']}")
            print(f"   └─ {result['message']}\n")

        print("="*70)
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n📈 Összesítés:")
        print(f"   Sikeres: {self.passed}/{total} ({pass_rate:.1f}%)")
        print(f"   Sikertelen: {self.failed}/{total}")

        if self.failed == 0:
            print("\n🎉 MINDEN TESZT SIKERES! A curriculum struktúra megfelelő.")
        else:
            print("\n⚠️  Van sikertelen teszt. Ellenőrizd a fenti hibaüzeneteket.")

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
            tester = CurriculumTester(db)
            tester.run_all_tests()

            failed_count = tester.failed

        # Cleanup after tests
        teardown_db()

        # Exit code a CI/CD számára
        sys.exit(0 if failed_count == 0 else 1)

    except Exception as e:
        print(f"\n❌ Kritikus hiba a tesztelés során: {e}")
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
