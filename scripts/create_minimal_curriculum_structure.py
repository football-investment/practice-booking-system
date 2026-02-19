#!/usr/bin/env python3
"""
🏗️ Minimális Curriculum Struktúra Generátor
===========================================

Egyszerű, tesztelhető alapstruktúra létrehozása placeholder adatokkal.
Később manuálisan bővíthető valódi szakmai tartalommal.

Struktúra:
- 3 Specialization (PLAYER, COACH, INTERNSHIP)
- Minden specializációnak annyi szintje van, amennyi az adatbázisban
- Minden szinten 1 placeholder modul
- Minden modulban 3 komponens: theory, quiz, practice

Előnyök:
- ✅ Könnyű tesztelés
- ✅ Memória-hatékony
- ✅ Skálázható
- ✅ Manuálisan bővíthető
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user_progress import Specialization, PlayerLevel, CoachLevel, InternshipLevel
from app.models.track import Track, Module, ModuleComponent
from datetime import datetime
import uuid


class MinimalCurriculumGenerator:
    """Generálja az egyszerű curriculum struktúrát"""

    def __init__(self, db: Session):
        self.db = db
        self.created_tracks = {}
        self.created_modules = {}

    def generate_all(self):
        """Főfolyamat - minden specializáció generálása"""
        print("🏗️ Minimális Curriculum Struktúra Generálás")
        print("=" * 60)

        # 1. Player curriculum
        self.generate_player_curriculum()

        # 2. Coach curriculum
        self.generate_coach_curriculum()

        # 3. Internship curriculum
        self.generate_internship_curriculum()

        print("\n✅ Generálás sikeres!")
        self.print_summary()

    def generate_player_curriculum(self):
        """PLAYER specializáció curriculum"""
        print("\n⚽ PLAYER Curriculum generálása...")

        # Ellenőrizzük a szintek számát
        level_count = self.db.query(PlayerLevel).count()
        print(f"   Talált szintek: {level_count}")

        if level_count == 0:
            print("   ⚠️  Nincs PlayerLevel az adatbázisban! Először futtasd a migrationt.")
            return

        # Track létrehozása vagy lekérése
        track = self.get_or_create_track(
            code="PLAYER",
            name="GānCuju™© Player Program",
            description="Placeholder curriculum for Player specialization",
            duration_semesters=8
        )

        # Minden szinthez 1 modul
        levels = self.db.query(PlayerLevel).order_by(PlayerLevel.id).all()
        for idx, level in enumerate(levels, 1):
            module = self.create_module(
                track=track,
                name=f"Level {idx}: {level.name}",
                description=f"Placeholder module for {level.name}. To be filled with real content later.",
                order=idx,
                estimated_hours=level.required_sessions * 2  # Becsült óraszám
            )

            # 3 komponens minden modulhoz
            self.create_standard_components(module, idx)

        print(f"   ✅ {len(levels)} modul létrehozva")

    def generate_coach_curriculum(self):
        """COACH specializáció curriculum"""
        print("\n👨‍🏫 COACH Curriculum generálása...")

        level_count = self.db.query(CoachLevel).count()
        print(f"   Talált szintek: {level_count}")

        if level_count == 0:
            print("   ⚠️  Nincs CoachLevel az adatbázisban!")
            return

        track = self.get_or_create_track(
            code="COACH",
            name="LFA Coach Development Program",
            description="Placeholder curriculum for Coach specialization",
            duration_semesters=5
        )

        levels = self.db.query(CoachLevel).order_by(CoachLevel.id).all()
        for idx, level in enumerate(levels, 1):
            module = self.create_module(
                track=track,
                name=f"Level {idx}: {level.name}",
                description=f"Placeholder module for {level.name}. Theory: {level.theory_hours}h, Practice: {level.practice_hours}h",
                order=idx,
                estimated_hours=level.theory_hours + level.practice_hours
            )

            self.create_standard_components(module, idx)

        print(f"   ✅ {len(levels)} modul létrehozva")

    def generate_internship_curriculum(self):
        """INTERNSHIP specializáció curriculum"""
        print("\n🚀 INTERNSHIP Curriculum generálása...")

        level_count = self.db.query(InternshipLevel).count()
        print(f"   Talált szintek: {level_count}")

        if level_count == 0:
            print("   ⚠️  Nincs InternshipLevel az adatbázisban!")
            return

        track = self.get_or_create_track(
            code="INTERNSHIP",
            name="Startup Spirit Internship",
            description="Placeholder curriculum for Internship program",
            duration_semesters=3
        )

        levels = self.db.query(InternshipLevel).order_by(InternshipLevel.id).all()
        for idx, level in enumerate(levels, 1):
            module = self.create_module(
                track=track,
                name=f"Level {idx}: {level.name}",
                description=f"Placeholder module for {level.name}. Total hours: {level.total_hours}h",
                order=idx,
                estimated_hours=level.total_hours
            )

            self.create_standard_components(module, idx)

        print(f"   ✅ {len(levels)} modul létrehozva")

    def get_or_create_track(self, code: str, name: str, description: str, duration_semesters: int) -> Track:
        """Track létrehozása vagy lekérése"""
        track = self.db.query(Track).filter(Track.code == code).first()

        if track:
            print(f"   📁 Meglévő track: {track.name}")
            self.created_tracks[code] = track
            return track

        track = Track(
            id=uuid.uuid4(),
            code=code,
            name=name,
            description=description,
            duration_semesters=duration_semesters,
            is_active=True,
            created_at=datetime.utcnow()
        )

        self.db.add(track)
        self.db.commit()
        self.db.refresh(track)

        self.created_tracks[code] = track
        print(f"   ✨ Új track létrehozva: {track.name}")
        return track

    def create_module(self, track: Track, name: str, description: str, order: int, estimated_hours: int) -> Module:
        """Modul létrehozása"""
        module = Module(
            id=uuid.uuid4(),
            track_id=track.id,
            name=name,
            description=description,
            order_in_track=order,
            estimated_hours=estimated_hours,
            is_mandatory=True,
            learning_objectives=[
                "Placeholder objective 1",
                "Placeholder objective 2",
                "Placeholder objective 3"
            ],
            created_at=datetime.utcnow()
        )

        self.db.add(module)
        self.db.commit()
        self.db.refresh(module)

        key = f"{track.code}_L{order}"
        self.created_modules[key] = module

        return module

    def create_standard_components(self, module: Module, level_num: int):
        """Standard komponensek létrehozása egy modulhoz"""
        components = [
            {
                "type": "theory",
                "name": f"Theory Content - Level {level_num}",
                "description": "Placeholder theory content. Replace with real educational material.",
                "order": 1,
                "estimated_minutes": 45,
                "component_data": {
                    "content_type": "markdown",
                    "placeholder": True
                }
            },
            {
                "type": "quiz",
                "name": f"Knowledge Check - Level {level_num}",
                "description": "Placeholder quiz. Add real questions later.",
                "order": 2,
                "estimated_minutes": 15,
                "component_data": {
                    "questions": [],
                    "passing_score": 70,
                    "placeholder": True
                }
            },
            {
                "type": "practice",
                "name": f"Practical Exercise - Level {level_num}",
                "description": "Placeholder practice exercise. Define real tasks later.",
                "order": 3,
                "estimated_minutes": 60,
                "component_data": {
                    "exercise_type": "hands_on",
                    "placeholder": True
                }
            }
        ]

        for comp_data in components:
            component = ModuleComponent(
                id=uuid.uuid4(),
                module_id=module.id,
                type=comp_data["type"],
                name=comp_data["name"],
                description=comp_data["description"],
                order_in_module=comp_data["order"],
                estimated_minutes=comp_data["estimated_minutes"],
                is_mandatory=True,
                component_data=comp_data["component_data"],
                created_at=datetime.utcnow()
            )
            self.db.add(component)

        self.db.commit()

    def print_summary(self):
        """Összefoglaló kiírása"""
        print("\n" + "=" * 60)
        print("📊 ÖSSZEFOGLALÓ")
        print("=" * 60)

        for code, track in self.created_tracks.items():
            module_count = self.db.query(Module).filter(Module.track_id == track.id).count()
            component_count = self.db.query(ModuleComponent).join(Module).filter(
                Module.track_id == track.id
            ).count()

            print(f"\n{track.name} ({code}):")
            print(f"  - Modulok: {module_count}")
            print(f"  - Komponensek: {component_count}")
            print(f"  - Időtartam: {track.duration_semesters} félév")


def main():
    """Főprogram"""
    print("\n" + "="*60)
    print("🏗️  MINIMÁLIS CURRICULUM STRUKTÚRA GENERÁTOR")
    print("="*60)
    print("\nEz a szkript egyszerű placeholder struktúrát hoz létre.")
    print("Később manuálisan bővíthető valódi tartalommal.\n")

    response = input("Folytatod? (y/n): ")
    if response.lower() != 'y':
        print("Megszakítva.")
        return

    db = SessionLocal()

    try:
        generator = MinimalCurriculumGenerator(db)
        generator.generate_all()

        print("\n" + "="*60)
        print("✅ SIKERES GENERÁLÁS!")
        print("="*60)
        print("\nKövetkező lépések:")
        print("1. Futtasd a tesztelő szkriptet: python scripts/test_curriculum_structure.py")
        print("2. Töltsd fel valódi tartalommal a modulokat")
        print("3. Ellenőrizd a frontend megjelenítést")

    except Exception as e:
        print(f"\n❌ Hiba történt: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
