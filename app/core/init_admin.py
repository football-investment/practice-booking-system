from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user import User, UserRole
from ..core.security import get_password_hash
from ..config import settings


def create_initial_admin():
    """Create initial admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if admin:
            print(f"Admin user already exists: {settings.ADMIN_EMAIL}")
            return
        
        # Create admin user
        admin_user = User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"Initial admin user created: {settings.ADMIN_EMAIL}")
        print(f"Admin password: {settings.ADMIN_PASSWORD}")
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_admin()