"""
🎓 Parallel Specialization API Endpoints
Multi-track specialization management with semester-based progression
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from ....database import get_db
from ....services.parallel_specialization_service import ParallelSpecializationService
from ....dependencies import get_current_user
from ....models.user import User

router = APIRouter()


@router.get("/my-specializations", response_model=List[Dict[str, Any]])
async def get_my_specializations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active specializations for the current user
    """
    service = ParallelSpecializationService(db)
    return service.get_user_active_specializations(current_user.id)


@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_specializations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available specializations for current user based on their semester
    """
    service = ParallelSpecializationService(db)
    semester = service.get_user_semester_count(current_user.id)
    return service.get_available_specializations_for_semester(current_user.id, semester)


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_specialization_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive specialization dashboard for current user
    """
    service = ParallelSpecializationService(db)
    return service.get_user_specialization_dashboard(current_user.id)


@router.post("/start", response_model=Dict[str, Any])
async def start_new_specialization(
    data: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new specialization for the current user
    
    Request body:
    - **specialization**: PLAYER, COACH, or INTERNSHIP
    """
    if 'specialization' not in data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: specialization"
        )
    
    service = ParallelSpecializationService(db)
    result = service.start_new_specialization(current_user.id, data['specialization'])
    
    if not result['success']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result['message']
        )
    
    return result


@router.get("/validate/{specialization}", response_model=Dict[str, Any])
async def validate_specialization_addition(
    specialization: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate if a specialization can be added for current user
    
    - **specialization**: PLAYER, COACH, or INTERNSHIP
    """
    service = ParallelSpecializationService(db)
    return service.validate_specialization_addition(current_user.id, specialization)


@router.get("/combinations", response_model=Dict[int, Dict[str, Any]])
async def get_specialization_combinations():
    """
    Get possible specialization combinations by semester
    """
    service = ParallelSpecializationService(None)  # Static method, no DB needed
    return service.get_specialization_combinations_by_semester()


@router.get("/semester-info/{semester}", response_model=Dict[str, Any])
async def get_semester_specialization_info(
    semester: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specialization information for a specific semester
    
    - **semester**: Semester number (1, 2, 3, etc.)
    """
    service = ParallelSpecializationService(db)
    available = service.get_available_specializations_for_semester(current_user.id, semester)
    combinations = service.get_specialization_combinations_by_semester()
    
    return {
        'semester': semester,
        'available_specializations': available,
        'semester_info': combinations.get(semester, combinations.get(3, {})),  # Default to semester 3 rules
        'user_current_semester': service.get_user_semester_count(current_user.id)
    }


@router.get("/progression-rules", response_model=Dict[str, Any])
async def get_progression_rules():
    """
    Get complete progression rules for parallel specializations
    """
    return {
        'overview': 'Párhuzamos specializációs rendszer - fokozatos fejlődés',
        'rules': {
            'semester_1': {
                'description': 'Első szemeszter - Alapképzés',
                'max_specializations': 2,
                'available': ['PLAYER', 'INTERNSHIP'],
                'requirements': {
                    'PLAYER': 'Nincs előfeltétel - alapképzés',
                    'INTERNSHIP': 'Nincs előfeltétel - bármikor elérhető'
                },
                'typical_choices': [
                    'PLAYER (ajánlott kezdés)',
                    'PLAYER + INTERNSHIP (ambiciózus kezdés)'
                ]
            },
            'semester_2': {
                'description': 'Második szemeszter - Specializáció bővítés',
                'max_specializations': 3,
                'available': ['PLAYER', 'COACH', 'INTERNSHIP'],
                'requirements': {
                    'PLAYER': 'Mindig választható',
                    'COACH': 'Player specializáció megkezdése után',
                    'INTERNSHIP': 'Nincs előfeltétel'
                },
                'typical_choices': [
                    'PLAYER + COACH (természetes fejlődés)',
                    'PLAYER + COACH + INTERNSHIP (teljes paletta)'
                ]
            },
            'semester_3_plus': {
                'description': 'Harmadik szemeszter és utána - Párhuzamos specializációk',
                'max_specializations': 3,
                'available': ['PLAYER', 'COACH', 'INTERNSHIP'],
                'note': 'Mind a három specializáció párhuzamosan folytatható'
            }
        },
        'key_principles': [
            'Fokozatos fejlődés - nem minden egyszerre',
            'Player alapképzés ajánlott kiindulópont',
            'Coach csak Player után választható',
            'Internship bármikor hozzáadható',
            'Maximum 3 párhuzamos specializáció'
        ]
    }