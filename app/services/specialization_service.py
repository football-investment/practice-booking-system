"""
Specialization Progress Service
Manages student progression through specialization levels
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, Any, Optional

from app.database import Base


class SpecializationService:
    """Service for managing specialization progression"""

    def __init__(self, db: Session):
        self.db = db

    def get_level_requirements(self, specialization_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Get requirements for a specific level in a specialization.

        Args:
            specialization_id: PLAYER, COACH, or INTERNSHIP
            level: Level number (1-8 for PLAYER/COACH, 1-3 for INTERNSHIP)

        Returns:
            Dict with level info or None if not found
        """
        from app.models.user_progress import PlayerLevel, CoachLevel, InternshipLevel

        if specialization_id == 'PLAYER':
            level_data = self.db.query(PlayerLevel).filter(PlayerLevel.id == level).first()
            if not level_data:
                return None
            return {
                'level': level,
                'name': level_data.name,
                'color': level_data.color,
                'required_xp': level_data.required_xp,
                'required_sessions': level_data.required_sessions,
                'description': level_data.description,
                'license_title': level_data.license_title
            }

        elif specialization_id == 'COACH':
            level_data = self.db.query(CoachLevel).filter(CoachLevel.id == level).first()
            if not level_data:
                return None
            return {
                'level': level,
                'name': level_data.name,
                'required_xp': level_data.required_xp,
                'required_sessions': level_data.required_sessions,
                'theory_hours': level_data.theory_hours,
                'practice_hours': level_data.practice_hours,
                'description': level_data.description,
                'license_title': level_data.license_title
            }

        elif specialization_id == 'INTERNSHIP':
            level_data = self.db.query(InternshipLevel).filter(InternshipLevel.id == level).first()
            if not level_data:
                return None
            return {
                'level': level,
                'name': level_data.name,
                'required_xp': level_data.required_xp,
                'required_sessions': level_data.required_sessions,
                'total_hours': level_data.total_hours,
                'description': level_data.description,
                'license_title': level_data.license_title
            }

        return None

    def get_student_progress(self, student_id: int, specialization_id: str) -> Dict[str, Any]:
        """
        Get student's progress for a specialization.
        Creates progress entry if doesn't exist.

        Args:
            student_id: User ID
            specialization_id: PLAYER, COACH, or INTERNSHIP

        Returns:
            Dict with complete progress information
        """
        from app.models.user_progress import SpecializationProgress

        # Progress lekérése vagy létrehozása
        progress = self.db.query(SpecializationProgress).filter(
            and_(
                SpecializationProgress.student_id == student_id,
                SpecializationProgress.specialization_id == specialization_id
            )
        ).first()

        if not progress:
            # Automatikus létrehozás
            progress = SpecializationProgress(
                student_id=student_id,
                specialization_id=specialization_id,
                current_level=1,
                total_xp=0,
                completed_sessions=0,
                completed_projects=0
            )
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)

        # Jelenlegi szint követelmények
        current_level_req = self.get_level_requirements(specialization_id, progress.current_level)

        # Következő szint követelmények
        next_level_req = self.get_level_requirements(specialization_id, progress.current_level + 1)

        # Progress percentage kalkuláció
        progress_percentage = 0
        if next_level_req:
            progress_percentage = min(100, int((progress.total_xp / next_level_req['required_xp']) * 100))

        # XP needed for next level
        xp_needed = 0
        if next_level_req:
            xp_needed = max(0, next_level_req['required_xp'] - progress.total_xp)

        # Sessions needed for next level
        sessions_needed = 0
        if next_level_req:
            sessions_needed = max(0, next_level_req['required_sessions'] - progress.completed_sessions)

        return {
            'student_id': student_id,
            'specialization_id': specialization_id,
            'current_level': progress.current_level,
            'current_level_info': current_level_req,
            'next_level_info': next_level_req,
            'total_xp': progress.total_xp,
            'xp_needed': xp_needed,
            'completed_sessions': progress.completed_sessions,
            'sessions_needed': sessions_needed,
            'completed_projects': progress.completed_projects,
            'progress_percentage': progress_percentage,
            'can_level_up': self.can_level_up(progress),
            'last_activity': progress.last_activity,
            'is_max_level': next_level_req is None
        }

    def can_level_up(self, progress) -> bool:
        """
        Check if student can level up.

        Args:
            progress: SpecializationProgress instance

        Returns:
            bool: True if requirements met
        """
        next_level_req = self.get_level_requirements(
            progress.specialization_id,
            progress.current_level + 1
        )

        if not next_level_req:
            return False  # Nincs több szint

        return (
            progress.total_xp >= next_level_req['required_xp'] and
            progress.completed_sessions >= next_level_req['required_sessions']
        )

    def update_progress(
        self,
        student_id: int,
        specialization_id: str,
        xp_gained: int = 0,
        sessions_completed: int = 0,
        projects_completed: int = 0
    ) -> Dict[str, Any]:
        """
        Update student progress and check for level up.

        Args:
            student_id: User ID
            specialization_id: PLAYER, COACH, or INTERNSHIP
            xp_gained: XP to add
            sessions_completed: Number of sessions completed
            projects_completed: Number of projects completed

        Returns:
            Dict with update result
        """
        from app.models.user_progress import SpecializationProgress

        progress = self.db.query(SpecializationProgress).filter(
            and_(
                SpecializationProgress.student_id == student_id,
                SpecializationProgress.specialization_id == specialization_id
            )
        ).first()

        if not progress:
            progress = SpecializationProgress(
                student_id=student_id,
                specialization_id=specialization_id,
                current_level=1,
                total_xp=0,
                completed_sessions=0,
                completed_projects=0
            )
            self.db.add(progress)

        # Progress frissítése
        old_level = progress.current_level
        progress.total_xp += xp_gained
        progress.completed_sessions += sessions_completed
        progress.completed_projects += projects_completed
        progress.last_activity = datetime.utcnow()

        # Level up ellenőrzés (akár többszöri level up is)
        leveled_up = False
        levels_gained = 0
        while self.can_level_up(progress):
            progress.current_level += 1
            levels_gained += 1
            leveled_up = True

        self.db.commit()
        self.db.refresh(progress)

        # Get new level info if leveled up
        new_level_info = None
        if leveled_up:
            new_level_info = self.get_level_requirements(specialization_id, progress.current_level)

        return {
            'success': True,
            'new_xp': progress.total_xp,
            'old_level': old_level,
            'new_level': progress.current_level,
            'leveled_up': leveled_up,
            'levels_gained': levels_gained,
            'new_level_info': new_level_info
        }

    def get_all_specializations(self) -> list[Dict[str, Any]]:
        """
        Get all active specializations.

        Returns:
            List of specialization dicts
        """
        from app.models.user_progress import Specialization

        specs = self.db.query(Specialization).filter(Specialization.is_active == True).all()

        return [
            {
                'id': s.id,
                'name': s.name,
                'icon': s.icon,
                'description': s.description,
                'max_levels': s.max_levels
            }
            for s in specs
        ]

    def get_all_levels(self, specialization_id: str) -> list[Dict[str, Any]]:
        """
        Get all levels for a specialization.

        Args:
            specialization_id: PLAYER, COACH, or INTERNSHIP

        Returns:
            List of level dicts
        """
        from app.models.user_progress import Specialization

        # Max levels lekérése
        spec = self.db.query(Specialization).filter(Specialization.id == specialization_id).first()
        if not spec:
            return []

        levels = []
        for level in range(1, spec.max_levels + 1):
            level_info = self.get_level_requirements(specialization_id, level)
            if level_info:
                levels.append(level_info)

        return levels
