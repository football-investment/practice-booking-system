from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# Production-ready connection pool configuration
# For 100+ concurrent users, we need larger pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Base pool size (was: 5 default)
    max_overflow=30,       # Extra connections beyond pool_size (total: 50)
    pool_pre_ping=True,    # Verify connections before use (prevents stale connections)
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo_pool=False        # Set to True for debugging pool issues
)
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