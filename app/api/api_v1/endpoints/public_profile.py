"""
Public Profile API Endpoints
=============================
FIFA/Football Manager style player profiles for LFA students.
Instructor profiles showing licenses and qualifications.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.dependencies import get_db
from app.models.user import User
from app.models.license import UserLicense

router = APIRouter()


@router.get("/users/{user_id}/profile/lfa-player")
def get_lfa_player_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get FIFA-style LFA Football Player profile

    **Returns:**
    - User basic info (name, email, photo)
    - Position preference
    - 7 football skills with radar chart data
    - Overall rating (0-100)
    - Level & progress
    - Recent assessments
    - Achievements
    """
    try:
        # 1. Get user basic info
        user_result = db.execute(
            text("""
                SELECT id, email, name, date_of_birth, nationality, credit_balance
                FROM users
                WHERE id = :user_id AND is_active = true
            """),
            {"user_id": user_id}
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # 2. Get LFA Player license with skills
        license_result = db.execute(
            text("""
                SELECT
                    lpl.id,                    -- 0
                    lpl.age_group,             -- 1
                    lpl.credit_balance,        -- 2
                    lpl.heading_avg,           -- 3
                    lpl.shooting_avg,          -- 4
                    lpl.crossing_avg,          -- 5
                    lpl.passing_avg,           -- 6
                    lpl.dribbling_avg,         -- 7
                    lpl.ball_control_avg,      -- 8
                    lpl.defending_avg,         -- 9
                    lpl.overall_avg,           -- 10
                    lpl.created_at,            -- 11
                    ul.current_level,          -- 12
                    ul.max_achieved_level,     -- 13
                    ul.motivation_scores       -- 14
                FROM lfa_player_licenses lpl
                JOIN user_licenses ul ON ul.user_id = lpl.user_id
                    AND ul.specialization_type LIKE 'LFA_PLAYER%'
                WHERE lpl.user_id = :user_id
                    AND lpl.is_active = true
                ORDER BY lpl.created_at DESC
                LIMIT 1
            """),
            {"user_id": user_id}
        ).fetchone()

        if not license_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} does not have an active LFA Player license"
            )

        # 3. Get position preference from motivation_scores
        motivation_scores = license_result[14]  # motivation_scores column (index 14)
        position_preference = "Unknown"
        if motivation_scores:
            # motivation_scores is already a dict (JSONB from PostgreSQL)
            position_preference = motivation_scores.get("preferred_position", "Unknown") if isinstance(motivation_scores, dict) else "Unknown"

        # 3b. Calculate correct age_group from user's date_of_birth (always up-to-date!)
        from datetime import datetime
        correct_age_group = "AMATEUR"  # Default
        if user_result[3]:  # date_of_birth exists
            dob = user_result[3]
            today = datetime.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            if age < 7:
                correct_age_group = "PRE"  # 4-6 years
            elif age < 15:
                correct_age_group = "YOUTH"  # 7-14 years
            else:
                correct_age_group = "AMATEUR"  # 15+ years
                # NOTE: PRO is NOT automatic - it's a professional qualification!

        # 4. Get recent skill assessments (last 5)
        assessments_results = db.execute(
            text("""
                SELECT
                    fsa.skill_name,
                    fsa.points_earned,
                    fsa.points_total,
                    fsa.percentage,
                    fsa.assessed_at,
                    u.name as instructor_name
                FROM football_skill_assessments fsa
                JOIN user_licenses ul ON fsa.user_license_id = ul.id
                LEFT JOIN users u ON fsa.assessed_by = u.id
                WHERE ul.user_id = :user_id
                ORDER BY fsa.assessed_at DESC
                LIMIT 5
            """),
            {"user_id": user_id}
        ).fetchall()

        # 5. Build FIFA-style profile
        profile = {
            # Basic Info
            "user_id": user_result[0],
            "email": user_result[1],
            "name": user_result[2] or "Unknown Player",
            "date_of_birth": user_result[3].isoformat() if user_result[3] else None,
            "nationality": user_result[4],

            # Player Info
            "position": position_preference,
            "age_group": correct_age_group,  # Auto-calculated from DOB (always current!)
            "level": license_result[12],      # index 12
            "max_level_achieved": license_result[13],  # index 13

            # Overall Rating (FIFA-style 0-100)
            "overall_rating": round(float(license_result[10]), 1) if license_result[10] else 0.0,  # index 10

            # 7 Football Skills (0-100 scale for radar chart)
            "skills": {
                "heading": round(float(license_result[3]), 1) if license_result[3] else 0.0,        # index 3
                "shooting": round(float(license_result[4]), 1) if license_result[4] else 0.0,       # index 4
                "crossing": round(float(license_result[5]), 1) if license_result[5] else 0.0,       # index 5
                "passing": round(float(license_result[6]), 1) if license_result[6] else 0.0,        # index 6
                "dribbling": round(float(license_result[7]), 1) if license_result[7] else 0.0,      # index 7
                "ball_control": round(float(license_result[8]), 1) if license_result[8] else 0.0,   # index 8
                "defending": round(float(license_result[9]), 1) if license_result[9] else 0.0,      # index 9
            },

            # Recent Assessments
            "recent_assessments": [
                {
                    "skill_name": row[0],
                    "points_earned": row[1],
                    "points_total": row[2],
                    "percentage": round(row[3], 1),
                    "assessed_at": row[4].isoformat() if row[4] else None,
                    "instructor_name": row[5] or "Unknown"
                }
                for row in assessments_results
            ],

            # Credits & Progress
            "credit_balance": user_result[5],  # User's centralized credit balance (index 5)
            "license_created_at": license_result[11].isoformat() if license_result[11] else None,  # index 11
        }

        return profile

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve LFA Player profile: {str(e)}"
        )


@router.get("/users/{user_id}/profile/basic")
def get_basic_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get basic profile for OTHER specializations (GānCuju, Coach, Internship)

    Returns:
    - User basic info
    - Active licenses list
    - Simple stats (no detailed skills)
    """
    try:
        # 1. Get user info
        user_result = db.execute(
            text("""
                SELECT id, email, name, date_of_birth, nationality, credit_balance
                FROM users
                WHERE id = :user_id AND is_active = true
            """),
            {"user_id": user_id}
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # 2. Get all active licenses
        licenses_results = db.execute(
            text("""
                SELECT
                    specialization_type,
                    current_level,
                    max_achieved_level,
                    started_at
                FROM user_licenses
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """),
            {"user_id": user_id}
        ).fetchall()

        profile = {
            "user_id": user_result[0],
            "email": user_result[1],
            "name": user_result[2] or "Unknown User",
            "date_of_birth": user_result[3].isoformat() if user_result[3] else None,
            "nationality": user_result[4],
            "credit_balance": user_result[5],
            "licenses": [
                {
                    "specialization": row[0],
                    "level": row[1],
                    "max_level": row[2],
                    "started_at": row[3].isoformat() if row[3] else None
                }
                for row in licenses_results
            ]
        }

        return profile

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve basic profile: {str(e)}"
        )


@router.get("/users/{user_id}/profile/instructor")
def get_instructor_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get Instructor Profile with all licenses and belt/level information.

    **Returns:**
    - User basic info (name, email, nationality)
    - All licenses with belt/level (PLAYER, COACH, INTERNSHIP)
    - License IDs
    - Availability windows count
    - Total teaching experience
    """
    try:
        # 1. Get user basic info
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found or inactive"
            )

        # 2. Get all user licenses with belt/level info
        licenses = db.query(UserLicense).filter(
            UserLicense.user_id == user_id
        ).all()

        # 3. Format licenses with belt/level names
        formatted_licenses = []
        for lic in licenses:
            license_data = {
                "license_id": lic.id,
                "specialization_type": lic.specialization_type,
                "current_level": lic.current_level,
                "max_achieved_level": lic.max_achieved_level,
                "started_at": lic.started_at.isoformat() if lic.started_at else None,
                "last_advanced_at": lic.last_advanced_at.isoformat() if lic.last_advanced_at else None,
                "is_active": lic.is_active,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                "last_renewed_at": lic.last_renewed_at.isoformat() if lic.last_renewed_at else None,
                "renewal_cost": lic.renewal_cost,
            }

            # Add belt/level display name (NO EMOJI in belt_name, only in belt_emoji)
            if lic.specialization_type == "PLAYER":
                belt_names = {
                    1: "Bamboo Student (White)",
                    2: "Morning Dew (Yellow)",
                    3: "Flexible Reed (Green)",
                    4: "Sky River (Blue)",
                    5: "Strong Root (Brown)",
                    6: "Winter Moon (Dark Gray)",
                    7: "Midnight Guardian (Black)",
                    8: "Dragon Wisdom (Red)"
                }
                belt_emojis = {
                    1: "🤍", 2: "💛", 3: "💚", 4: "💙",
                    5: "🤎", 6: "🩶", 7: "🖤", 8: "❤️"
                }
                license_data["belt_name"] = belt_names.get(lic.current_level, f"Level {lic.current_level}")
                license_data["belt_emoji"] = belt_emojis.get(lic.current_level, "🥋")
            elif lic.specialization_type == "COACH":
                coach_levels = {
                    1: "LFA PRE Assistant",
                    2: "LFA PRE Head",
                    3: "LFA YOUTH Assistant",
                    4: "LFA YOUTH Head",
                    5: "LFA AMATEUR Assistant",
                    6: "LFA AMATEUR Head",
                    7: "LFA PRO Assistant",
                    8: "LFA PRO Head"
                }
                license_data["belt_name"] = coach_levels.get(lic.current_level, f"Level {lic.current_level}")
                license_data["belt_emoji"] = "👨‍🏫"
            elif lic.specialization_type == "INTERNSHIP":
                intern_levels = {
                    1: "Junior Intern",
                    2: "Mid-level Intern",
                    3: "Senior Intern",
                    4: "Lead Intern",
                    5: "Principal Intern"
                }
                intern_emojis = {
                    1: "🔰", 2: "📈", 3: "🎯", 4: "👑", 5: "🚀"
                }
                license_data["belt_name"] = intern_levels.get(lic.current_level, f"Level {lic.current_level}")
                license_data["belt_emoji"] = intern_emojis.get(lic.current_level, "📚")
            else:
                license_data["belt_name"] = f"Level {lic.current_level}"
                license_data["belt_emoji"] = "🎓"

            formatted_licenses.append(license_data)

        # 4. Count availability windows
        from app.models.instructor_assignment import InstructorAvailabilityWindow
        availability_count = db.query(InstructorAvailabilityWindow).filter(
            InstructorAvailabilityWindow.instructor_id == user_id
        ).count()

        # 5. Build profile response
        profile = {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "nationality": user.nationality,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "credit_balance": user.credit_balance,
            "is_active": user.is_active,
            "licenses": formatted_licenses,
            "license_count": len(formatted_licenses),
            "availability_windows_count": availability_count,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        return profile

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve instructor profile: {str(e)}"
        )
