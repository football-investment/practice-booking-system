"""
🎓 User Specialization Models and Enums
Defines the Player/Coach specialization system for the LFA education platform
"""
import enum
from typing import Optional


class SpecializationType(enum.Enum):
    """User specialization types for the football education system"""
    PLAYER = "PLAYER"
    COACH = "COACH"
    INTERNSHIP = "INTERNSHIP"
    
    @classmethod
    def get_display_name(cls, specialization: Optional['SpecializationType']) -> str:
        """Get user-friendly display name for specialization"""
        if not specialization:
            return "Nincs kiválasztva"
            
        display_names = {
            cls.PLAYER: "Player (Játékos fejlesztés)",
            cls.COACH: "Coach (Edzői, vezetési készségek)",
            cls.INTERNSHIP: "Internship (Gyakornoki program)"
        }
        return display_names.get(specialization, str(specialization))
    
    @classmethod
    def get_description(cls, specialization: Optional['SpecializationType']) -> str:
        """Get detailed description for specialization"""
        if not specialization:
            return "Még nincs kiválasztva szakirány"
            
        descriptions = {
            cls.PLAYER: "Játékos fejlesztési fókusz - technikai készségek, taktikai tudás, fizikai fejlődés, mentális erősség",
            cls.COACH: "Edzői és vezetési fókusz - csapatvezetés, taktikai elemzés, kommunikáció, stratégiai tervezés",
            cls.INTERNSHIP: "Gyakornoki program - valós munkakörnyezeti tapasztalat, mentorship, gyakorlati projektmunka, karrierfejlesztés"
        }
        return descriptions.get(specialization, "")
    
    @classmethod
    def get_features(cls, specialization: Optional['SpecializationType']) -> list:
        """Get key features/focus areas for specialization"""
        if not specialization:
            return []
            
        features = {
            cls.PLAYER: [
                "Technikai készségfejlesztés",
                "Taktikai megértés",
                "Fizikai kondíció",
                "Mentális erősség",
                "Csapatjáték"
            ],
            cls.COACH: [
                "Csapatvezetési készségek", 
                "Taktikai elemzés",
                "Kommunikáció",
                "Stratégiai tervezés",
                "Motivációs technikák"
            ],
            cls.INTERNSHIP: [
                "Valós projektmunka",
                "Mentorship és támogatás",
                "Munkakörnyezeti tapasztalat",
                "Szakmai hálózatépítés",
                "Karrierfejlesztés"
            ]
        }
        return features.get(specialization, [])
    
    @classmethod
    def get_icon(cls, specialization: Optional['SpecializationType']) -> str:
        """Get emoji icon for specialization"""
        if not specialization:
            return "❓"
            
        icons = {
            cls.PLAYER: "⚽",
            cls.COACH: "👨‍🏫",
            cls.INTERNSHIP: "🎓"
        }
        return icons.get(specialization, "🎯")
    
    @classmethod
    def get_session_access_info(cls, specialization: Optional['SpecializationType']) -> str:
        """Get information about what sessions this specialization can access"""
        if not specialization:
            return "Minden session elérhető (nincs specializáció)"
        
        access_info = {
            cls.PLAYER: "Player-specifikus, vegyes és általános sessionok",
            cls.COACH: "Coach-specifikus, vegyes és általános sessionök",
            cls.INTERNSHIP: "Gyakornoki mentorship sessionök, gyakorlati workshopok és minden általános session"
        }
        return access_info.get(specialization, "Ismeretlen hozzáférés")
    
    @classmethod
    def get_project_access_info(cls, specialization: Optional['SpecializationType']) -> str:
        """Get information about what projects this specialization can enroll in"""
        if not specialization:
            return "Minden projekt elérhető (nincs specializáció)"
        
        access_info = {
            cls.PLAYER: "Player-fókuszú, interdiszciplináris és általános projektek",
            cls.COACH: "Coach-fókuszú, interdiszciplináris és általános projektek",
            cls.INTERNSHIP: "Gyakornoki projektek, valós munkakörnyezeti feladatok és interdiszciplináris kollaborációs projektek"
        }
        return access_info.get(specialization, "Ismeretlen hozzáférés")
    
    @classmethod
    def get_progression_path(cls) -> list:
        """Get the recommended progression path for specializations"""
        return [
            {
                'code': cls.PLAYER.value,
                'name': cls.get_display_name(cls.PLAYER),
                'description': 'Alapképzés - játékos fejlesztés',
                'semester': 1,
                'prerequisite': None
            },
            {
                'code': cls.COACH.value,
                'name': cls.get_display_name(cls.COACH),
                'description': 'Haladó képzés - edzői készségek',
                'semester': 2,
                'prerequisite': cls.PLAYER.value
            },
            {
                'code': cls.INTERNSHIP.value,
                'name': cls.get_display_name(cls.INTERNSHIP),
                'description': 'Gyakorlati program - bármikor elérhető',
                'semester': 'any',
                'prerequisite': None
            }
        ]
    
    @classmethod
    def get_available_for_user(cls, current_specialization: Optional['SpecializationType'], semester_count: int = 1) -> list:
        """Get available specializations for a user based on their current status"""
        available = []
        progression = cls.get_progression_path()
        
        for spec in progression:
            if spec['code'] == cls.INTERNSHIP.value:
                # Internship is always available
                available.append(spec)
            elif semester_count == 1 and spec['semester'] == 1:
                # First semester - can choose Player
                available.append(spec)
            elif semester_count >= 2 and spec['semester'] == 2:
                # Second semester+ - can choose Coach if have Player
                if current_specialization == cls.PLAYER or current_specialization is None:
                    available.append(spec)
        
        return available
    
    @classmethod
    def validate_specialization_change(cls, current: Optional['SpecializationType'], new: 'SpecializationType', semester_count: int = 1) -> tuple[bool, str]:
        """Validate if a specialization change is allowed"""
        if new == cls.INTERNSHIP:
            return True, "Gyakornoki program bármikor elérhető"
        
        if semester_count == 1:
            if new == cls.PLAYER:
                return True, "Player specializáció választható az első szemeszterben"
            else:
                return False, "Első szemeszterben csak Player specializáció választható"
        
        if semester_count >= 2:
            if new == cls.COACH and (current == cls.PLAYER or current is None):
                return True, "Coach specializáció választható Player után a második szemesztertől"
            elif new == cls.PLAYER:
                return True, "Player specializáció mindig választható"
            else:
                return False, "Coach specializácóhoz Player előképzettség szükséges"
        
        return False, "Érvénytelen specializáció váltás"