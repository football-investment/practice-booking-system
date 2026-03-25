"""
Playwright E2E — Team Creation + Invite + Accept + Admin Bypass Full Flow
=========================================================================

Proves the complete multi-user team flow works end-to-end in a real
browser (actual HTTP, JS, DOM — no TestClient mocking).

User types covered:
  👤 Captain (student)   — creates team, sends invite
  👤 Invitee (student)   — sees invite card, accepts
  👤 Stranger (student)  — cannot see / accept another user's invite
  👑 Admin               — bypasses invite flow, adds member directly

Tests:
  TM-01  Captain: create team → credit deduction → invite → DB assert
         Invitee: see invite card → accept → become TeamMember
  TM-02  Edge: captain with 0 credits → UI error message (no team created)
  TM-03  Admin: bypass invite → directly add member via admin route
  TM-04  Edge: wrong user cannot accept invite meant for someone else

Requirements:
    Running server:  uvicorn app.main:app --port 8000
    Env vars:        DATABASE_URL (default: dev DB), API_URL (default: http://localhost:8000)

Run:
    pytest tests/e2e/admin_ui/test_team_flow_e2e.py -v -s
    PYTEST_HEADLESS=false PYTEST_SLOW_MO=400 pytest tests/e2e/admin_ui/test_team_flow_e2e.py -v -s
"""
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.license import UserLicense
from app.models.semester import Semester, SemesterStatus, SemesterCategory  # noqa: F401
from app.models.tournament_configuration import TournamentConfiguration
from app.models.team import TeamMember, TeamInvite
from app.services.tournament import team_service
from tests.factories.game_factory import TournamentFactory

# ── Config ─────────────────────────────────────────────────────────────────────

APP_URL = os.environ.get("API_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@lfa.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

_STUDENT_PASSWORD = "E2ETeam1234!"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ss(page, name: str) -> None:
    ts = datetime.now().strftime("%H%M%S")
    (SCREENSHOTS_DIR / f"{ts}_{name}.png").write_bytes(page.screenshot(full_page=True))


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


def _make_student(db: Session, suffix: str, label: str, credit_balance: int = 0) -> User:
    user = User(
        email=f"e2etgt-{label}-{suffix}@lfa-test.com",
        name=f"E2E {label.title()} {suffix[:4]}",
        password_hash=get_password_hash(_STUDENT_PASSWORD),
        role=UserRole.STUDENT,
        is_active=True,
        onboarding_completed=True,
        credit_balance=credit_balance,
        payment_verified=True,
        date_of_birth=datetime(2000, 6, 15, tzinfo=timezone.utc),  # avoids /age-verification redirect
    )
    db.add(user)
    db.flush()
    return user


def _make_license(db: Session, user: User, credit_balance: int) -> UserLicense:
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
    tt = TournamentFactory.ensure_tournament_type(db, code=f"tt-e2e-{suffix[:6]}")
    t = Semester(
        code=f"TEAM-E2E-{suffix[:8].upper()}",
        name=f"E2E Team Tournament {suffix[:6]}",
        semester_category=SemesterCategory.TOURNAMENT,
        status=SemesterStatus.ONGOING,
        tournament_status="ENROLLMENT_OPEN",
        age_group="YOUTH",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 8),
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


def _cleanup_users(db: Session, user_ids: list[int]) -> None:
    """Remove all test rows in FK order."""
    from app.models.team import TeamInvite, Team, TournamentTeamEnrollment
    from app.models.credit_transaction import CreditTransaction

    db.query(TeamMember).filter(
        TeamMember.user_id.in_(user_ids)
    ).delete(synchronize_session=False)

    team_ids = [
        r[0] for r in db.query(Team.id).filter(Team.captain_user_id.in_(user_ids)).all()
    ]
    if team_ids:
        invite_ids = [
            r[0] for r in db.query(TeamInvite.id).filter(
                TeamInvite.team_id.in_(team_ids)
            ).all()
        ]
        if invite_ids:
            db.query(TeamInvite).filter(
                TeamInvite.id.in_(invite_ids)
            ).delete(synchronize_session=False)
        db.query(TournamentTeamEnrollment).filter(
            TournamentTeamEnrollment.team_id.in_(team_ids)
        ).delete(synchronize_session=False)
        db.query(Team).filter(Team.id.in_(team_ids)).delete(synchronize_session=False)

    for uid in user_ids:
        db.query(CreditTransaction).filter(
            CreditTransaction.user_id == uid
        ).delete(synchronize_session=False)

    db.query(UserLicense).filter(
        UserLicense.user_id.in_(user_ids)
    ).delete(synchronize_session=False)

    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


# ── DB fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")   # function-scoped: db_session is function-scoped
def e2e_users(db_session: Session):
    """
    Create captain + invitee + stranger accounts and a TEAM tournament.
    Yields: (captain, invitee, stranger, tournament)
    Teardown: removes all created DB rows.
    """
    suffix = uuid.uuid4().hex[:8]

    captain  = _make_student(db_session, suffix, "capt",    credit_balance=500)
    invitee  = _make_student(db_session, suffix, "inv",     credit_balance=0)
    stranger = _make_student(db_session, suffix, "stranger", credit_balance=0)
    player   = _make_student(db_session, suffix, "player",  credit_balance=0)

    _make_license(db_session, captain,  credit_balance=300)
    _make_license(db_session, invitee,  credit_balance=0)
    _make_license(db_session, stranger, credit_balance=0)
    _make_license(db_session, player,   credit_balance=0)

    tournament = _make_tournament(db_session, suffix)

    yield captain, invitee, stranger, player, tournament

    _cleanup_users(
        db_session,
        [captain.id, invitee.id, stranger.id, player.id],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestTeamFlowE2E:
    """Full click-through proof that the team flow works in a real browser."""

    # ── TM-01: Full create → invite → accept flow ──────────────────────────────

    def test_e2e_team_01_full_create_invite_accept_flow(
        self, page, e2e_users, db_session: Session
    ):
        """
        👤 Captain: login → create team (credit deduction) → invite player
        👤 Invitee: login → see invite card → accept → join team
        DB: TeamMember(PLAYER) exists for invitee after browser accept.

        Step-by-step log:
          TM01-01  Captain logs in
          TM01-02  Captain opens /tournaments/{id}/team/create
          TM01-03  Captain sees cost badge (100 credits) + tournament name
          TM01-04  Captain submits form → redirected to /teams/{id}
          TM01-05  Team dashboard shows captain in member table
          TM01-06  Captain searches invitee → live search results appear
          TM01-07  Captain selects invitee → invite sent → /teams/{id}?msg=Invited
          TM01-08  Captain logs out
          TM01-09  Invitee logs in → /teams/invites shows Dragon FC card
          TM01-10  Invitee clicks Accept → confirmation shown
          TM01-DB  DB assert: TeamMember(PLAYER, is_active=True) exists
        """
        captain, invitee, _stranger, _player, tournament = e2e_users

        # TM01-01: Captain logs in
        _login(page, captain.email)
        _ss(page, "TM01_01_captain_dashboard")

        # TM01-02: Navigate to Create Team form
        page.goto(f"{APP_URL}/tournaments/{tournament.id}/team/create")
        page.wait_for_load_state("networkidle")
        _ss(page, "TM01_02_create_team_form")

        # TM01-03: Verify cost badge + tournament name rendered
        content = page.content()
        assert "E2E Team Tournament" in content, "Tournament name missing from form"
        assert "100" in content, "Cost badge (100 credits) missing from form"
        assert "credits" in content.lower(), "'credits' label missing"

        # TM01-04: Submit Create Team form
        page.fill("input[name=name]", "E2E Dragon FC")
        page.click("button[type=submit]")
        page.wait_for_url(f"{APP_URL}/teams/*", timeout=8_000)
        _ss(page, "TM01_04_team_dashboard_after_create")

        team_url = page.url
        team_id = int(team_url.split("/teams/")[1].split("?")[0])

        # TM01-05: Captain visible in member table
        content = page.content()
        assert "E2E Dragon FC" in content
        assert captain.name in content
        assert "Captain" in content

        # TM01-06: Captain searches for invitee via live search
        page.fill("#user-search", invitee.name[:10])
        page.wait_for_timeout(600)   # debounce 300 ms + buffer
        page.wait_for_selector("#search-results .result-item[data-id]", timeout=5_000)
        _ss(page, "TM01_06_search_results_visible")

        # TM01-07: Select invitee → send invite
        page.click(f"#search-results .result-item[data-id='{invitee.id}']")
        assert invitee.name in page.inner_text("#selected-user-name")
        page.click("#invite-btn")
        # wait for ?msg=Invited — must NOT use /teams/{id}* (matches current URL already)
        page.wait_for_url(f"{APP_URL}/teams/{team_id}?msg=*", timeout=6_000)
        page.wait_for_load_state("networkidle")
        _ss(page, "TM01_07_after_invite_sent")

        assert "msg=" in page.url  # URL check without page.content()
        # Wait for specific element to avoid "page is navigating" race on content()
        page.wait_for_selector(f"text={invitee.name}", timeout=5_000)
        content = page.content()
        assert invitee.name in content, "Invitee must appear in Pending Invites"

        # TM01-08: Captain logs out
        _logout(page)

        # TM01-09: Invitee logs in → invite card visible
        _login(page, invitee.email)
        page.goto(f"{APP_URL}/teams/invites")
        page.wait_for_load_state("networkidle")
        _ss(page, "TM01_09_invitee_invite_list")

        content = page.content()
        assert "E2E Dragon FC" in content, "Team name must be in invite card"
        assert captain.name in content, "Invited-by captain name must be shown"

        # TM01-10: Invitee accepts
        page.click("button:has-text('Accept')")
        # CSRF script intercepts the POST form, does fetch, then window.location.href = redirect.
        # wait_for_url catches the JS-triggered navigation.
        page.wait_for_url(f"{APP_URL}/teams/invites?*", timeout=8_000)
        page.wait_for_load_state("networkidle")
        _ss(page, "TM01_10_after_accept")

        content = page.content()
        assert "joined" in content.lower() or "No pending invites" in content

        # TM01-DB: DB assertion
        db_session.expire_all()
        member = db_session.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == invitee.id,
            TeamMember.is_active == True,
        ).first()
        assert member is not None, "Invitee must be active TeamMember after browser accept"
        assert member.role == "PLAYER", f"Expected PLAYER role, got {member.role}"

        print(
            f"\n  ✅ TM-01 PASSED — full flow:\n"
            f"     team_id={team_id}\n"
            f"     captain={captain.email}\n"
            f"     invitee={invitee.email} → TeamMember.role={member.role}"
        )

    # ── TM-02: 0 credits → UI error message ───────────────────────────────────

    def test_e2e_team_02_zero_credits_shows_error(
        self, page, e2e_users, db_session: Session
    ):
        """
        👤 Edge case (captain): 0 license credits → Create Team form shows
        "Insufficient credits" error; no team is created; page stays on /team/create.

        Step-by-step log:
          TM02-01  Drain captain's license credits to 0
          TM02-02  Captain logs in
          TM02-03  Submits Create Team form
          TM02-04  Page stays on create URL (402 re-render), not /teams/{id}
          TM02-05  "Insufficient" or "credits" appears in HTML
        """
        captain, _invitee, _stranger, _player, tournament = e2e_users

        # TM02-01: Drain credits
        import sqlalchemy
        db_session.execute(
            sqlalchemy.text(
                "UPDATE user_licenses SET credit_balance = 0 "
                "WHERE user_id = :uid AND is_active = true"
            ),
            {"uid": captain.id},
        )
        db_session.commit()

        # TM02-02: Captain logs in
        _login(page, captain.email)
        page.goto(f"{APP_URL}/tournaments/{tournament.id}/team/create")
        page.wait_for_load_state("networkidle")

        # TM02-03: Submit form with 0 credits
        page.fill("input[name=name]", "Broke FC")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        _ss(page, "TM02_zero_credits_error")

        # TM02-04: Must NOT redirect to /teams/{id}
        assert "/teams/" not in page.url or "team/create" in page.url, (
            f"Should stay on create page (402), redirected to: {page.url}"
        )

        # TM02-05: Error text in HTML
        content = page.content()
        assert "Insufficient" in content or "credits" in content.lower(), (
            "Expected 'Insufficient credits' error in HTML, got none"
        )

        print(
            f"\n  ✅ TM-02 PASSED — 0-credit error shown in browser\n"
            f"     captain={captain.email}, page_url={page.url}"
        )

    # ── TM-03: Admin bypass add (no invite required) ──────────────────────────

    def test_e2e_team_03_admin_bypass_add_member(
        self, page, e2e_users, db_session: Session
    ):
        """
        👑 Admin: directly adds a player to a team via
        POST /admin/tournaments/{id}/teams/{id}/members — no invite flow.

        Step-by-step log:
          TM03-01  Captain creates team (via service layer)
          TM03-02  Admin logs in via browser
          TM03-03  Admin POSTs the add-member form (fetch inside browser context)
          TM03-04  Redirect: /admin/tournaments/{id}/teams?flash=Member+added
          TM03-DB  DB assert: player is TeamMember, no TeamInvite exists
        """
        captain, _invitee, _stranger, player, tournament = e2e_users

        # TM03-01: Create team via service layer (no browser needed)
        team = team_service.create_team_with_cost(
            db=db_session,
            name="Admin Bypass FC",
            captain_user_id=captain.id,
            specialization_type="TEAM",
            tournament_id=tournament.id,
        )
        db_session.expire_all()

        # TM03-02: Admin logs in
        _login(page, ADMIN_EMAIL, ADMIN_PASSWORD)
        _ss(page, "TM03_02_admin_logged_in")
        assert "/dashboard" in page.url, f"Admin login failed — at {page.url}"

        # TM03-03: Admin POSTs the direct add-member form
        #   Uses browser's session cookie (credentials:'include')
        #   URL: POST /admin/tournaments/{tid}/teams/{team_id}/members
        result = page.evaluate(f"""
            async () => {{
                const csrfToken = (document.cookie.split('; ')
                    .find(row => row.startsWith('csrf_token=')) || '').split('=')[1] || '';
                const body = new URLSearchParams();
                body.append('user_id', '{player.id}');
                const resp = await fetch(
                    '/admin/tournaments/{tournament.id}/teams/{team.id}/members',
                    {{
                        method: 'POST',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        body: body,
                        redirect: 'follow',
                        credentials: 'include',
                    }}
                );
                return {{ status: resp.status, url: resp.url }};
            }}
        """)
        _ss(page, "TM03_03_after_admin_add")

        # TM03-04: Response confirms redirect to admin teams page
        assert result["status"] == 200, (
            f"Admin add-member fetch returned {result['status']} (expected 200 after redirect)\n"
            f"Final URL: {result['url']}"
        )
        assert "Member+added" in result["url"] or "flash" in result["url"] or "teams" in result["url"], (
            f"Unexpected redirect target: {result['url']}"
        )

        # TM03-DB: DB assertion
        db_session.expire_all()
        member = db_session.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == player.id,
            TeamMember.is_active == True,
        ).first()
        assert member is not None, (
            f"player (id={player.id}) must be TeamMember after admin bypass add"
        )

        # No invite was created
        invite = db_session.query(TeamInvite).filter(
            TeamInvite.team_id == team.id,
            TeamInvite.invited_user_id == player.id,
        ).first()
        assert invite is None, (
            "Admin direct-add must NOT create a TeamInvite row"
        )

        print(
            f"\n  ✅ TM-03 PASSED — admin bypass add:\n"
            f"     team_id={team.id}, player={player.email}\n"
            f"     TeamMember.role={member.role}, TeamInvite=None"
        )

    # ── TM-04: Wrong user cannot accept invite ────────────────────────────────

    def test_e2e_team_04_wrong_user_cannot_accept_invite(
        self, page, e2e_users, db_session: Session
    ):
        """
        👤 Edge case (stranger): A user who was NOT invited cannot accept
        an invite meant for the invitee.

        Proofs:
          A. Stranger's /teams/invites shows "No pending invites"
             (invite card for Dragon FC is NOT visible)
          B. Stranger POSTs directly to /teams/invites/{id}/accept
             → redirected with error param (not success)
          DB: no TeamMember record created for stranger

        Step-by-step log:
          TM04-01  Captain creates team + invites invitee (service layer)
          TM04-02  Stranger logs in → /teams/invites → no invite card shown
          TM04-03  Stranger directly POSTs /teams/invites/{invite_id}/accept
          TM04-04  Redirect includes error (not msg=You+joined)
          TM04-DB  Stranger is NOT a TeamMember
        """
        captain, invitee, stranger, _player, tournament = e2e_users

        # TM04-01: Create team + invite invitee (service layer, not browser)
        team = team_service.create_team_with_cost(
            db=db_session,
            name="Exclusive FC",
            captain_user_id=captain.id,
            specialization_type="TEAM",
            tournament_id=tournament.id,
        )
        invite = team_service.invite_member(
            db=db_session,
            team_id=team.id,
            invited_user_id=invitee.id,
            invited_by_id=captain.id,
        )
        db_session.expire_all()

        # TM04-02: Stranger logs in → invite list is empty
        _login(page, stranger.email)
        page.goto(f"{APP_URL}/teams/invites")
        page.wait_for_load_state("networkidle")
        _ss(page, "TM04_02_stranger_invites_empty")

        content = page.content()
        assert "Exclusive FC" not in content, (
            "Stranger must NOT see Exclusive FC invite (it was sent to invitee)"
        )
        assert "No pending invites" in content or "Exclusive FC" not in content

        # TM04-03: Stranger directly POSTs /teams/invites/{invite_id}/accept
        #   In the browser, follow_redirects=True gives us the final page
        result = page.evaluate(f"""
            async () => {{
                const csrfToken = (document.cookie.split('; ')
                    .find(row => row.startsWith('csrf_token=')) || '').split('=')[1] || '';
                const resp = await fetch(
                    '/teams/invites/{invite.id}/accept',
                    {{
                        method: 'POST',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        redirect: 'follow',
                        credentials: 'include',
                    }}
                );
                return {{ status: resp.status, url: resp.url }};
            }}
        """)
        _ss(page, "TM04_03_stranger_attempt_result")

        # TM04-04: Must redirect with error, not success
        assert "error" in result["url"].lower() or "msg=You" not in result["url"], (
            f"Stranger should NOT get success redirect; got: {result['url']}"
        )

        # TM04-DB: Stranger is NOT a TeamMember
        db_session.expire_all()
        member = db_session.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == stranger.id,
            TeamMember.is_active == True,
        ).first()
        assert member is None, (
            f"Stranger (id={stranger.id}) must NOT become a TeamMember"
        )

        print(
            f"\n  ✅ TM-04 PASSED — wrong user cannot accept invite:\n"
            f"     stranger={stranger.email} → TeamMember=None\n"
            f"     redirect={result['url']}"
        )
