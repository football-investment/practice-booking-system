from fastapi import APIRouter

from .endpoints import (
    auth,
    users,
    semesters,
    groups,
    sessions,
    bookings,
    attendance,
    feedback,
    reports,
    analytics,
    gamification,
    quiz,
    projects,
    notifications,
    messages,
    debug
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(semesters.router, prefix="/semesters", tags=["semesters"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification"])
api_router.include_router(quiz.router, prefix="/quizzes", tags=["quizzes"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])