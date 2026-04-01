"""Club service — CRUD + code generation"""
import re
from sqlalchemy.orm import Session
from app.models.club import Club


def _generate_club_code(db: Session, name: str) -> str:
    """Auto-generate a unique code from club name. e.g. 'FC Vasas' → 'FC-VASAS'."""
    base = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().upper()).strip("-")
    base = base[:15]  # max 15 chars for base
    candidate = base
    suffix = 0
    while db.query(Club).filter(Club.code == candidate).first():
        suffix += 1
        candidate = f"{base}-{suffix:02d}"
    return candidate


def create_club(
    db: Session,
    *,
    name: str,
    city: str | None = None,
    country: str | None = None,
    contact_email: str | None = None,
    created_by_id: int | None = None,
) -> Club:
    """Create a new Club. Raises ValueError if name already exists (normalised)."""
    normalised = name.strip().lower()
    existing = db.query(Club).filter(Club.name.ilike(normalised)).first()
    if existing:
        raise ValueError(f"Club with name '{name}' already exists (id={existing.id})")

    code = _generate_club_code(db, name)
    club = Club(
        name=name.strip(),
        code=code,
        city=city,
        country=country,
        contact_email=contact_email,
        created_by=created_by_id,
        is_active=True,
    )
    db.add(club)
    db.flush()
    return club


def get_club(db: Session, club_id: int) -> Club | None:
    return db.query(Club).filter(Club.id == club_id).first()


def get_or_create_club(
    db: Session,
    *,
    name: str,
    city: str | None = None,
    country: str | None = None,
    created_by_id: int | None = None,
) -> Club:
    """Return existing Club by normalised name, or create it."""
    existing = db.query(Club).filter(Club.name.ilike(name.strip())).first()
    if existing:
        return existing
    return create_club(
        db,
        name=name,
        city=city,
        country=country,
        created_by_id=created_by_id,
    )


def list_clubs(db: Session, *, active_only: bool = True) -> list[Club]:
    q = db.query(Club)
    if active_only:
        q = q.filter(Club.is_active.is_(True))
    return q.order_by(Club.name).all()
