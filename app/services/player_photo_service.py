"""
LFA Football Player card photo service.

Stores spec-specific photos in app/static/uploads/lfa_player_photos/{user_id}.jpg
— completely separate from any global User avatar/profile picture.
"""
import io
from pathlib import Path

from PIL import Image

ALLOWED_MIME: set[str] = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES: int = 2 * 1024 * 1024          # 2 MB hard limit
PHOTO_SIZE: tuple[int, int] = (400, 400)  # center-crop target
PHOTO_DIR: Path = Path("app/static/uploads/lfa_player_photos")


def get_photo_url(user_id: int) -> str:
    return f"/static/uploads/lfa_player_photos/{user_id}.jpg"


def save_player_photo(file_bytes: bytes, content_type: str, user_id: int) -> str:
    """Validate, center-crop to 400×400, save as JPEG. Returns static URL."""
    if content_type not in ALLOWED_MIME:
        raise ValueError(f"Nem támogatott képformátum: {content_type}. Elfogadott: JPEG, PNG, WEBP")
    if len(file_bytes) > MAX_BYTES:
        raise ValueError("A fájl mérete meghaladja a 2 MB-os korlátot")

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Érvénytelen képfájl")

    # Center-crop to square, then resize
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize(PHOTO_SIZE, Image.LANCZOS)

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PHOTO_DIR / f"{user_id}.jpg"
    img.save(out_path, "JPEG", quality=85, optimize=True)

    return get_photo_url(user_id)


def delete_player_photo(user_id: int) -> None:
    """Remove the photo file if it exists (silent no-op if missing)."""
    path = PHOTO_DIR / f"{user_id}.jpg"
    if path.exists():
        path.unlink()
