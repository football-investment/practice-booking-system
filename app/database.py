from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database():
    """Create all database tables"""
    # Import all models to ensure they are registered with Base
    from .models import (
        user, semester, group, session, booking, 
        attendance, feedback, notification
    )
    Base.metadata.create_all(bind=engine)