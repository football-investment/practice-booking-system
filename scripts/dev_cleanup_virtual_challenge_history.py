"""
Dev-only cleanup: remove Virtual Challenge history for the two test users.

Clears VT challenge records, linked attempts, and VT-type notifications so that
a clean challenge card lifecycle test can be run from scratch.

PRESERVED (never touched):
  - users (uid=3 rdias@manchestercity.com, uid=3617 johny7@lfa.com)
  - friendship between them
  - UserLicense, CardDraft, CardTheme, card designs
  - skill taxonomy, game definitions, virtual_training_games
  - reward/credit ledger (xp_transactions, credits)
  - standalone VT attempts NOT linked to any challenge
  - friendship notifications (FRIEND_REQUEST_*)

Usage:
    python scripts/dev_cleanup_virtual_challenge_history.py          # dry-run
    python scripts/dev_cleanup_virtual_challenge_history.py --apply  # execute

Safety:
    - Aborts if ENVIRONMENT not in {development, dev, local, test}
    - Verifies user emails before proceeding
    - Verifies friendship is accepted
    - Lists every ID to be deleted before touching the DB
    - Idempotent: safe to run multiple times
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Constants ─────────────────────────────────────────────────────────────────

TARGET_EMAILS = frozenset({"rdias@manchestercity.com", "johny7@lfa.com"})
_ALLOWED_ENVS = frozenset({"development", "dev", "local", "test"})

_VT_CHALLENGE_NOTIFICATION_TYPES = frozenset({
    # enum .value strings (lowercase) — what Python ORM returns
    "vt_challenge_received",
    "vt_challenge_accepted",
    "vt_challenge_declined",
    "vt_challenge_cancelled",
    "vt_challenge_live_lobby",
    "vt_challenge_completed",
    "vt_challenge_forfeited",
    "vt_challenge_result",
    "vt_challenge_skill_delta",
    "vt_challenge_expired",
})


def _abort(msg: str) -> None:
    print(f"\n❌  ABORT: {msg}")
    sys.exit(1)


def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)


# ── Safety guard ──────────────────────────────────────────────────────────────

def _check_environment() -> None:
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "")).lower().strip()
    if env not in _ALLOWED_ENVS:
        _abort(
            f"ENVIRONMENT={env!r} — script only runs in dev/local/test environments.\n"
            f"  Set ENVIRONMENT=development before running."
        )


# ── Database queries ──────────────────────────────────────────────────────────

def _load_users(db) -> dict[str, object]:
    from app.models.user import User
    users = (
        db.query(User)
        .filter(User.email.in_(TARGET_EMAILS))
        .all()
    )
    by_email = {u.email: u for u in users}
    missing = TARGET_EMAILS - by_email.keys()
    if missing:
        _abort(f"Target users not found in DB: {missing}")
    return by_email


def _check_friendship(db, uid_a: int, uid_b: int) -> None:
    from sqlalchemy import or_, and_
    from app.models.friendship import Friendship, FriendshipStatus
    f = (
        db.query(Friendship)
        .filter(
            or_(
                and_(Friendship.requester_id == uid_a, Friendship.addressee_id == uid_b),
                and_(Friendship.requester_id == uid_b, Friendship.addressee_id == uid_a),
            )
        )
        .first()
    )
    if f is None:
        _abort("No friendship record found between the two target users.")
    if f.status.value != "accepted":
        _abort(f"Friendship exists but status={f.status.value!r} — expected 'accepted'.")
    print(f"  ✓ Friendship id={f.id} status=accepted — will not be touched.")


def _collect_challenge_ids(db, user_ids: list[int]) -> list[int]:
    from sqlalchemy import or_
    from app.models.vt_challenge import VirtualTrainingChallenge
    rows = (
        db.query(VirtualTrainingChallenge.id)
        .filter(
            or_(
                VirtualTrainingChallenge.challenger_id.in_(user_ids),
                VirtualTrainingChallenge.challenged_id.in_(user_ids),
            )
        )
        .all()
    )
    return sorted(r.id for r in rows)


def _collect_linked_attempt_ids(db, challenge_ids: list[int]) -> list[int]:
    """Attempt IDs that are FK-referenced by any of the listed challenges."""
    if not challenge_ids:
        return []
    from app.models.vt_challenge import VirtualTrainingChallenge
    challenges = (
        db.query(
            VirtualTrainingChallenge.challenger_attempt_id,
            VirtualTrainingChallenge.challenged_attempt_id,
        )
        .filter(VirtualTrainingChallenge.id.in_(challenge_ids))
        .all()
    )
    ids: set[int] = set()
    for row in challenges:
        if row.challenger_attempt_id is not None:
            ids.add(row.challenger_attempt_id)
        if row.challenged_attempt_id is not None:
            ids.add(row.challenged_attempt_id)
    return sorted(ids)


def _collect_standalone_attempt_ids(db, user_ids: list[int], linked_ids: list[int]) -> list[int]:
    """VT attempts belonging to the users that are NOT linked to any challenge."""
    from app.models.virtual_training import VirtualTrainingAttempt
    rows = (
        db.query(VirtualTrainingAttempt.id)
        .filter(VirtualTrainingAttempt.user_id.in_(user_ids))
        .all()
    )
    all_ids = {r.id for r in rows}
    return sorted(all_ids - set(linked_ids))


def _collect_vt_notification_ids(db, user_ids: list[int]) -> list[int]:
    """Notification IDs of VT_CHALLENGE_* type for the target users."""
    from app.models.notification import Notification
    rows = (
        db.query(Notification.id, Notification.type)
        .filter(Notification.user_id.in_(user_ids))
        .all()
    )
    target_ids = []
    for row in rows:
        type_str = row.type.value if hasattr(row.type, "value") else str(row.type)
        if type_str in _VT_CHALLENGE_NOTIFICATION_TYPES:
            target_ids.append(row.id)
    return sorted(target_ids)


def _collect_preserved_notification_ids(db, user_ids: list[int]) -> list[int]:
    """Notification IDs that will NOT be deleted (non-VT types)."""
    from app.models.notification import Notification
    rows = (
        db.query(Notification.id, Notification.type)
        .filter(Notification.user_id.in_(user_ids))
        .all()
    )
    keep_ids = []
    for row in rows:
        type_str = row.type.value if hasattr(row.type, "value") else str(row.type)
        if type_str not in _VT_CHALLENGE_NOTIFICATION_TYPES:
            keep_ids.append(row.id)
    return sorted(keep_ids)


# ── Deletion ──────────────────────────────────────────────────────────────────

def _delete_notifications(db, notif_ids: list[int]) -> None:
    from app.models.notification import Notification
    db.query(Notification).filter(Notification.id.in_(notif_ids)).delete(
        synchronize_session=False
    )


def _delete_challenges(db, challenge_ids: list[int]) -> None:
    from app.models.vt_challenge import VirtualTrainingChallenge
    db.query(VirtualTrainingChallenge).filter(
        VirtualTrainingChallenge.id.in_(challenge_ids)
    ).delete(synchronize_session=False)


def _delete_attempts(db, attempt_ids: list[int]) -> None:
    from app.models.virtual_training import VirtualTrainingAttempt
    db.query(VirtualTrainingAttempt).filter(
        VirtualTrainingAttempt.id.in_(attempt_ids)
    ).delete(synchronize_session=False)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(*, apply: bool = False) -> None:
    _check_environment()

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        _section("1 · User verification")
        users_by_email = _load_users(db)
        for email, u in users_by_email.items():
            print(f"  ✓ uid={u.id}  {email}  (nickname={u.nickname})")
        user_ids = [u.id for u in users_by_email.values()]

        _section("2 · Friendship check")
        _check_friendship(db, user_ids[0], user_ids[1])

        _section("3 · Collecting records to delete")

        challenge_ids = _collect_challenge_ids(db, user_ids)
        linked_attempt_ids = _collect_linked_attempt_ids(db, challenge_ids)
        standalone_attempt_ids = _collect_standalone_attempt_ids(db, user_ids, linked_attempt_ids)
        vt_notif_ids = _collect_vt_notification_ids(db, user_ids)
        preserved_notif_ids = _collect_preserved_notification_ids(db, user_ids)

        print(f"\n  TO DELETE:")
        print(f"    vt_challenges              : {challenge_ids if challenge_ids else '(none)'}")
        print(f"    virtual_training_attempts  : {linked_attempt_ids if linked_attempt_ids else '(none)'}")
        print(f"    notifications (VT_CHALLENGE): {vt_notif_ids if vt_notif_ids else '(none)'}")
        print(f"\n  PRESERVED (not touched):")
        print(f"    standalone VT attempts     : {standalone_attempt_ids if standalone_attempt_ids else '(none)'}")
        print(f"    notifications (other types): {preserved_notif_ids if preserved_notif_ids else '(none)'}")
        print(f"    users, friendship, licenses, card drafts, game defs: ALL kept")

        if not challenge_ids and not linked_attempt_ids and not vt_notif_ids:
            print("\n  ✅  DB is already clean — nothing to delete.")
            return

        _section("4 · Execution")

        if not apply:
            print(
                "\n  🔍  DRY-RUN mode — no changes made.\n"
                "\n  To execute the cleanup, run:\n"
                "      python scripts/dev_cleanup_virtual_challenge_history.py --apply\n"
                "\n  ⚠️  Backup tip: before running --apply, snapshot the DB:\n"
                "      pg_dump -h localhost -p 5432 -U postgres lfa_intern_system > /tmp/lfa_intern_system_before_cleanup.sql"
            )
            return

        # Deletion order: notifications → challenges → attempts (FK-safe)
        # challenges FK → attempts ON DELETE SET NULL, so we can delete challenges
        # first (nullifying attempt FKs) or delete challenges while attempts still
        # exist (both orders work; we delete in this order for clarity).

        deleted_notifs = 0
        deleted_challenges = 0
        deleted_attempts = 0

        if vt_notif_ids:
            _delete_notifications(db, vt_notif_ids)
            deleted_notifs = len(vt_notif_ids)
            print(f"  → Deleted {deleted_notifs} VT_CHALLENGE notifications")

        if challenge_ids:
            _delete_challenges(db, challenge_ids)
            deleted_challenges = len(challenge_ids)
            print(f"  → Deleted {deleted_challenges} vt_challenges")

        if linked_attempt_ids:
            _delete_attempts(db, linked_attempt_ids)
            deleted_attempts = len(linked_attempt_ids)
            print(f"  → Deleted {deleted_attempts} virtual_training_attempts")

        db.commit()
        print(f"\n  ✅  Commit OK")

        _section("5 · Post-cleanup audit")
        remaining_challenges = _collect_challenge_ids(db, user_ids)
        remaining_linked    = _collect_linked_attempt_ids(db, remaining_challenges)
        remaining_vt_notifs = _collect_vt_notification_ids(db, user_ids)
        remaining_standalone = _collect_standalone_attempt_ids(db, user_ids, [])

        print(f"  vt_challenges remaining       : {len(remaining_challenges)}")
        print(f"  challenge-linked attempts left : {len(remaining_linked)}")
        print(f"  VT_CHALLENGE notifications left: {len(remaining_vt_notifs)}")
        print(f"  standalone attempts (kept)     : {remaining_standalone}")

        if remaining_challenges or remaining_linked or remaining_vt_notifs:
            print("\n  ⚠️  Some records remain — check for unexpected challenge participants.")
        else:
            print("\n  ✅  Clean state confirmed.")

        _section("Manual validation checklist")
        print(
            "  After cleanup, verify:\n"
            "  1. [ ] New async challenge can be sent (rdias → T1B1K3)\n"
            "  2. [ ] challenge_sent card preview renders (phase=challenge_sent)\n"
            "  3. [ ] challenge_sent card is preview-only (no Download button)\n"
            "  4. [ ] New live challenge can be started and played to completion\n"
            "  5. [ ] completed_score_win preview renders correctly\n"
            "  6. [ ] completed_score_win PNG export downloads successfully\n"
            "  7. [ ] /my-cards/challenge-card shows both challenges in collection\n"
            "  8. [ ] Platform toggle (Post 16:9 ↔ Story 9:16) works on collection page\n"
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dev-only: clean up Virtual Challenge history for test users."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute deletions. Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args()
    run(apply=args.apply)
