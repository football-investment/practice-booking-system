"""
Golden Flow Demo — Full Team Journey (All 4 Roles, One Video)
=============================================================

Business proof: one complete recording that shows every role transition
in the team credit + invite flow.

  👤 Student (future Captain)
       → /tournaments/{id}/team/create
       → submits form (100 credits deducted on-screen)
       → redirected to team dashboard

  👤 Captain
       → live-search for invitee by name
       → sends invite → pending invite appears in table

  👤 Invitee
       → /teams/invites — invite card visible (team name + captain name)
       → clicks Accept → confirmation shown

  👑 Admin
       → browser fetch to POST /admin/tournaments/{id}/teams/{id}/members
       → player added without any invite

  DB assertions after each step.

─────────────────────────────────────────────────────────────────────────────
Run modes
─────────────────────────────────────────────────────────────────────────────
  CI (headless, video recorded):
      PLAYWRIGHT_VIDEO_DIR=test-results/videos/golden-flow \\
      PYTHONPATH=. pytest tests/e2e/admin_ui/test_team_golden_flow.py -v -s

  Local demo (headed, slow — shows every click):
      PYTEST_HEADLESS=false PYTEST_SLOW_MO=300 \\
      PLAYWRIGHT_VIDEO_DIR=test-results/videos/golden-flow \\
      PYTHONPATH=. pytest tests/e2e/admin_ui/test_team_golden_flow.py -v -s

  Local quick sanity (headless, no video):
      PYTHONPATH=. pytest tests/e2e/admin_ui/test_team_golden_flow.py -v -s
"""
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterStatus, SemesterCategory
from app.models.tournament_configuration import TournamentConfiguration
from app.models.team import TeamMember, TeamInvite
from app.services.tournament import team_service
from tests.factories.game_factory import TournamentFactory

# ── Config ──────────────────────────────────────────────────────────────────

APP_URL       = os.environ.get("API_URL", "http://localhost:8000")
ADMIN_EMAIL   = os.environ.get("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

_STUDENT_PASSWORD = "E2EGolden1234!"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ss(page, step: str) -> None:
    ts = datetime.now().strftime("%H%M%S")
    (SCREENSHOTS_DIR / f"{ts}_GF_{step}.png").write_bytes(
        page.screenshot(full_page=True)
    )


def _login(page, email: str, password: str = _STUDENT_PASSWORD) -> None:
    page.goto(f"{APP_URL}/login")
    page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", password)
    page.click("button[type=submit]")
    page.wait_for_url(f"{APP_URL}/dashboard*", timeout=10_000)


def _logout(page) -> None:
    page.goto(f"{APP_URL}/logout")
    page.wait_for_url(f"{APP_URL}/login*", timeout=8_000)


def _make_student(
    db: Session, suffix: str, label: str, credit_balance: int = 0
) -> User:
    user = User(
        email=f"e2etgt-golden-{label}-{suffix}@lfa-test.com",
        name=f"GF {label.title()} {suffix[:4]}",
        password_hash=get_password_hash(_STUDENT_PASSWORD),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=credit_balance,
        payment_verified=True,
        date_of_birth=datetime(2000, 6, 15, tzinfo=timezone.utc),
    )
    db.add(user)
    db.flush()
    return user


def _make_license(
    db: Session, user: User, credit_balance: int
) -> UserLicense:
    lic = UserLicense(
        user_id=user.id,
        specialization_type="LFA_FOOTBALL_PLAYER",
        current_level=1, max_achieved_level=1,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True, onboarding_completed=True,
        payment_verified=True, credit_balance=credit_balance,
    )
    db.add(lic)
    db.flush()
    return lic


def _make_tournament(db: Session, suffix: str) -> Semester:
    tt = TournamentFactory.ensure_tournament_type(db, code=f"tt-gf-{suffix[:6]}")
    t = Semester(
        code=f"GF-DEMO-{suffix[:8].upper()}",
        name=f"Golden Flow Demo Cup {suffix[:4]}",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        tournament_status="ENROLLMENT_OPEN",
        age_group="YOUTH",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 8),
        enrollment_cost=0,
        specialization_type="LFA_FOOTBALL_PLAYER",
    )
    db.add(t)
    db.flush()
    cfg = TournamentConfiguration(
        semester_id=t.id,
        tournament_type_id=tt.id,
        participant_type="TEAM",
        max_players=64,
        parallel_fields=1,
        sessions_generated=False,
        team_enrollment_cost=100,
    )
    db.add(cfg)
    db.commit()
    db.refresh(t)
    return t


def _cleanup(db: Session, user_ids: list[int]) -> None:
    from app.models.team import Team, TournamentTeamEnrollment
    from app.models.credit_transaction import CreditTransaction

    db.query(TeamMember).filter(
        TeamMember.user_id.in_(user_ids)
    ).delete(synchronize_session=False)

    team_ids = [
        r[0] for r in db.query(Team.id).filter(
            Team.captain_user_id.in_(user_ids)
        ).all()
    ]
    if team_ids:
        db.query(TeamInvite).filter(
            TeamInvite.team_id.in_(team_ids)
        ).delete(synchronize_session=False)
        db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.team_id.in_(team_ids)
        ).delete(synchronize_session=False)
        db.query(Team).filter(
            Team.id.in_(team_ids)
        ).delete(synchronize_session=False)

    for uid in user_ids:
        db.query(CreditTransaction).filter(
            CreditTransaction.user_id == uid
        ).delete(synchronize_session=False)

    db.query(UserLicense).filter(
        UserLicense.user_id.in_(user_ids)
    ).delete(synchronize_session=False)
    db.query(User).filter(
        User.id.in_(user_ids)
    ).delete(synchronize_session=False)
    db.commit()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def golden_users(db_session: Session):
    """
    Four actors for the golden flow:
      captain  — 500 user / 300 license credits (enough to pay 100)
      invitee  — 0 credits
      player   — 0 credits (for admin bypass)
      tournament — TEAM type, cost=100
    """
    suffix = uuid.uuid4().hex[:8]

    captain = _make_student(db_session, suffix, "capt",  credit_balance=500)
    invitee = _make_student(db_session, suffix, "inv",   credit_balance=0)
    player  = _make_student(db_session, suffix, "plyr",  credit_balance=0)

    _make_license(db_session, captain, credit_balance=300)
    _make_license(db_session, invitee, credit_balance=0)
    _make_license(db_session, player,  credit_balance=0)

    tournament = _make_tournament(db_session, suffix)

    yield captain, invitee, player, tournament

    _cleanup(db_session, [captain.id, invitee.id, player.id])


# ── Golden Flow Test ──────────────────────────────────────────────────────────

class TestGoldenTeamFlow:
    """
    GF-01  Complete team journey — all 4 roles in one browser session.

    This is the visual business proof: one recording shows every user type
    interacting with the team flow from start to finish.
    """

    def test_gf_01_complete_team_journey(
        self, page, golden_users, db_session: Session
    ):
        """
        Full golden flow:

          ① Student → create team (100 credits deducted, shown in UI)
          ② Captain → search invitee by name → send invite
          ③ Invitee → see invite card → accept → become TeamMember
          ④ Admin   → bypass add player directly (no invite created)

        Steps are numbered GF-01..GF-12 for artifact cross-reference.
        """
        captain, invitee, player, tournament = golden_users

        # ── ① Student: Create Team (credit deduction) ────────────────────────

        # GF-01: Captain logs in
        _login(page, captain.email)
        _ss(page, "01_captain_login")

        # GF-02: Navigate to team create form
        page.goto(f"{APP_URL}/tournaments/{tournament.id}/team/create")
        page.wait_for_load_state("networkidle")
        _ss(page, "02_create_form")

        content = page.content()
        assert "Golden Flow Demo Cup" in content, "Tournament name not on form"
        assert "100" in content and "credits" in content.lower(), \
            "Cost badge (100 credits) missing"

        # GF-03: Submit form → team created
        page.fill("input[name=name]", "Golden Dragons FC")
        page.click("button[type=submit]")
        page.wait_for_url(f"{APP_URL}/teams/*", timeout=8_000)
        _ss(page, "03_team_dashboard")

        team_url = page.url
        team_id = int(team_url.split("/teams/")[1].split("?")[0])

        content = page.content()
        assert "Golden Dragons FC" in content
        assert captain.name in content
        assert "Captain" in content

        # DB: credit deducted
        db_session.expire_all()
        lic = db_session.query(UserLicense).filter(
            UserLicense.user_id == captain.id, UserLicense.is_active == True
        ).first()
        assert lic is not None
        assert lic.credit_balance == 200, (
            f"Expected 300-100=200 credits after team creation, got {lic.credit_balance}"
        )

        # ── ② Captain: Search + Invite ────────────────────────────────────────

        # GF-04: Search for invitee
        page.fill("#user-search", invitee.name[:10])
        page.wait_for_timeout(600)
        page.wait_for_selector(
            "#search-results .result-item[data-id]", timeout=5_000
        )
        _ss(page, "04_search_results")

        # GF-05: Select + send invite
        page.click(f"#search-results .result-item[data-id='{invitee.id}']")
        assert invitee.name in page.inner_text("#selected-user-name")
        page.click("#invite-btn")
        page.wait_for_url(f"{APP_URL}/teams/{team_id}?msg=*", timeout=6_000)
        page.wait_for_load_state("networkidle")
        _ss(page, "05_invite_sent")

        content = page.content()
        assert invitee.name in content, "Invitee name must appear in Pending Invites table"

        # DB: TeamInvite PENDING exists
        db_session.expire_all()
        invite = db_session.query(TeamInvite).filter(
            TeamInvite.team_id == team_id,
            TeamInvite.invited_user_id == invitee.id,
            TeamInvite.status == "PENDING",
        ).first()
        assert invite is not None, "TeamInvite PENDING must exist after browser invite"

        # GF-06: Captain logs out
        _logout(page)
        _ss(page, "06_captain_logged_out")

        # ── ③ Invitee: Accept Invite ──────────────────────────────────────────

        # GF-07: Invitee logs in
        _login(page, invitee.email)
        page.goto(f"{APP_URL}/teams/invites")
        page.wait_for_load_state("networkidle")
        _ss(page, "07_invitee_invite_list")

        content = page.content()
        assert "Golden Dragons FC" in content, "Team name not on invitee's invite list"
        assert captain.name in content, "Captain name not shown on invite card"

        # GF-08: Accept
        page.click("button:has-text('Accept')")
        page.wait_for_url(f"{APP_URL}/teams/invites?*", timeout=8_000)
        page.wait_for_load_state("networkidle")
        _ss(page, "08_invite_accepted")

        content = page.content()
        assert "joined" in content.lower() or "No pending invites" in content

        # DB: invitee is now TeamMember(PLAYER)
        db_session.expire_all()
        member = db_session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == invitee.id,
            TeamMember.is_active == True,
        ).first()
        assert member is not None, "Invitee must be active TeamMember after accept"
        assert member.role == "PLAYER", f"Expected PLAYER role, got {member.role}"

        # GF-09: Invitee logs out
        _logout(page)
        _ss(page, "09_invitee_logged_out")

        # ── ④ Admin: Bypass Add (no invite) ───────────────────────────────────

        # GF-10: Admin logs in
        _login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
        _ss(page, "10_admin_login")
        assert "/dashboard" in page.url

        # GF-11: Admin directly adds player via fetch (no invite flow)
        result = page.evaluate(f"""
            async () => {{
                const csrf = (document.cookie.split('; ')
                    .find(r => r.startsWith('csrf_token=')) || '').split('=')[1] || '';
                const body = new URLSearchParams();
                body.append('user_id', '{player.id}');
                const resp = await fetch(
                    '/admin/tournaments/{tournament.id}/teams/{team_id}/members',
                    {{
                        method: 'POST',
                        headers: {{ 'X-CSRF-Token': csrf }},
                        body: body,
                        redirect: 'follow',
                        credentials: 'include',
                    }}
                );
                return {{ status: resp.status, url: resp.url }};
            }}
        """)
        _ss(page, "11_admin_bypass_add")

        assert result["status"] == 200, (
            f"Admin add-member returned {result['status']}: {result['url']}"
        )

        # DB: player is TeamMember, no TeamInvite
        db_session.expire_all()
        admin_member = db_session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == player.id,
            TeamMember.is_active == True,
        ).first()
        assert admin_member is not None, "Player must be TeamMember after admin bypass"

        no_invite = db_session.query(TeamInvite).filter(
            TeamInvite.team_id == team_id,
            TeamInvite.invited_user_id == player.id,
        ).first()
        assert no_invite is None, "Admin bypass must NOT create a TeamInvite"

        # GF-12: Final team dashboard (admin view — navigate to team page)
        page.goto(f"{APP_URL}/teams/{team_id}")
        page.wait_for_load_state("networkidle")
        _ss(page, "12_final_team_state")

        # ── Summary ───────────────────────────────────────────────────────────

        print(
            f"\n  ✅ GOLDEN FLOW COMPLETE\n"
            f"     team_id={team_id}  tournament={tournament.name}\n"
            f"\n"
            f"     ① Student → team created (100 credits deducted, balance: 300→200)\n"
            f"     ② Captain → invite sent to {invitee.email}\n"
            f"     ③ Invitee → accepted, role=PLAYER  (TeamMember id={member.id})\n"
            f"     ④ Admin   → {player.email} added directly (no TeamInvite)\n"
            f"\n"
            f"     Screenshots → tests/e2e/admin_ui/screenshots/GF_*.png"
        )
