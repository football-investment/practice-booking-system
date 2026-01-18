"""
🎓 Parallel Specialization Service
Manages multiple simultaneous specializations per user with semester-based progression
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, date

from ..models.user import User
from ..models.license import UserLicense, LicenseMetadata
from ..models.specialization import SpecializationType
from ..services.license_service import LicenseService


class ParallelSpecializationService:
    """Service for managing multiple parallel specializations"""

    def __init__(self, db: Session):
        self.db = db
        self.license_service = LicenseService(db)
    # Age requirements for each specialization
    AGE_REQUIREMENTS = {
        'PLAYER': 5,    # Player: 5+ years
        'COACH': 14,    # Coach: 14+ years  
        'INTERNSHIP': 18 # Internship: 18+ years
    }
    
    def calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    
    def check_age_requirement(self, user_id: int, specialization: str) -> Dict[str, Any]:
        """Check if user meets age requirement for specialization"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'meets_requirement': False, 'reason': 'User not found'}
        if not user.date_of_birth:
            return {'meets_requirement': False, 'reason': 'Születési dátum hiányzik a profilból'}
        user_age = self.calculate_age(user.date_of_birth.date())
        required_age = self.AGE_REQUIREMENTS.get(specialization.upper(), 0)
        meets_requirement = user_age >= required_age
        return {
            'meets_requirement': meets_requirement,
            'user_age': user_age,
            'required_age': required_age,
            'reason': f'Minimum életkor: {required_age} év (jelenlegi: {user_age} év)' if not meets_requirement else f'Életkor követelmény teljesítve ({user_age} év)'
        }

    def check_payment_requirement(self, user_id: int, specialization_type: str = None, semester: int = None) -> Dict[str, Any]:
        """
        Check if user has verified payment for specialization enrollment
        Enhanced to support semester-specific and specialization-specific verification
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'payment_verified': False, 'reason': 'User not found'}

        # Admins and instructors can always enroll
        if user.role.value in ['admin', 'instructor']:
            return {
                'payment_verified': True,
                'reason': 'Admin/Instructor - befizetés nem szükséges',
                'verified_at': None,
                'verified_by': None,
                'payment_status_display': '✅ Admin/Instructor'
            }

        # Get current user semester and active specializations
        current_semester = semester or self.get_user_semester_count(user_id)
        current_licenses = self.get_user_active_specializations(user_id)
        current_spec_count = len(current_licenses)
        
        # Enhanced payment verification logic
        payment_verified = user.payment_verified
        
        # Special logic for multiple specializations in semester 2+
        if current_semester >= 2 and specialization_type:
            # If user already has one specialization and wants to add another
            if current_spec_count >= 1 and not any(spec['specialization_type'] == specialization_type for spec in current_licenses):
                # For second/third specialization, payment is considered verified if:
                # 1. User has basic payment verified (first specialization was paid)
                # 2. OR admin has specifically verified payment for this user
                
                payment_verified = user.payment_verified
                
                if payment_verified:
                    reason = f'Alapbefizetés ellenőrizve - további specializációk hozzáadhatók (Szemeszter {current_semester})'
                else:
                    reason = f'Alapbefizetés szükséges a specializációk hozzáadásához (Szemeszter {current_semester})'
            else:
                # First specialization or existing specialization
                reason = 'Alapbefizetés ellenőrizve és jóváhagyva' if payment_verified else 'Alapbefizetés még nem került ellenőrzésre és jóváhagyásra'
        else:
            # Semester 1 or no specific specialization
            reason = 'Alapbefizetés ellenőrizve és jóváhagyva' if payment_verified else 'Alapbefizetés még nem került ellenőrzésre és jóváhagyásra'
        
        return {
            'payment_verified': payment_verified,
            'reason': reason,
            'verified_at': user.payment_verified_at,
            'verified_by': user.payment_verified_by,
            'payment_status_display': user.payment_status_display,
            'semester_context': current_semester,
            'current_specialization_count': current_spec_count
        }

    def get_user_semester_count(self, user_id: int) -> int:
        """Calculate user's semester count based on their activity"""
        # For now, return a simple calculation
        # In production, this would be based on enrollment history
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return 1
        
        # Simple logic: if user has at least one specialization, they're in semester 2+
        licenses = self.db.query(UserLicense).filter(UserLicense.user_id == user_id).count()
        return 2 if licenses > 0 else 1

    def get_available_specializations_for_semester(self, user_id: int, semester: int) -> List[Dict[str, Any]]:
        """Get available specializations based on semester and current progress"""
        current_licenses = self.get_user_active_specializations(user_id)
        current_spec_codes = [spec['specialization_type'] for spec in current_licenses]
        current_count = len(current_spec_codes)
        
        available = []
        
        # Semester 1: Maximum 1 specialization (Player OR Coach OR Internship)
        if semester == 1:
            # If already has one specialization, no more can be added
            if current_count >= 1:
                return available
                
            if 'PLAYER' not in current_spec_codes:
                player_meta = self.license_service.get_license_metadata_by_level('PLAYER', 1)
                age_check = self.check_age_requirement(user_id, 'PLAYER')
                payment_check = self.check_payment_requirement(user_id, 'PLAYER', semester)
                
                # Both age and payment requirements must be met
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Player specializáció - alapképzés (min. 5 év) - minden követelmény teljesített'
                else:
                    reason = f'Player specializáció - {"; ".join(reason_parts)}'
                
                if player_meta:
                    available.append({
                        **player_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            if 'COACH' not in current_spec_codes:
                coach_meta = self.license_service.get_license_metadata_by_level('COACH', 1)
                age_check = self.check_age_requirement(user_id, 'COACH')
                payment_check = self.check_payment_requirement(user_id, 'COACH', semester)
                
                # Both age and payment requirements must be met
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Coach specializáció - edzői képzés (min. 14 év) - minden követelmény teljesített'
                else:
                    reason = f'Coach specializáció - {"; ".join(reason_parts)}'
                
                if coach_meta:
                    available.append({
                        **coach_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            if 'INTERNSHIP' not in current_spec_codes:
                intern_meta = self.license_service.get_license_metadata_by_level('INTERNSHIP', 1)
                age_check = self.check_age_requirement(user_id, 'INTERNSHIP')
                payment_check = self.check_payment_requirement(user_id, 'INTERNSHIP', semester)
                
                # Both age and payment requirements must be met
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Gyakornoki program (min. 18 év) - minden követelmény teljesített'
                else:
                    reason = f'Gyakornoki program - {"; ".join(reason_parts)}'
                
                if intern_meta:
                    available.append({
                        **intern_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })

        # Semester 2: Maximum 2 specializations (Player + Coach OR Player + Internship)
        elif semester == 2:
            # If already has 2 specializations, no more can be added
            if current_count >= 2:
                return available
            # Player always available
            if 'PLAYER' not in current_spec_codes:
                player_meta = self.license_service.get_license_metadata_by_level('PLAYER', 1)
                age_check = self.check_age_requirement(user_id, 'PLAYER')
                payment_check = self.check_payment_requirement(user_id, 'PLAYER', semester)
                
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Player specializáció (min. 5 év) - minden követelmény teljesített'
                else:
                    reason = f'Player specializáció - {"; ".join(reason_parts)}'
                
                if player_meta:
                    available.append({
                        **player_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            # Coach always available
            if 'COACH' not in current_spec_codes:
                coach_meta = self.license_service.get_license_metadata_by_level('COACH', 1)
                age_check = self.check_age_requirement(user_id, 'COACH')
                payment_check = self.check_payment_requirement(user_id, 'COACH', semester)
                
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Coach specializáció (min. 14 év) - minden követelmény teljesített'
                else:
                    reason = f'Coach specializáció - {"; ".join(reason_parts)}'
                
                if coach_meta:
                    available.append({
                        **coach_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            # Internship always available
            if 'INTERNSHIP' not in current_spec_codes:
                intern_meta = self.license_service.get_license_metadata_by_level('INTERNSHIP', 1)
                age_check = self.check_age_requirement(user_id, 'INTERNSHIP')
                payment_check = self.check_payment_requirement(user_id, 'INTERNSHIP', semester)
                
                # Both age and payment requirements must be met
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Gyakornoki program (min. 18 év) - minden követelmény teljesített'
                else:
                    reason = f'Gyakornoki program - {"; ".join(reason_parts)}'
                
                if intern_meta:
                    available.append({
                        **intern_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })

        # Semester 3+: Maximum 3 specializations (all three possible)
        elif semester >= 3:
            # If already has 3 specializations, no more can be added
            if current_count >= 3:
                return available
                
            # Player always available
            if 'PLAYER' not in current_spec_codes:
                player_meta = self.license_service.get_license_metadata_by_level('PLAYER', 1)
                age_check = self.check_age_requirement(user_id, 'PLAYER')
                payment_check = self.check_payment_requirement(user_id, 'PLAYER', semester)
                
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Player specializáció (min. 5 év) - minden követelmény teljesített'
                else:
                    reason = f'Player specializáció - {"; ".join(reason_parts)}'
                
                if player_meta:
                    available.append({
                        **player_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            # Coach always available
            if 'COACH' not in current_spec_codes:
                coach_meta = self.license_service.get_license_metadata_by_level('COACH', 1)
                age_check = self.check_age_requirement(user_id, 'COACH')
                payment_check = self.check_payment_requirement(user_id, 'COACH', semester)
                
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Coach specializáció (min. 14 év) - minden követelmény teljesített'
                else:
                    reason = f'Coach specializáció - {"; ".join(reason_parts)}'
                
                if coach_meta:
                    available.append({
                        **coach_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
            
            # Internship always available
            if 'INTERNSHIP' not in current_spec_codes:
                intern_meta = self.license_service.get_license_metadata_by_level('INTERNSHIP', 1)
                age_check = self.check_age_requirement(user_id, 'INTERNSHIP')
                payment_check = self.check_payment_requirement(user_id, 'INTERNSHIP', semester)
                
                # Both age and payment requirements must be met
                can_start = age_check['meets_requirement'] and payment_check['payment_verified']
                
                reason_parts = []
                if not age_check['meets_requirement']:
                    reason_parts.append(f"Korhatár: {age_check['reason']}")
                if not payment_check['payment_verified']:
                    reason_parts.append(f"Befizetés: {payment_check['reason']}")
                
                if can_start:
                    reason = f'Gyakornoki program (min. 18 év) - minden követelmény teljesített'
                else:
                    reason = f'Gyakornoki program - {"; ".join(reason_parts)}'
                
                if intern_meta:
                    available.append({
                        **intern_meta,
                        'can_start': can_start,
                        'requirement_met': can_start,
                        'reason': reason,
                        'age_requirement': age_check,
                        'payment_requirement': payment_check
                    })
        
        return available

    def get_user_active_specializations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active specializations for a user"""
        licenses = self.db.query(UserLicense).filter(
            UserLicense.user_id == user_id
        ).all()
        
        result = []
        for license in licenses:
            # Get current level metadata
            current_meta = self.license_service.get_license_metadata_by_level(
                license.specialization_type, 
                license.current_level
            )
            
            result.append({
                'specialization_type': license.specialization_type,
                'current_level': license.current_level,
                'max_achieved_level': license.max_achieved_level,
                'started_at': license.started_at.isoformat() if license.started_at else None,
                'last_advanced_at': license.last_advanced_at.isoformat() if license.last_advanced_at else None,
                'current_level_metadata': current_meta,
                'license_id': license.id
            })
        
        return result

    def start_new_specialization(self, user_id: int, specialization: str) -> Dict[str, Any]:
        """Start a new specialization for a user"""
        specialization = specialization.upper()
        
        # Check if user already has this specialization
        existing = self.db.query(UserLicense).filter(
            UserLicense.user_id == user_id,
            UserLicense.specialization_type == specialization
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'User already has {specialization} specialization',
                'license': existing.to_dict()
            }
        
        # Validate availability
        semester = self.get_user_semester_count(user_id)
        available = self.get_available_specializations_for_semester(user_id, semester)
        
        can_start = any(
            spec['specialization_type'] == specialization and spec['can_start'] 
            for spec in available
        )
        
        if not can_start:
            return {
                'success': False,
                'message': f'{specialization} not available for current semester/progress',
                'available_specializations': available
            }
        
        # Create new license
        new_license = UserLicense(
            user_id=user_id,
            specialization_type=specialization,
            current_level=1,
            max_achieved_level=1,
            started_at=datetime.now(timezone.utc)
        )
        
        self.db.add(new_license)
        self.db.commit()
        self.db.refresh(new_license)
        
        return {
            'success': True,
            'message': f'Successfully started {specialization} specialization',
            'license': new_license.to_dict()
        }

    def get_user_specialization_dashboard(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive specialization dashboard for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {'error': 'User not found'}
        
        semester = self.get_user_semester_count(user_id)
        active_specializations = self.get_user_active_specializations(user_id)
        available_specializations = self.get_available_specializations_for_semester(user_id, semester)
        
        # Get specialization progression info
        progression_info = {
            'semester_1': {
                'description': 'Alapképzés - Player specializáció',
                'available': ['PLAYER', 'INTERNSHIP'],
                'note': 'Első szemeszterben Player vagy Internship választható'
            },
            'semester_2_plus': {
                'description': 'Haladó képzés - párhuzamos specializációk',
                'available': ['PLAYER', 'COACH (Player után)', 'INTERNSHIP'],
                'note': 'Második szemesztertől Coach is választható Player mellett'
            }
        }
        
        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email
            },
            'current_semester': semester,
            'active_specializations': active_specializations,
            'available_specializations': available_specializations,
            'progression_info': progression_info,
            'parallel_progress': {
                'total_active': len(active_specializations),
                'can_add_more': len(available_specializations) > 0,
                'next_available': available_specializations[0] if available_specializations else None
            }
        }

    def get_specialization_combinations_by_semester(self) -> Dict[int, Dict[str, Any]]:
        """Get possible specialization combinations for each semester"""
        return {
            1: {
                'max_specializations': 1,
                'available': ['PLAYER', 'COACH', 'INTERNSHIP'],
                'combinations': [
                    ['PLAYER'],
                    ['COACH'],
                    ['INTERNSHIP']
                ],
                'description': 'Első szemeszter: Egy specializáció választható (Player VAGY Coach VAGY Internship)'
            },
            2: {
                'max_specializations': 2,
                'available': ['PLAYER', 'COACH', 'INTERNSHIP'],
                'combinations': [
                    ['PLAYER', 'COACH'],
                    ['PLAYER', 'INTERNSHIP'],
                    ['COACH', 'INTERNSHIP']
                ],
                'description': 'Második szemeszter: Két specializáció párhuzamosan'
            },
            3: {
                'max_specializations': 3,
                'available': ['PLAYER', 'COACH', 'INTERNSHIP'],
                'combinations': [
                    ['PLAYER', 'COACH', 'INTERNSHIP']
                ],
                'description': 'Harmadik szemeszter: Mind a három specializáció párhuzamosan'
            }
        }

    def validate_specialization_addition(self, user_id: int, new_specialization: str) -> Dict[str, Any]:
        """Validate if a new specialization can be added"""
        semester = self.get_user_semester_count(user_id)
        available = self.get_available_specializations_for_semester(user_id, semester)
        
        new_spec_available = next(
            (spec for spec in available if spec['specialization_type'] == new_specialization.upper()),
            None
        )
        
        if not new_spec_available:
            return {
                'valid': False,
                'reason': f'{new_specialization} not available for semester {semester}',
                'available_options': [spec['specialization_type'] for spec in available]
            }
        
        if not new_spec_available['can_start']:
            return {
                'valid': False,
                'reason': new_spec_available['reason'],
                'requirements': 'Player specialization required first'
            }
        
        return {
            'valid': True,
            'reason': new_spec_available['reason'],
            'semester': semester,
            'metadata': new_spec_available
        }