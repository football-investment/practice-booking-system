from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
from typing import List, Optional

from ....database import get_db
from ....dependencies import get_current_user
from ....models.user import User
from ....models.message import Message, MessagePriority
from ....schemas.message import (
    MessageList,
    from datetime import datetime, timezone
        import traceback
    Message as MessageSchema,
    MessageCreate,
    MessageCreateByNickname,
    MessageUpdate,
    MessageSummary,
    MessageUserInfo
)

router = APIRouter()


@router.get("/inbox", response_model=MessageList)
def get_inbox_messages(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get inbox messages for current user"""
    
    # Base query for received messages
    query = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(Message.recipient_id == current_user.id)
    
    # Filter unread if requested
    if unread_only:
        query = query.filter(Message.is_read == False)
    
    # Get total and unread counts
    total_query = db.query(Message).filter(Message.recipient_id == current_user.id)
    total_count = total_query.count()
    unread_count = total_query.filter(Message.is_read == False).count()
    
    # Apply pagination and ordering
    messages = query.order_by(Message.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return MessageList(
        messages=messages,
        total_count=total_count,
        unread_count=unread_count
    )


@router.get("/sent", response_model=MessageList)
def get_sent_messages(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sent messages for current user"""
    
    # Base query for sent messages
    query = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(Message.sender_id == current_user.id)
    
    # Get counts
    total_count = db.query(Message).filter(Message.sender_id == current_user.id).count()
    
    # Apply pagination and ordering
    messages = query.order_by(Message.created_at.desc()).offset((page - 1) * size).limit(size).all()
    
    return MessageList(
        messages=messages,
        total_count=total_count,
        unread_count=0  # Sent messages don't have unread count
    )


@router.get("/{message_id}", response_model=MessageSchema)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific message by ID"""
    
    message = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user has access to this message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mark as read if it's the recipient viewing
    if message.recipient_id == current_user.id and not message.is_read:
        message.is_read = True
        message.read_at = func.now()
        db.commit()
        db.refresh(message)
    
    return message


@router.post("/", response_model=MessageSchema)
def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new message"""
    
    # Verify recipient exists
    recipient = db.query(User).filter(User.id == message_data.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Create message
    new_message = Message(
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        subject=message_data.subject,
        message=message_data.message,
        priority=message_data.priority,
        is_read=False,
        created_at=datetime.now(timezone.utc),
        read_at=None
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Load relationships for response
    message_with_relations = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(Message.id == new_message.id).first()
    
    return message_with_relations


@router.post("/by-nickname", response_model=MessageSchema)
def create_message_by_nickname(
    message_data: MessageCreateByNickname,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new message using recipient's nickname"""
    
    try:
        # Find recipient by nickname
        recipient = db.query(User).filter(User.nickname == message_data.recipient_nickname).first()
        if not recipient:
            raise HTTPException(status_code=404, detail=f"User with nickname '{message_data.recipient_nickname}' not found")
        
        # Create message with explicit datetime
        new_message = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            subject=message_data.subject,
            message=message_data.message,
            priority=message_data.priority,
            is_read=False,
            created_at=datetime.now(timezone.utc),
            read_at=None
        )
        
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        # Load relationships for response
        message_with_relations = db.query(Message).options(
            joinedload(Message.sender),
            joinedload(Message.recipient)
        ).filter(Message.id == new_message.id).first()
        
        return message_with_relations
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Database error in create_message_by_nickname: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Database operation failed")


@router.put("/{message_id}", response_model=MessageSchema)
def update_message(
    message_id: int,
    message_update: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update message content or mark as read"""
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check permissions based on what's being updated
    if message_update.message is not None:
        # Editing message content - only sender can edit
        if message.sender_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only message sender can edit content")
    elif message_update.is_read is not None:
        # Marking as read - only recipient can update
        if message.recipient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only message recipient can mark as read")
    else:
        # No update requested
        raise HTTPException(status_code=400, detail="No valid update fields provided")
    
    # Update message content if provided
    if message_update.message is not None:
        message.message = message_update.message
        # Mark as edited
        message.edited_at = datetime.now(timezone.utc)
        message.is_edited = True
    
    # Update read status if provided
    if message_update.is_read is not None:
        message.is_read = message_update.is_read
        if message_update.is_read:
            message.read_at = func.now()
        else:
            message.read_at = None
    
    db.commit()
    db.refresh(message)
    
    # Load relationships for response
    message_with_relations = db.query(Message).options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(Message.id == message.id).first()
    
    return message_with_relations


@router.get("/users/available", response_model=List[MessageUserInfo])
def get_available_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users available for messaging (excluding current user)"""
    
    users = db.query(User).filter(
        User.id != current_user.id,
        User.is_active == True,
        User.nickname.isnot(None)  # Only users with nicknames
    ).order_by(User.nickname).all()
    
    return users


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a message (sender or recipient can delete)"""
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Only sender or recipient can delete the message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully"}


@router.delete("/conversation/{user_id}")
def delete_conversation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete entire conversation between current user and specified user"""
    
    # Verify the other user exists
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find all messages between the two users
    messages_to_delete = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id)
        )
    ).all()
    
    # Delete all messages in the conversation
    deleted_count = 0
    for message in messages_to_delete:
        db.delete(message)
        deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Conversation deleted successfully",
        "deleted_messages": deleted_count,
        "other_user": other_user.name
    }