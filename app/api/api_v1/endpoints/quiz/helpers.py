"""
Quiz service dependency injection helper
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from .....database import get_db
from .....services.quiz_service import QuizService


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(db)
