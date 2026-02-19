#!/usr/bin/env python3
"""
Debug script to test get_my_bookings endpoint directly
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.user import User
from app.models.booking import Booking
from app.schemas.booking import BookingWithRelations

# Create database session
db = SessionLocal()

try:
    # Get user
    user = db.query(User).filter(User.email == "junior.intern@lfa.com").first()
    print(f"User: {user.email}, ID: {user.id}")

    # Get bookings
    bookings = db.query(Booking).filter(Booking.user_id == user.id).all()
    print(f"\nFound {len(bookings)} bookings")

    for booking in bookings:
        print(f"\n=== Booking ID: {booking.id} ===")
        print(f"  Status: {booking.status}")
        print(f"  Session ID: {booking.session_id}")
        print(f"  User relationship loaded: {booking.user is not None}")
        print(f"  Session relationship loaded: {booking.session is not None}")

        if booking.session:
            print(f"  Session title: {booking.session.title}")

        # Try to create BookingWithRelations
        try:
            booking_schema = BookingWithRelations(
                id=booking.id,
                user_id=booking.user_id,
                session_id=booking.session_id,
                status=booking.status,
                waitlist_position=booking.waitlist_position,
                notes=booking.notes,
                created_at=booking.created_at,
                updated_at=booking.updated_at,
                cancelled_at=booking.cancelled_at,
                attended_status=booking.attended_status,
                user=booking.user,
                session=booking.session,
                attended=False
            )
            print(f"  ✅ BookingWithRelations created successfully")

            # Try to serialize
            try:
                json_data = booking_schema.model_dump()
                print(f"  ✅ Serialization successful")
            except Exception as e:
                print(f"  ❌ Serialization failed: {e}")

        except Exception as e:
            print(f"  ❌ BookingWithRelations creation failed: {e}")
            import traceback
            traceback.print_exc()

finally:
    db.close()
