"""
Admin coupon management endpoints
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ....database import get_db
from ....dependencies import get_current_admin_user, get_current_admin_user_web
from ....models.coupon import Coupon, CouponType
from ....models.audit_log import AuditLog, AuditAction
from ....models.user import User

router = APIRouter()


# Pydantic schemas
class CouponBase(BaseModel):
    """Base coupon schema"""
    code: str = Field(..., min_length=3, max_length=50, description="Unique coupon code")
    type: CouponType = Field(..., description="Coupon type (percent, fixed, credits)")
    discount_value: float = Field(..., gt=0, description="Discount value")
    description: str = Field(..., min_length=1, max_length=200, description="Human-readable description")
    is_active: bool = Field(default=True, description="Whether coupon is active")
    expires_at: datetime | None = Field(default=None, description="Expiration date (NULL = never expires)")
    max_uses: int | None = Field(default=None, ge=1, description="Maximum uses (NULL = unlimited)")


class CouponCreate(CouponBase):
    """Schema for creating a coupon"""
    pass


class CouponUpdate(BaseModel):
    """Schema for updating a coupon"""
    code: str | None = Field(None, min_length=3, max_length=50)
    type: CouponType | None = None
    discount_value: float | None = Field(None, gt=0)
    description: str | None = Field(None, min_length=1, max_length=200)
    is_active: bool | None = None
    expires_at: datetime | None = None
    max_uses: int | None = Field(None, ge=1)


class CouponResponse(CouponBase):
    """Schema for coupon response"""
    id: int
    current_uses: int
    created_at: datetime
    updated_at: datetime
    is_valid: bool

    class Config:
        from_attributes = True


class CouponPublic(BaseModel):
    """Public coupon schema (for students on credits page)"""
    code: str
    type: CouponType
    discount_value: float
    description: str

    class Config:
        from_attributes = True


# Admin endpoints
@router.get("/admin/coupons", response_model=List[CouponResponse])
async def list_all_coupons(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Any:
    """
    List all coupons (Admin only) - Web-based (cookie auth)
    """
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()

    # Add is_valid property
    response = []
    for coupon in coupons:
        coupon_dict = {
            "id": coupon.id,
            "code": coupon.code,
            "type": coupon.type,
            "discount_value": coupon.discount_value,
            "description": coupon.description,
            "is_active": coupon.is_active,
            "expires_at": coupon.expires_at,
            "max_uses": coupon.max_uses,
            "current_uses": coupon.current_uses,
            "created_at": coupon.created_at,
            "updated_at": coupon.updated_at,
            "is_valid": coupon.is_valid()
        }
        response.append(coupon_dict)

    return response


@router.post("/admin/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    request: Request,
    coupon_data: CouponCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Any:
    """
    Create a new coupon (Admin only) - Web-based (cookie auth)
    """
    # Check if code already exists
    existing = db.query(Coupon).filter(Coupon.code == coupon_data.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon code '{coupon_data.code}' already exists"
        )

    # Create coupon
    now = datetime.now(timezone.utc)
    coupon = Coupon(
        code=coupon_data.code.upper(),
        type=coupon_data.type,
        discount_value=coupon_data.discount_value,
        description=coupon_data.description,
        is_active=coupon_data.is_active,
        expires_at=coupon_data.expires_at,
        max_uses=coupon_data.max_uses,
        current_uses=0,
        created_at=now,
        updated_at=now
    )

    db.add(coupon)

    # Create audit log
    # Create audit log (optional - skip if table doesn't exist)
    try:
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.USER_CREATED,  # Using existing action
            resource_type="coupon",
            resource_id=None,
            details={
                "admin_name": current_user.name,
                "admin_email": current_user.email,
                "coupon_code": coupon.code,
                "coupon_type": coupon.type.value,
                "discount_value": coupon.discount_value,
                "description": coupon.description,
                "is_active": coupon.is_active,
                "message": f"Admin {current_user.name} created coupon '{coupon.code}'",
                "timestamp": now.isoformat()
            }
        )
        db.add(audit_log)
        db.commit()

        # Update audit log with coupon ID
        audit_log.resource_id = coupon.id
        db.commit()
    except Exception as e:
        print(f"⚠️ Audit log skipped (table may not exist): {e}")
        db.rollback()

    db.refresh(coupon)

    print(f"💳 Coupon created: {coupon.code} ({coupon.type.value}, {coupon.discount_value}) by {current_user.name}")

    return {
        "id": coupon.id,
        "code": coupon.code,
        "type": coupon.type,
        "discount_value": coupon.discount_value,
        "description": coupon.description,
        "is_active": coupon.is_active,
        "expires_at": coupon.expires_at,
        "max_uses": coupon.max_uses,
        "current_uses": coupon.current_uses,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at,
        "is_valid": coupon.is_valid()
    }


@router.put("/admin/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    request: Request,
    coupon_id: int,
    coupon_data: CouponUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Any:
    """
    Update a coupon (Admin only)
    """
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Check if new code conflicts with existing
    if coupon_data.code and coupon_data.code.upper() != coupon.code:
        existing = db.query(Coupon).filter(
            Coupon.code == coupon_data.code.upper(),
            Coupon.id != coupon_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coupon code '{coupon_data.code}' already exists"
            )

    # Store old values for audit
    old_values = {
        "code": coupon.code,
        "type": coupon.type.value,
        "discount_value": coupon.discount_value,
        "is_active": coupon.is_active
    }

    # Update fields
    update_data = coupon_data.model_dump(exclude_unset=True)
    if "code" in update_data:
        update_data["code"] = update_data["code"].upper()

    for field, value in update_data.items():
        setattr(coupon, field, value)

    coupon.updated_at = datetime.now(timezone.utc)

    # Create audit log (optional - skip if table doesn't exist)
    try:
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.USER_UPDATED,  # Using existing action
            resource_type="coupon",
            resource_id=coupon.id,
            details={
                "admin_name": current_user.name,
                "admin_email": current_user.email,
                "coupon_code": coupon.code,
                "old_values": old_values,
                "new_values": {k: str(v) for k, v in update_data.items()},
                "message": f"Admin {current_user.name} updated coupon '{coupon.code}'",
                "timestamp": coupon.updated_at.isoformat()
            }
        )
        db.add(audit_log)
    except Exception as e:
        print(f"⚠️ Audit log skipped (table may not exist): {e}")

    db.commit()
    db.refresh(coupon)

    print(f"✏️ Coupon updated: {coupon.code} by {current_user.name}")

    return {
        "id": coupon.id,
        "code": coupon.code,
        "type": coupon.type,
        "discount_value": coupon.discount_value,
        "description": coupon.description,
        "is_active": coupon.is_active,
        "expires_at": coupon.expires_at,
        "max_uses": coupon.max_uses,
        "current_uses": coupon.current_uses,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at,
        "is_valid": coupon.is_valid()
    }


@router.delete("/admin/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    request: Request,
    coupon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> None:
    """
    Delete a coupon (Admin only)
    """
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Create audit log before deletion (optional - skip if table doesn't exist)
    try:
        audit_log = AuditLog(
            user_id=current_user.id,
            action=AuditAction.USER_DELETED,  # Using existing action
            resource_type="coupon",
            resource_id=coupon.id,
            details={
                "admin_name": current_user.name,
                "admin_email": current_user.email,
                "coupon_code": coupon.code,
                "coupon_type": coupon.type.value,
                "discount_value": coupon.discount_value,
                "current_uses": coupon.current_uses,
                "message": f"Admin {current_user.name} deleted coupon '{coupon.code}'",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(audit_log)
    except Exception as e:
        print(f"⚠️ Audit log skipped (table may not exist): {e}")

    db.delete(coupon)
    db.commit()

    print(f"🗑️ Coupon deleted: {coupon.code} by {current_user.name}")


@router.post("/admin/coupons/{coupon_id}/toggle", response_model=CouponResponse)
async def toggle_coupon_status(
    request: Request,
    coupon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user_web)
) -> Any:
    """
    Toggle coupon active status (Admin only) - Web-based (cookie auth)
    """
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Toggle status
    old_status = coupon.is_active
    coupon.is_active = not coupon.is_active
    coupon.updated_at = datetime.now(timezone.utc)

    # Commit the coupon status change
    db.commit()
    db.refresh(coupon)

    print(f"🔄 Coupon {'activated' if coupon.is_active else 'deactivated'}: {coupon.code} by {current_user.name}")

    return {
        "id": coupon.id,
        "code": coupon.code,
        "type": coupon.type,
        "discount_value": coupon.discount_value,
        "description": coupon.description,
        "is_active": coupon.is_active,
        "expires_at": coupon.expires_at,
        "max_uses": coupon.max_uses,
        "current_uses": coupon.current_uses,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at,
        "is_valid": coupon.is_valid()
    }


# Public endpoints
@router.get("/coupons/active", response_model=List[CouponPublic])
async def list_active_coupons(
    db: Session = Depends(get_db)
) -> Any:
    """
    List all currently active and valid coupons (Public - for credits page)
    """
    now = datetime.now(timezone.utc)

    # Get active coupons that haven't expired
    coupons = db.query(Coupon).filter(
        Coupon.is_active == True
    ).all()

    # Filter by validity (expiration + max uses)
    valid_coupons = [c for c in coupons if c.is_valid()]

    return valid_coupons


@router.post("/coupons/validate/{code}")
async def validate_coupon(
    code: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Validate a coupon code and return its details if valid
    """
    coupon = db.query(Coupon).filter(Coupon.code == code.upper()).first()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    if not coupon.is_valid():
        reasons = []
        if not coupon.is_active:
            reasons.append("Coupon is inactive")
        if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
            reasons.append("Coupon has expired")
        if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
            reasons.append("Coupon has reached maximum uses")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon is not valid: {', '.join(reasons)}"
        )

    return {
        "code": coupon.code,
        "type": coupon.type,
        "discount_value": coupon.discount_value,
        "description": coupon.description,
        "valid": True
    }
