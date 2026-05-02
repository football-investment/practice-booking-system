"""Admin sponsor management routes."""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ....database import get_db
from ....dependencies import get_current_user_web
from ....models.user import User
from ....models.sponsor import Sponsor, SponsorContact

from . import templates, _admin_guard

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/admin/sponsors", response_class=HTMLResponse)
async def admin_sponsors_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: list all sponsors."""
    _admin_guard(user)
    sponsors = db.query(Sponsor).order_by(Sponsor.name).all()
    return templates.TemplateResponse(
        "admin/sponsors.html",
        {"request": request, "user": user, "sponsors": sponsors},
    )


@router.get("/admin/sponsors/new", response_class=HTMLResponse)
async def admin_sponsors_new_form(
    request: Request,
    user: User = Depends(get_current_user_web),
):
    """Admin: render new-sponsor form."""
    _admin_guard(user)
    return templates.TemplateResponse(
        "admin/sponsor_new.html",
        {"request": request, "user": user, "error": None},
    )


@router.post("/admin/sponsors/new")
async def admin_sponsors_create(
    request: Request,
    name: str = Form(...),
    code: str = Form(...),
    brand_category: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    # primary contact (optional)
    contact_name: Optional[str] = Form(None),
    contact_role: Optional[str] = Form(None),
    contact_email_primary: Optional[str] = Form(None),
    contact_phone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: create a new sponsor."""
    _admin_guard(user)

    code = code.strip().upper()

    # Uniqueness check (user-friendly error before DB constraint fires)
    existing = db.query(Sponsor).filter(Sponsor.code == code).first()
    if existing:
        return templates.TemplateResponse(
            "admin/sponsor_new.html",
            {
                "request": request,
                "user": user,
                "error": f"Partner code '{code}' is already in use.",
                "form": {
                    "name": name, "code": code, "brand_category": brand_category,
                    "city": city, "country": country, "contact_email": contact_email,
                    "website": website, "notes": notes,
                    "contact_name": contact_name, "contact_role": contact_role,
                    "contact_email_primary": contact_email_primary,
                    "contact_phone": contact_phone,
                },
            },
            status_code=400,
        )

    sponsor = Sponsor(
        name=name,
        code=code,
        brand_category=brand_category or None,
        city=city or None,
        country=country or None,
        contact_email=contact_email or None,
        website=website or None,
        notes=notes or None,
        is_active=True,
        created_by=user.id,
    )
    db.add(sponsor)
    db.flush()  # get sponsor.id before adding contact

    if contact_name and contact_name.strip():
        primary_contact = SponsorContact(
            sponsor_id=sponsor.id,
            name=contact_name.strip(),
            role=contact_role or None,
            email=contact_email_primary or None,
            phone=contact_phone or None,
            is_primary=True,
        )
        db.add(primary_contact)

    db.commit()
    logger.info("Sponsor created: id=%s code=%s by user=%s", sponsor.id, sponsor.code, user.id)
    return RedirectResponse(
        f"/admin/sponsors/{sponsor.id}?flash=Partner+created",
        status_code=303,
    )


@router.get("/admin/sponsors/{sponsor_id}", response_class=HTMLResponse)
async def admin_sponsors_detail(
    sponsor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: sponsor detail + contacts + linked events."""
    _admin_guard(user)
    sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Partner not found")

    return templates.TemplateResponse(
        "admin/sponsor_detail.html",
        {"request": request, "user": user, "sponsor": sponsor},
    )


@router.post("/admin/sponsors/{sponsor_id}/edit")
async def admin_sponsors_edit(
    sponsor_id: int,
    request: Request,
    name: str = Form(...),
    brand_category: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: update sponsor fields."""
    _admin_guard(user)
    sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Partner not found")

    sponsor.name           = name
    sponsor.brand_category = brand_category or None
    sponsor.city           = city or None
    sponsor.country        = country or None
    sponsor.contact_email  = contact_email or None
    sponsor.website        = website or None
    sponsor.notes          = notes or None
    sponsor.is_active      = is_active == "on"
    db.commit()
    return RedirectResponse(
        f"/admin/sponsors/{sponsor_id}?flash=Partner+updated",
        status_code=303,
    )


@router.post("/admin/sponsors/{sponsor_id}/contacts/add")
async def admin_sponsors_add_contact(
    sponsor_id: int,
    request: Request,
    contact_name: str = Form(...),
    contact_role: Optional[str] = Form(None),
    contact_email: Optional[str] = Form(None),
    contact_phone: Optional[str] = Form(None),
    is_primary: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: add a contact to a sponsor."""
    _admin_guard(user)
    sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()
    if not sponsor:
        raise HTTPException(status_code=404, detail="Partner not found")

    want_primary = is_primary == "on"

    if want_primary:
        existing_primary = (
            db.query(SponsorContact)
            .filter(SponsorContact.sponsor_id == sponsor_id, SponsorContact.is_primary == True)  # noqa: E712
            .first()
        )
        if existing_primary:
            return RedirectResponse(
                f"/admin/sponsors/{sponsor_id}?error=This+partner+already+has+a+primary+contact.+Unset+it+first.",
                status_code=303,
            )

    contact = SponsorContact(
        sponsor_id=sponsor_id,
        name=contact_name.strip(),
        role=contact_role or None,
        email=contact_email or None,
        phone=contact_phone or None,
        is_primary=want_primary,
    )
    db.add(contact)
    db.commit()
    return RedirectResponse(
        f"/admin/sponsors/{sponsor_id}?flash=Contact+added",
        status_code=303,
    )


@router.post("/admin/sponsors/{sponsor_id}/contacts/{contact_id}/delete")
async def admin_sponsors_delete_contact(
    sponsor_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Admin: remove a contact from a sponsor."""
    _admin_guard(user)
    contact = (
        db.query(SponsorContact)
        .filter(SponsorContact.id == contact_id, SponsorContact.sponsor_id == sponsor_id)
        .first()
    )
    if contact:
        db.delete(contact)
        db.commit()
    return RedirectResponse(
        f"/admin/sponsors/{sponsor_id}?flash=Contact+removed",
        status_code=303,
    )
