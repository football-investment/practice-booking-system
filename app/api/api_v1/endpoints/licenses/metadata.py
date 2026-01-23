"""
License metadata endpoints
"""
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .....database import get_db
from .....services.license_service import LicenseService

router = APIRouter()

@router.get("/metadata", response_model=List[Dict[str, Any]])
async def get_license_metadata(
    specialization: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get license metadata for all specializations or a specific one

    - **specialization**: Optional filter by COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_all_license_metadata(specialization)


@router.get("/metadata/{specialization}", response_model=List[Dict[str, Any]])
async def get_license_metadata_by_specialization(
    specialization: str,
    db: Session = Depends(get_db)
):
    """
    Get license metadata for a specific specialization (path parameter)

    - **specialization**: COACH, PLAYER, or INTERNSHIP
    """
    license_service = LicenseService(db)
    return license_service.get_all_license_metadata(specialization)


@router.get("/metadata/{specialization}/{level}", response_model=Dict[str, Any])
async def get_license_level_metadata(
    specialization: str,
    level: int,
    db: Session = Depends(get_db)
):
    """
    Get specific license level metadata with marketing content
    
    - **specialization**: COACH, PLAYER, or INTERNSHIP
    - **level**: License level number (1-8 for Coach/Player, 1-5 for Internship)
    """
    license_service = LicenseService(db)
    metadata = license_service.get_license_metadata_by_level(specialization, level)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License level {level} not found for {specialization}"
        )
    
    return metadata

