from .user import User, UserRole
from .semester import Semester
from .group import Group, group_users
from .session import Session, SessionMode
from .booking import Booking, BookingStatus
from .attendance import Attendance, AttendanceStatus
from .feedback import Feedback
from .notification import Notification, NotificationType
from .message import Message, MessagePriority
from .gamification import UserAchievement, UserStats, BadgeType, configure_relationships
from .quiz import Quiz, QuizQuestion, QuizAnswerOption, QuizAttempt, QuizUserAnswer, QuestionType, QuizCategory, QuizDifficulty
from .project import Project, ProjectEnrollment, ProjectMilestone, ProjectMilestoneProgress, ProjectSession, ProjectStatus, ProjectEnrollmentStatus, ProjectProgressStatus, MilestoneStatus
from .license import LicenseMetadata, UserLicense, LicenseProgression, LicenseType, LicenseLevel, LicenseSystemHelper, configure_license_relationships

# 🎓 New Track-Based Modular Education System
from .track import Track, Module, ModuleComponent
from .certificate import CertificateTemplate, IssuedCertificate
from .user_progress import UserTrackProgress, UserModuleProgress, TrackProgressStatus, ModuleProgressStatus

# Configure relationships after all models are imported
configure_relationships()
configure_license_relationships()

__all__ = [
    "User",
    "UserRole",
    "Semester",
    "Group",
    "group_users",
    "Session",
    "SessionMode",
    "Booking",
    "BookingStatus",
    "Attendance",
    "AttendanceStatus",
    "Feedback",
    "Notification",
    "NotificationType",
    "Message",
    "MessagePriority",
    "UserAchievement",
    "UserStats",
    "BadgeType",
    "Quiz",
    "QuizQuestion",
    "QuizAnswerOption",
    "QuizAttempt",
    "QuizUserAnswer",
    "QuestionType",
    "QuizCategory",
    "QuizDifficulty",
    "Project",
    "ProjectEnrollment",
    "ProjectMilestone",
    "ProjectMilestoneProgress",
    "ProjectSession",
    "ProjectStatus",
    "ProjectEnrollmentStatus",
    "ProjectProgressStatus",
    "MilestoneStatus",
    "LicenseMetadata",
    "UserLicense", 
    "LicenseProgression",
    "LicenseType",
    "LicenseLevel",
    "LicenseSystemHelper",
]