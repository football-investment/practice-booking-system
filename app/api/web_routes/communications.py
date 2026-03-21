"""
Communications web routes — notifications and messages HTML frontend.

Notifications: reuses notification_service layer directly.
Messages:      direct DB queries (no standalone service layer exists).
Both pages use cookie auth (get_current_user_web), consistent with all other
web route modules.

GET  /notifications              → notification list page
POST /notifications/read-all     → mark all as read, redirect
POST /notifications/{id}/read    → mark one as read (fetch, returns JSON)
POST /notifications/{id}/delete  → delete one (fetch, returns JSON)
GET  /messages                   → inbox/sent/compose tabs
GET  /messages/{id}              → message detail (auto-marks read)
POST /messages/send              → send new message, redirect
POST /messages/{id}/delete       → delete message (fetch, returns JSON)
GET  /unread-counts              → JSON badge counts for header polling
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...dependencies import get_current_user_optional, get_current_user_web
from ...models.message import Message, MessagePriority
from ...models.user import User
from ...services import notification_service

BASE_DIR = Path(__file__).resolve().parent.parent.parent
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    notifications = notification_service.get_notifications(db, user.id, limit=50)
    unread_count = notification_service.get_unread_notification_count(db, user.id)
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": user,
        "notifications": notifications,
        "unread_count": unread_count,
        "spec_header_class": "hdr-hub",
        "show_spec_nav": False,
    })


@router.post("/notifications/read-all")
async def notifications_mark_all_read(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    notification_service.mark_all_as_read(db, user.id)
    db.commit()
    return RedirectResponse(url="/notifications?success=marked", status_code=303)


@router.post("/notifications/{notification_id}/read")
async def notification_mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Mark one notification as read. Called via fetch; returns JSON."""
    notification_service.mark_notification_as_read(db, notification_id, user.id)
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/notifications/{notification_id}/delete")
async def notification_delete(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Delete a notification. Called via fetch; returns JSON."""
    notification_service.delete_notification(db, notification_id, user.id)
    db.commit()
    return JSONResponse({"ok": True})


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    tab: str = "inbox",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    inbox = (
        db.query(Message)
        .filter(Message.recipient_id == user.id)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )
    sent = (
        db.query(Message)
        .filter(Message.sender_id == user.id)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )
    unread_count = (
        db.query(Message)
        .filter(Message.recipient_id == user.id, Message.is_read == False)
        .count()
    )
    # Available recipients for compose form (all active users except self)
    recipients = (
        db.query(User)
        .filter(User.id != user.id, User.is_active == True)
        .order_by(User.name)
        .all()
    )
    priorities = [p.value for p in MessagePriority]
    return templates.TemplateResponse("messages.html", {
        "request": request,
        "user": user,
        "inbox": inbox,
        "sent": sent,
        "unread_count": unread_count,
        "recipients": recipients,
        "priorities": priorities,
        "active_tab": tab,
        "spec_header_class": "hdr-hub",
        "show_spec_nav": False,
    })


@router.get("/messages/{message_id}", response_class=HTMLResponse)
async def message_detail(
    message_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    msg = (
        db.query(Message)
        .filter(
            Message.id == message_id,
            (Message.sender_id == user.id) | (Message.recipient_id == user.id),
        )
        .first()
    )
    if not msg:
        return RedirectResponse(url="/messages?error=not_found", status_code=303)

    # Auto-mark as read when recipient opens the message
    if msg.recipient_id == user.id and not msg.is_read:
        msg.is_read = True
        msg.read_at = datetime.now(timezone.utc)
        db.commit()

    return templates.TemplateResponse("message_detail.html", {
        "request": request,
        "user": user,
        "msg": msg,
    })


@router.post("/messages/send")
async def message_send(
    request: Request,
    recipient_id: int = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    priority: str = Form("NORMAL"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    recipient = db.query(User).filter(User.id == recipient_id, User.is_active == True).first()
    if not recipient:
        return RedirectResponse(url="/messages?tab=compose&error=invalid_recipient", status_code=303)

    subject = subject.strip()
    message = message.strip()
    if not subject or not message:
        return RedirectResponse(url="/messages?tab=compose&error=empty_fields", status_code=303)

    try:
        priority_enum = MessagePriority(priority)
    except ValueError:
        priority_enum = MessagePriority.NORMAL

    new_msg = Message(
        sender_id=user.id,
        recipient_id=recipient.id,
        subject=subject,
        message=message,
        priority=priority_enum,
    )
    db.add(new_msg)
    db.commit()
    return RedirectResponse(url="/messages?tab=sent&success=sent", status_code=303)


@router.post("/messages/{message_id}/delete")
async def message_delete(
    message_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_web),
):
    """Delete a message (sender or recipient). Called via fetch; returns JSON."""
    msg = (
        db.query(Message)
        .filter(
            Message.id == message_id,
            (Message.sender_id == user.id) | (Message.recipient_id == user.id),
        )
        .first()
    )
    if msg:
        db.delete(msg)
        db.commit()
    return JSONResponse({"ok": True})


# ── Badge polling (used by unified header JS) ─────────────────────────────────

@router.get("/unread-counts")
async def unread_counts(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    """Return unread notification + message counts for the header badge.
    Uses the optional dependency so unauthenticated requests get 0/0
    instead of a redirect (this endpoint is called by JS polling).
    """
    if not user:
        return JSONResponse({"notifications": 0, "messages": 0})

    notif_count = notification_service.get_unread_notification_count(db, user.id)
    msg_count = (
        db.query(Message)
        .filter(Message.recipient_id == user.id, Message.is_read == False)
        .count()
    )
    return JSONResponse({"notifications": notif_count, "messages": msg_count})
