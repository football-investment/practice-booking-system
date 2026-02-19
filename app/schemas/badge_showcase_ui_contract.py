"""
Badge Showcase UI Contract

Minimal contract between backend and frontend for badge display.
Defines exactly what data the UI needs for different badge views.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class BadgeDisplayMode(str, Enum):
    """How badges should be displayed"""
    GRID = "grid"           # Grid layout (profile page)
    LIST = "list"           # List layout (history page)
    COMPACT = "compact"     # Compact badges (header/sidebar)
    SHOWCASE = "showcase"   # Featured showcase (landing page)


class BadgeRarity(str, Enum):
    """Badge rarity levels - affects visual styling"""
    COMMON = "COMMON"          # Gray/White
    UNCOMMON = "UNCOMMON"      # Green
    RARE = "RARE"              # Blue
    EPIC = "EPIC"              # Purple
    LEGENDARY = "LEGENDARY"    # Gold/Orange


# ============================================================================
# MINIMAL BADGE DATA
# ============================================================================

class BadgeUIMinimal(BaseModel):
    """
    Minimal badge data for compact displays.

    Use in: Header, sidebar, tooltips
    """
    icon: str                    # Emoji: 🥇, 🥈, 🥉, 🏆
    rarity: BadgeRarity          # For color coding
    title: str                   # Short title

    class Config:
        from_attributes = True


class BadgeUIStandard(BaseModel):
    """
    Standard badge data for normal displays.

    Use in: Profile grid, list views
    """
    id: int
    icon: str                    # Emoji
    rarity: BadgeRarity          # For styling
    title: str                   # "Tournament Champion"
    description: str             # "Claimed victory in Speed Test 2026"
    badge_type: str              # CHAMPION, RUNNER_UP, etc.
    badge_category: str          # PLACEMENT, ACHIEVEMENT, etc.
    earned_at: str               # ISO datetime
    is_pinned: bool = False      # User can pin favorites

    class Config:
        from_attributes = True


class BadgeUIExtended(BaseModel):
    """
    Extended badge data with full context.

    Use in: Badge detail modal, showcase
    """
    id: int
    icon: str
    rarity: BadgeRarity
    title: str
    description: str
    badge_type: str
    badge_category: str
    earned_at: str
    is_pinned: bool = False

    # Extended data
    tournament_id: int
    tournament_name: str
    metadata: Optional[Dict] = Field(default=None, description="Extra context (placement, time, etc.)")

    # Progress (for milestone badges)
    progress: Optional[Dict] = Field(
        default=None,
        description="Progress towards next tier (e.g., '5/10 tournaments for Legend')"
    )

    class Config:
        from_attributes = True


# ============================================================================
# BADGE SHOWCASE (Profile Display)
# ============================================================================

class BadgeShowcaseSection(BaseModel):
    """
    Single section in badge showcase.

    Grouped by category or rarity.
    """
    section_title: str           # "Placement Badges", "Rarest Achievements"
    section_icon: Optional[str]  # Optional emoji for section
    badges: List[BadgeUIStandard]
    total_in_category: int       # Total badges in this category
    show_all_link: Optional[str] = None  # Link to see all


class BadgeShowcaseUI(BaseModel):
    """
    Complete badge showcase for profile page.

    Organized into sections with featured/pinned badges at top.
    """
    user_id: int
    total_badges: int
    rarest_badge_rarity: Optional[BadgeRarity] = None

    # Featured section (pinned or rarest)
    featured_badges: List[BadgeUIExtended] = Field(
        default_factory=list,
        description="User's pinned badges or rarest badges (max 3-5)"
    )

    # Sections by category
    sections: List[BadgeShowcaseSection] = Field(
        default_factory=list,
        description="Badge groups (Placement, Achievements, Milestones, etc.)"
    )

    # Quick stats
    stats: Dict[str, int] = Field(
        default_factory=dict,
        description="Badge counts by rarity/category"
    )

    class Config:
        from_attributes = True


# ============================================================================
# BADGE PROGRESS TRACKING
# ============================================================================

class BadgeProgressUI(BaseModel):
    """
    Progress towards earning a badge.

    For milestone badges that have requirements.
    """
    badge_type: str              # TOURNAMENT_VETERAN, TOURNAMENT_LEGEND, etc.
    title: str                   # "Tournament Veteran"
    icon: str                    # 🎖️
    description: str             # "Compete in 5 tournaments"
    rarity: BadgeRarity

    # Progress tracking
    current_value: int           # Current progress (e.g., 3 tournaments)
    required_value: int          # Required to unlock (e.g., 5 tournaments)
    progress_percentage: float   # 60.0 (3/5 * 100)
    is_unlocked: bool            # True if earned

    # Metadata
    unlock_condition: str        # "Participate in 5 tournaments"

    class Config:
        from_attributes = True


class BadgeProgressListUI(BaseModel):
    """
    List of badges with progress.

    Shows both earned and unearned badges with progress bars.
    """
    user_id: int
    badges: List[BadgeProgressUI]

    # Summary
    total_unlocked: int
    total_available: int
    completion_percentage: float

    class Config:
        from_attributes = True


# ============================================================================
# BADGE FILTER & SORT OPTIONS
# ============================================================================

class BadgeFilter(BaseModel):
    """Filter options for badge lists"""
    category: Optional[str] = None       # PLACEMENT, ACHIEVEMENT, etc.
    rarity: Optional[BadgeRarity] = None
    tournament_id: Optional[int] = None
    is_pinned: Optional[bool] = None
    earned_after: Optional[str] = None   # ISO datetime


class BadgeSortOption(str, Enum):
    """Sort options for badge lists"""
    EARNED_DATE_DESC = "earned_date_desc"  # Newest first
    EARNED_DATE_ASC = "earned_date_asc"    # Oldest first
    RARITY_DESC = "rarity_desc"            # Rarest first
    RARITY_ASC = "rarity_asc"              # Common first
    TITLE_ASC = "title_asc"                # Alphabetical


# ============================================================================
# BADGE LIST RESPONSE
# ============================================================================

class BadgeListUI(BaseModel):
    """
    Paginated badge list response.

    Use in: Badge history, tournament results
    """
    user_id: int
    badges: List[BadgeUIStandard]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False

    # Applied filters/sorting
    applied_filter: Optional[BadgeFilter] = None
    applied_sort: BadgeSortOption = BadgeSortOption.EARNED_DATE_DESC

    class Config:
        from_attributes = True


# ============================================================================
# UI ACTION CONTRACTS
# ============================================================================

class PinBadgeRequest(BaseModel):
    """Request to pin/unpin a badge"""
    badge_id: int
    is_pinned: bool


class PinBadgeResponse(BaseModel):
    """Response after pinning/unpinning"""
    success: bool
    badge_id: int
    is_pinned: bool
    message: str


# ============================================================================
# BADGE DETAIL MODAL
# ============================================================================

class BadgeDetailModalUI(BaseModel):
    """
    Full badge details for modal/popup.

    Shows everything about a single badge.
    """
    badge: BadgeUIExtended

    # Context
    tournament_details: Optional[Dict] = Field(
        default=None,
        description="Tournament info (format, date, participants)"
    )

    # Sharing (optional)
    share_url: Optional[str] = None
    share_text: Optional[str] = None

    # Similar badges
    similar_badges: List[BadgeUIMinimal] = Field(
        default_factory=list,
        description="Other badges in same category"
    )

    class Config:
        from_attributes = True


# ============================================================================
# BADGE NOTIFICATION
# ============================================================================

class BadgeNotificationUI(BaseModel):
    """
    Badge notification after earning.

    Shown as toast/popup immediately after tournament completion.
    """
    badge: BadgeUIStandard
    is_new: bool = True
    animation: str = "slide-up"  # Animation type
    auto_dismiss_ms: int = 5000  # Auto-dismiss after 5 seconds

    # Optional message
    congratulations_message: Optional[str] = Field(
        default=None,
        description="Custom message (e.g., 'First tournament badge!')"
    )

    class Config:
        from_attributes = True


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
Example 1: Profile Badge Showcase

GET /api/v1/tournaments/badges/showcase/123

Response:
{
    "user_id": 123,
    "total_badges": 12,
    "rarest_badge_rarity": "EPIC",
    "featured_badges": [
        {
            "id": 1,
            "icon": "🥇",
            "rarity": "EPIC",
            "title": "Tournament Champion",
            "description": "Claimed victory in Speed Test 2026",
            "badge_type": "CHAMPION",
            "badge_category": "PLACEMENT",
            "earned_at": "2026-01-25T15:30:00",
            "is_pinned": true,
            "tournament_id": 42,
            "tournament_name": "Speed Test 2026",
            "metadata": {"placement": 1, "total_participants": 20}
        }
    ],
    "sections": [
        {
            "section_title": "Placement Badges",
            "section_icon": "🏆",
            "badges": [...],
            "total_in_category": 8
        }
    ],
    "stats": {
        "LEGENDARY": 1,
        "EPIC": 3,
        "RARE": 5,
        "UNCOMMON": 2,
        "COMMON": 1
    }
}

Example 2: Badge Progress Tracking

GET /api/v1/tournaments/badges/progress/123

Response:
{
    "user_id": 123,
    "badges": [
        {
            "badge_type": "TOURNAMENT_VETERAN",
            "title": "Tournament Veteran",
            "icon": "🎖️",
            "description": "Compete in 5 tournaments",
            "rarity": "RARE",
            "current_value": 3,
            "required_value": 5,
            "progress_percentage": 60.0,
            "is_unlocked": false,
            "unlock_condition": "Participate in 5 tournaments"
        },
        {
            "badge_type": "TRIPLE_CROWN",
            "title": "Triple Crown",
            "icon": "🔥",
            "description": "Win 3 consecutive tournaments",
            "rarity": "LEGENDARY",
            "current_value": 2,
            "required_value": 3,
            "progress_percentage": 66.7,
            "is_unlocked": false,
            "unlock_condition": "Win 3 tournaments in a row"
        }
    ],
    "total_unlocked": 8,
    "total_available": 15,
    "completion_percentage": 53.3
}
"""
