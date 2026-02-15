"""
Database Query Helpers for E2E Tests

Fast, read-only queries for verification.
No ORM overhead - direct psycopg2 for speed.
"""

import os
import psycopg2
from typing import Optional, Dict, Any, List


def get_db_connection():
    """Get database connection from environment."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
    )
    return psycopg2.connect(db_url)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email.

    Returns:
        User dict or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, email, name, role, onboarding_completed
            FROM users
            WHERE email = %s
        """, (email,))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "role": row[3],
                "onboarding_completed": row[4],
            }
        return None

    finally:
        cursor.close()
        conn.close()


def get_user_license(user_id: int, specialization_type: str) -> Optional[Dict[str, Any]]:
    """Get user license by user ID and specialization."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, onboarding_completed, is_active
            FROM user_licenses
            WHERE user_id = %s AND specialization_type = %s
        """, (user_id, specialization_type))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "onboarding_completed": row[1],
                "is_active": row[2],
            }
        return None

    finally:
        cursor.close()
        conn.close()


def get_latest_tournament() -> Optional[Dict[str, Any]]:
    """Get most recently created tournament."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, code, name, status, created_at
            FROM semesters
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "status": row[3],
                "created_at": row[4],
            }
        return None

    finally:
        cursor.close()
        conn.close()


def get_champion_badge(user_id: int) -> Optional[Dict[str, Any]]:
    """Get CHAMPION badge for user (most recent)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                tb.id,
                tb.badge_type,
                tb.badge_metadata,
                s.code AS tournament_code
            FROM tournament_badges tb
            JOIN semesters s ON tb.semester_id = s.id
            WHERE tb.user_id = %s AND tb.badge_type = 'CHAMPION'
            ORDER BY tb.created_at DESC
            LIMIT 1
        """, (user_id,))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "badge_type": row[1],
                "badge_metadata": row[2],  # JSON object
                "tournament_code": row[3],
            }
        return None

    finally:
        cursor.close()
        conn.close()


def count_tables() -> int:
    """Count number of tables in public schema (health check)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        return cursor.fetchone()[0]

    finally:
        cursor.close()
        conn.close()


def get_invitation_code(code: str) -> Optional[Dict[str, Any]]:
    """Get invitation code details."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, code, invited_name, invited_email, is_used, expires_at
            FROM invitation_codes
            WHERE code = %s
        """, (code,))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "code": row[1],
                "invited_name": row[2],
                "invited_email": row[3],
                "is_used": row[4],
                "expires_at": row[5],
            }
        return None

    finally:
        cursor.close()
        conn.close()
