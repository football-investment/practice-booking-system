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
    debug,
    adaptive_learning,
    specializations,  # 🎓 NEW: Add specializations import
    payment_verification,  # 💰 NEW: Add payment verification import
    licenses,  # 🏮 NEW: Add GānCuju™️©️ license system
    parallel_specializations,  # 🎓🔀 NEW: Add parallel specialization system
    progression,  # 📈 NEW: Add progression tracking system
    tracks,  # 🎯 NEW: Add track-based education system
    certificates,  # 🏆 NEW: Add certificate management system
    students,  # 🎓 NEW: Add student dashboard endpoints
    curriculum,  # 📚 NEW: Add curriculum system endpoints
    curriculum_adaptive,  # 🧠 NEW: Add curriculum-based adaptive learning
    competency  # 🎯 NEW: Add competency tracking system
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
api_router.include_router(adaptive_learning.router, prefix="/adaptive-learning", tags=["adaptive-learning"])

# 🎓 NEW: Add specialization routes
api_router.include_router(
    specializations.router, 
    prefix="/specializations", 
    tags=["specializations"]
)

# 💰 NEW: Add payment verification routes
api_router.include_router(
    payment_verification.router, 
    prefix="/payment-verification", 
    tags=["payment-verification"]
)

# 🏮 NEW: Add GānCuju™️©️ license system routes
api_router.include_router(
    licenses.router, 
    prefix="/licenses", 
    tags=["licenses"]
)

# 🎓🔀 NEW: Add parallel specialization system routes
api_router.include_router(
    parallel_specializations.router, 
    prefix="/parallel-specializations", 
    tags=["parallel-specializations"]
)

# 📈 NEW: Add progression tracking system routes
api_router.include_router(
    progression.router, 
    prefix="/progression", 
    tags=["progression"]
)

# 🎯 NEW: Add track-based education system routes
api_router.include_router(
    tracks.router, 
    prefix="/tracks", 
    tags=["tracks"]
)

# 🏆 NEW: Add certificate management system routes
api_router.include_router(
    certificates.router, 
    prefix="/certificates", 
    tags=["certificates"]
)

# 🎓 NEW: Add student dashboard routes
api_router.include_router(
    students.router,
    prefix="/students",
    tags=["students"]
)

# 📚 NEW: Add curriculum system routes
api_router.include_router(
    curriculum.router,
    prefix="/curriculum",
    tags=["curriculum"]
)

# 🧠 NEW: Add curriculum-based adaptive learning routes
api_router.include_router(
    curriculum_adaptive.router,
    prefix="/curriculum-adaptive",
    tags=["curriculum-adaptive-learning"]
)

# 🎯 NEW: Add competency tracking system routes
api_router.include_router(
    competency.router,
    prefix="/competency",
    tags=["competency"]
)