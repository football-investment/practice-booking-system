from .user import User, UserRole
from .instructor_specialization import InstructorSpecialization
from .instructor_availability import InstructorSpecializationAvailability
from .instructor_assignment import (
    InstructorAvailabilityWindow,
    InstructorAssignmentRequest,
    AssignmentRequestStatus,
    LocationMasterInstructor,
    InstructorPosition,
    PositionStatus,
    PositionApplication,
    ApplicationStatus,
    InstructorAssignment
)
from .location import Location
from .campus import Campus
from .semester import Semester, SemesterStatus
from .group import Group, group_users
from .session import Session, SessionType
from .booking import Booking, BookingStatus
from .attendance import Attendance, AttendanceStatus
from .feedback import Feedback
from .notification import Notification, NotificationType
from .message import Message, MessagePriority
from .gamification import UserAchievement, UserStats, BadgeType, configure_relationships
from .achievement import Achievement, AchievementCategory
from .quiz import Quiz, QuizQuestion, QuizAnswerOption, QuizAttempt, QuizUserAnswer, SessionQuiz, QuestionType, QuizCategory, QuizDifficulty
from .project import Project, ProjectEnrollment, ProjectMilestone, ProjectMilestoneProgress, ProjectSession, ProjectStatus, ProjectEnrollmentStatus, ProjectProgressStatus, MilestoneStatus
from .license import LicenseMetadata, UserLicense, LicenseProgression, LicenseType, LicenseLevel, LicenseSystemHelper, configure_license_relationships
from .semester_enrollment import SemesterEnrollment
from .performance_review import StudentPerformanceReview, InstructorSessionReview
from .football_skill_assessment import FootballSkillAssessment
from .belt_promotion import BeltPromotion
from .credit_transaction import CreditTransaction, TransactionType
from .xp_transaction import XPTransaction
from .invoice_request import InvoiceRequest, InvoiceRequestStatus
from .coupon import Coupon, CouponType
from .invitation_code import InvitationCode
from .session_group import SessionGroupAssignment, SessionGroupStudent
from .audit_log import AuditLog

# 🎓 New Track-Based Modular Education System
from .track import Track, Module, ModuleComponent
from .certificate import CertificateTemplate, IssuedCertificate
from .user_progress import UserTrackProgress, UserModuleProgress, TrackProgressStatus, ModuleProgressStatus

# 🏆 Tournament System
from .tournament_enums import TournamentType, ParticipantType, TeamMemberRole
from .tournament_type import TournamentType as TournamentTypeModel  # DB model for tournament types
from .team import Team, TeamMember, TournamentTeamEnrollment
from .tournament_ranking import TournamentRanking, TournamentStats, TournamentReward
from .tournament_status_history import TournamentStatusHistory
from .tournament_achievement import (
    TournamentSkillMapping,
    TournamentParticipation,
    TournamentBadge,
    TournamentBadgeType,
    TournamentBadgeCategory,
    TournamentBadgeRarity,
    SkillPointConversionRate
)

# Configure relationships after all models are imported
configure_relationships()
configure_license_relationships()

__all__ = [
    "User",
    "UserRole",
    "InstructorSpecialization",
    "InstructorSpecializationAvailability",
    "InstructorAvailabilityWindow",
    "InstructorAssignmentRequest",
    "AssignmentRequestStatus",
    "LocationMasterInstructor",
    "InstructorPosition",
    "PositionStatus",
    "PositionApplication",
    "ApplicationStatus",
    "InstructorAssignment",
    "Location",
    "Campus",
    "Semester",
    "SemesterStatus",
    "Group",
    "group_users",
    "Session",
    "SessionType",
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
    "Achievement",
    "AchievementCategory",
    "Quiz",
    "QuizQuestion",
    "QuizAnswerOption",
    "QuizAttempt",
    "QuizUserAnswer",
    "SessionQuiz",
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
    "SemesterEnrollment",
    "FootballSkillAssessment",
    "BeltPromotion",
    "CreditTransaction",
    "TransactionType",
    "XPTransaction",
    "InvoiceRequest",
    "InvoiceRequestStatus",
    "Coupon",
    "CouponType",
    "StudentPerformanceReview",
    "InstructorSessionReview",
    "SessionGroupAssignment",
    "SessionGroupStudent",
    "AuditLog",
    # Tournament System
    "TournamentType",
    "TournamentTypeModel",
    "ParticipantType",
    "TeamMemberRole",
    "Team",
    "TeamMember",
    "TournamentTeamEnrollment",
    "TournamentRanking",
    "TournamentStats",
    "TournamentReward",
    "TournamentStatusHistory",
    "TournamentSkillMapping",
    "TournamentParticipation",
    "TournamentBadge",
    "TournamentBadgeType",
    "TournamentBadgeCategory",
    "TournamentBadgeRarity",
    "SkillPointConversionRate",
]