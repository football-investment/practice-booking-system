"""
Unit tests — SandboxTestOrchestrator

Test matrix:
  _build_reward_config:
    B-01  1 skill → weight=1.0, all keys present
    B-02  2 skills → weight=0.5 each

  _get_current_stage:
    GCS-01  empty steps → INITIALIZATION
    GCS-02  "created" in step → TOURNAMENT_CREATION
    GCS-03  "enrolled" in step → ENROLLMENT
    GCS-04  "rankings" in step → RANKING_GENERATION
    GCS-05  "completed" in step → STATUS_TRANSITION
    GCS-06  "rewards" in step → REWARD_DISTRIBUTION
    GCS-07  unknown step → UNKNOWN

  _get_tournament_status:
    GTS-01  no tournament_id → None
    GTS-02  tournament not found → None
    GTS-03  tournament found → status string

  _snapshot_skills_before:
    SSB-01  non-dict profile → defaults 50.0
    SSB-02  exception → defaults 50.0
    SSB-03  success, skill present → extracted level
    SSB-04  success, skill absent → default 50.0

  _generate_rankings:
    GR-01  NORMAL, 4 players
    GR-02  TOP_HEAVY ≥ 3 players
    GR-03  TOP_HEAVY < 3 players (2 players)
    GR-04  BOTTOM_HEAVY, 3 players
    GR-05  unknown distribution → NORMAL formula

  _enroll_participants:
    EP-01  selected_users matching count
    EP-02  selected_users != player_count → override
    EP-03  no selected_users, seed users found
    EP-04  no selected_users, no seed → TEST_USER_POOL fallback
    EP-05  player_count > pool → ValueError
    EP-06  user has no active license → skipped

  _transition_to_completed:
    TC-01  tournament not found → ValueError
    TC-02  success → status = COMPLETED

  _cleanup_sandbox_data:
    CSD-01  no tournament_id → early return
    CSD-02  success path → all deletes committed
    CSD-03  exception → rollback (no re-raise)

  _create_tournament:
    CT-01  tournament type not found → ValueError
    CT-02  invalid player count → ValueError
    CT-03  success HEAD_TO_HEAD (no game_preset)
    CT-04  individual_config in overrides → INDIVIDUAL_RANKING path, no preset
    CT-05  game_preset_id provided, preset found → preset path with overrides
    CT-05b game_preset_id + individual_ranking → format_config override inside preset
    CT-06  game_preset_id provided, preset NOT found → warning + basic config fallback

  _distribute_rewards:
    DR-01  success path → status REWARDS_DISTRIBUTED, returns result

  _calculate_verdict:
    CV-01  delegates to SandboxVerdictCalculator

  execute_test:
    ET-01  success path (all helpers mocked)
    ET-02  exception path → NOT_WORKING result with error details
"""
import pytest
from unittest.mock import MagicMock, patch, call
from types import SimpleNamespace
from datetime import datetime

from app.services.sandbox_test_orchestrator import SandboxTestOrchestrator, TEST_USER_POOL

_BASE = "app.services.sandbox_test_orchestrator"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _db():
    """Minimal mock DB session."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.first.return_value = None
    q.all.return_value = []
    q.delete.return_value = 0
    db.query.return_value = q
    return db


def _orch(db=None):
    """Create orchestrator with mock DB."""
    return SandboxTestOrchestrator(db or _db())


def _fq(first=None, all_=None):
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ or []
    q.delete.return_value = 0
    return q


# ─── _build_reward_config ────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildRewardConfig:
    def test_single_skill_weight_is_one(self):
        """B-01"""
        o = _orch()
        cfg = o._build_reward_config(["dribbling"])
        assert len(cfg["skill_mappings"]) == 1
        assert cfg["skill_mappings"][0]["skill"] == "dribbling"
        assert cfg["skill_mappings"][0]["weight"] == 1.0
        assert cfg["skill_mappings"][0]["enabled"] is True
        assert cfg["first_place"]["credits"] == 100

    def test_two_skills_both_present(self):
        """B-02: 2 skills → both in mappings, each weight=1.0"""
        o = _orch()
        cfg = o._build_reward_config(["dribbling", "passing"])
        assert len(cfg["skill_mappings"]) == 2
        skills = {m["skill"] for m in cfg["skill_mappings"]}
        assert skills == {"dribbling", "passing"}
        assert cfg["participation"]["credits"] == 10


# ─── _get_current_stage ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetCurrentStage:
    def test_empty_steps_returns_initialization(self):
        """GCS-01"""
        o = _orch()
        assert o._get_current_stage() == "INITIALIZATION"

    def test_created_step(self):
        """GCS-02"""
        o = _orch()
        o.execution_steps = ["Tournament created (ID: 7, Status: IN_PROGRESS)"]
        assert o._get_current_stage() == "TOURNAMENT_CREATION"

    def test_enrolled_step(self):
        """GCS-03"""
        o = _orch()
        o.execution_steps = ["Participants enrolled (4 players)"]
        assert o._get_current_stage() == "ENROLLMENT"

    def test_rankings_step(self):
        """GCS-04: step with 'rankings' but not 'created'/'enrolled'"""
        o = _orch()
        o.execution_steps = ["Rankings persisted (4 participants)"]
        assert o._get_current_stage() == "RANKING_GENERATION"

    def test_completed_step(self):
        """GCS-05"""
        o = _orch()
        o.execution_steps = ["Tournament transitioned to COMPLETED"]
        assert o._get_current_stage() == "STATUS_TRANSITION"

    def test_rewards_step(self):
        """GCS-06"""
        o = _orch()
        o.execution_steps = ["Rewards distributed (4 participants, SANDBOX MODE)"]
        assert o._get_current_stage() == "REWARD_DISTRIBUTION"

    def test_unknown_step_returns_unknown(self):
        """GCS-07"""
        o = _orch()
        o.execution_steps = ["Sandbox data cleaned up (tournament 7 deleted)"]
        assert o._get_current_stage() == "UNKNOWN"


# ─── _get_tournament_status ──────────────────────────────────────────────────

@pytest.mark.unit
class TestGetTournamentStatus:
    def test_no_tournament_id_returns_none(self):
        """GTS-01"""
        o = _orch()
        o.tournament_id = None
        assert o._get_tournament_status() is None

    def test_tournament_not_found_returns_none(self):
        """GTS-02"""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        o = _orch(db)
        o.tournament_id = 99
        assert o._get_tournament_status() is None

    def test_tournament_found_returns_status(self):
        """GTS-03"""
        db = _db()
        t = SimpleNamespace(tournament_status="IN_PROGRESS")
        db.query.return_value.filter.return_value.first.return_value = t
        o = _orch(db)
        o.tournament_id = 7
        assert o._get_tournament_status() == "IN_PROGRESS"


# ─── _snapshot_skills_before ─────────────────────────────────────────────────

@pytest.mark.unit
class TestSnapshotSkillsBefore:
    def test_non_dict_profile_uses_defaults(self):
        """SSB-01"""
        o = _orch()
        with patch(f"{_BASE}.skill_progression_service") as mock_svc:
            mock_svc.get_skill_profile.return_value = "not-a-dict"
            o._snapshot_skills_before([42], ["dribbling"])
        assert o.skills_before_snapshot[42]["dribbling"] == 50.0

    def test_exception_uses_defaults(self):
        """SSB-02"""
        o = _orch()
        with patch(f"{_BASE}.skill_progression_service") as mock_svc:
            mock_svc.get_skill_profile.side_effect = RuntimeError("DB error")
            o._snapshot_skills_before([42], ["passing"])
        assert o.skills_before_snapshot[42]["passing"] == 50.0

    def test_success_extracts_skill_level(self):
        """SSB-03"""
        o = _orch()
        profile = {"skills": {"dribbling": {"current_level": 75.0}}}
        with patch(f"{_BASE}.skill_progression_service") as mock_svc:
            mock_svc.get_skill_profile.return_value = profile
            o._snapshot_skills_before([42], ["dribbling", "passing"])
        assert o.skills_before_snapshot[42]["dribbling"] == 75.0

    def test_missing_skill_uses_default(self):
        """SSB-04"""
        o = _orch()
        profile = {"skills": {}}  # no "passing" key
        with patch(f"{_BASE}.skill_progression_service") as mock_svc:
            mock_svc.get_skill_profile.return_value = profile
            o._snapshot_skills_before([42], ["passing"])
        assert o.skills_before_snapshot[42]["passing"] == 50.0


# ─── _generate_rankings ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestGenerateRankings:
    def _setup(self):
        db = _db()
        o = _orch(db)
        o.tournament_id = 7
        return o, db

    def test_normal_4_players(self):
        """GR-01"""
        o, db = self._setup()
        o._generate_rankings([10, 20, 30, 40], "MEDIUM", "NORMAL")
        assert db.add.call_count == 4
        db.commit.assert_called()
        assert "Rankings created" in o.execution_steps[-1]

    def test_top_heavy_4_players(self):
        """GR-02: ≥ 3 players"""
        o, db = self._setup()
        o._generate_rankings([10, 20, 30, 40], "MEDIUM", "TOP_HEAVY")
        assert db.add.call_count == 4

    def test_top_heavy_2_players(self):
        """GR-03: < 3 players"""
        o, db = self._setup()
        o._generate_rankings([10, 20], "LOW", "TOP_HEAVY")
        assert db.add.call_count == 2

    def test_bottom_heavy_3_players(self):
        """GR-04"""
        o, db = self._setup()
        o._generate_rankings([10, 20, 30], "HIGH", "BOTTOM_HEAVY")
        assert db.add.call_count == 3

    def test_unknown_distribution_uses_normal_formula(self):
        """GR-05: else branch"""
        o, db = self._setup()
        o._generate_rankings([10, 20, 30], "MEDIUM", "ZIGZAG")
        assert db.add.call_count == 3


# ─── _enroll_participants ────────────────────────────────────────────────────

@pytest.mark.unit
class TestEnrollParticipants:
    def test_selected_users_matching_count(self):
        """EP-01"""
        db = _db()
        lic = SimpleNamespace(id=5)
        db.query.return_value.filter.return_value.first.return_value = lic
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.semester_enrollment.SemesterEnrollment"):
            with patch("app.models.semester_enrollment.EnrollmentStatus"):
                result = o._enroll_participants(1, selected_users=[42])
        assert result == [42]
        assert "Participants enrolled" in o.execution_steps[-1]

    def test_selected_users_count_mismatch_uses_actual(self):
        """EP-02: len(selected) != player_count → override"""
        db = _db()
        lic = SimpleNamespace(id=5)
        db.query.return_value.filter.return_value.first.return_value = lic
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.semester_enrollment.SemesterEnrollment"):
            with patch("app.models.semester_enrollment.EnrollmentStatus"):
                result = o._enroll_participants(3, selected_users=[42])  # 1 user, 3 expected
        assert result == [42]

    def test_no_selected_users_seed_found(self):
        """EP-03: @lfa-seed.hu users found → deterministic pool"""
        db = MagicMock()
        seed_rows = [SimpleNamespace(id=10), SimpleNamespace(id=11)]
        q_seed = MagicMock()
        q_seed.join.return_value = q_seed
        q_seed.filter.return_value = q_seed
        q_seed.order_by.return_value = q_seed
        q_seed.all.return_value = seed_rows
        lic = SimpleNamespace(id=5)
        q_lic = MagicMock()
        q_lic.filter.return_value = q_lic
        q_lic.first.return_value = lic
        n = [0]
        def _side(*args):
            n[0] += 1
            return q_seed if n[0] == 1 else q_lic
        db.query.side_effect = _side
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.user.User"), patch("app.models.user.UserRole"):
            with patch("app.models.semester_enrollment.SemesterEnrollment"):
                with patch("app.models.semester_enrollment.EnrollmentStatus"):
                    result = o._enroll_participants(2)
        assert result == [10, 11]

    def test_no_seed_falls_back_to_test_user_pool(self):
        """EP-04: no @lfa-seed.hu users → TEST_USER_POOL"""
        db = MagicMock()
        q_seed = MagicMock()
        q_seed.join.return_value = q_seed
        q_seed.filter.return_value = q_seed
        q_seed.order_by.return_value = q_seed
        q_seed.all.return_value = []
        lic = SimpleNamespace(id=5)
        q_lic = MagicMock()
        q_lic.filter.return_value = q_lic
        q_lic.first.return_value = lic
        n = [0]
        def _side(*args):
            n[0] += 1
            return q_seed if n[0] == 1 else q_lic
        db.query.side_effect = _side
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.user.User"), patch("app.models.user.UserRole"):
            with patch("app.models.semester_enrollment.SemesterEnrollment"):
                with patch("app.models.semester_enrollment.EnrollmentStatus"):
                    result = o._enroll_participants(2)
        assert result == sorted(TEST_USER_POOL)[:2]

    def test_player_count_exceeds_pool_raises(self):
        """EP-05"""
        db = MagicMock()
        q_seed = MagicMock()
        q_seed.join.return_value = q_seed
        q_seed.filter.return_value = q_seed
        q_seed.order_by.return_value = q_seed
        q_seed.all.return_value = []
        db.query.return_value = q_seed
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.user.User"), patch("app.models.user.UserRole"):
            with pytest.raises(ValueError, match="Cannot select"):
                o._enroll_participants(999)

    def test_user_without_license_skipped(self):
        """EP-06: no active license → no enrollment added"""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        o = _orch(db)
        o.tournament_id = 7
        result = o._enroll_participants(1, selected_users=[42])
        db.add.assert_not_called()
        assert result == [42]


# ─── _transition_to_completed ────────────────────────────────────────────────

@pytest.mark.unit
class TestTransitionToCompleted:
    def test_tournament_not_found_raises(self):
        """TC-01"""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        o = _orch(db)
        o.tournament_id = 99
        with pytest.raises(ValueError, match="not found"):
            o._transition_to_completed()

    def test_success_sets_completed(self):
        """TC-02"""
        db = _db()
        t = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = t
        o = _orch(db)
        o.tournament_id = 7
        o._transition_to_completed()
        assert t.tournament_status == "COMPLETED"
        db.commit.assert_called()
        assert "COMPLETED" in o.execution_steps[-1]


# ─── _cleanup_sandbox_data ───────────────────────────────────────────────────

@pytest.mark.unit
class TestCleanupSandboxData:
    def test_no_tournament_id_returns_early(self):
        """CSD-01"""
        db = _db()
        o = _orch(db)
        o.tournament_id = None
        o._cleanup_sandbox_data()
        db.commit.assert_not_called()

    def test_success_path_commits(self):
        """CSD-02"""
        db = _db()
        q = MagicMock()
        q.filter.return_value = q
        q.delete.return_value = 0
        db.query.return_value = q
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.tournament_achievement.TournamentParticipation"), \
             patch("app.models.tournament_achievement.TournamentBadge"), \
             patch("app.models.xp_transaction.XPTransaction"), \
             patch("app.models.credit_transaction.CreditTransaction"), \
             patch("app.models.semester_enrollment.SemesterEnrollment"), \
             patch("app.models.game_configuration.GameConfiguration"):
            o._cleanup_sandbox_data()
        db.commit.assert_called()
        assert "cleaned up" in o.execution_steps[-1]

    def test_exception_triggers_rollback_no_reraise(self):
        """CSD-03"""
        db = _db()
        db.query.side_effect = RuntimeError("DB failure")
        o = _orch(db)
        o.tournament_id = 7
        with patch("app.models.tournament_achievement.TournamentParticipation"):
            o._cleanup_sandbox_data()  # should NOT raise
        db.rollback.assert_called()


# ─── _create_tournament ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestCreateTournament:
    def test_tournament_type_not_found_raises(self):
        """CT-01"""
        db = _db()
        db.query.return_value.filter.return_value.first.return_value = None
        o = _orch(db)
        o.test_run_id = "test-123"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with pytest.raises(ValueError, match="Tournament type not found"):
            o._create_tournament("league", ["dribbling"], 4)

    def test_invalid_player_count_raises(self):
        """CT-02"""
        db = _db()
        tt = MagicMock()
        tt.validate_player_count.return_value = (False, "Not enough players")
        db.query.return_value.filter.return_value.first.return_value = tt
        o = _orch(db)
        o.test_run_id = "test-123"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with pytest.raises(ValueError, match="Not enough players"):
            o._create_tournament("league", ["dribbling"], 100)

    def test_success_head_to_head_no_preset(self):
        """CT-03: success HEAD_TO_HEAD without game_preset"""
        db = MagicMock()
        tt = MagicMock()
        tt.validate_player_count.return_value = (True, "")
        tt.format = "league"
        tt.id = 1
        grandmaster = MagicMock()
        grandmaster.id = 3
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            if n[0] == 1:
                q.first.return_value = tt
            else:
                q.first.return_value = grandmaster
            return q
        db.query.side_effect = _side
        mock_tournament = MagicMock()
        mock_tournament.id = 7
        o = _orch(db)
        o.test_run_id = "test-123"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with patch(f"{_BASE}.Semester", return_value=mock_tournament), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.game_configuration.GameConfiguration"), \
             patch("app.models.game_preset.GamePreset"):
            o._create_tournament("league", ["dribbling"], 4)
        assert o.tournament_id == 7
        assert "Tournament created" in o.execution_steps[-1]

    def test_individual_config_in_overrides_no_preset(self):
        """CT-04: individual_config → is_individual_ranking=True, tournament_type_id=None,
        format_key=INDIVIDUAL_RANKING, game_preset_id_value=None"""
        db = MagicMock()
        tt = MagicMock()
        tt.validate_player_count.return_value = (True, "")
        tt.format = "league"
        tt.id = 1
        grandmaster = MagicMock()
        grandmaster.id = 3
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            q.first.return_value = tt if n[0] == 1 else grandmaster
            return q
        db.query.side_effect = _side
        mock_tournament = MagicMock()
        mock_tournament.id = 7
        overrides = {
            "individual_config": {
                "scoring_type": "PLACEMENT",
                "number_of_rounds": 3,
                "measurement_unit": "meters",
                "ranking_direction": "ASC",
            }
        }
        o = _orch(db)
        o.test_run_id = "test-individual"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with patch(f"{_BASE}.Semester", return_value=mock_tournament), \
             patch("app.models.tournament_configuration.TournamentConfiguration") as MockTC, \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.game_configuration.GameConfiguration"), \
             patch("app.models.game_preset.GamePreset"):
            o._create_tournament("league", ["dribbling"], 4, game_config_overrides=overrides)
        # tournament_type_id_value must be None for INDIVIDUAL_RANKING
        call_kwargs = MockTC.call_args[1]
        assert call_kwargs["tournament_type_id"] is None
        assert call_kwargs["scoring_type"] == "PLACEMENT"
        assert call_kwargs["number_of_rounds"] == 3
        assert o.tournament_id == 7

    def test_game_preset_found_with_skill_sim_overrides(self):
        """CT-05: game_preset_id provided, preset found → preset path + skill_config + simulation_config overrides"""
        db = MagicMock()
        tt = MagicMock()
        tt.validate_player_count.return_value = (True, "")
        tt.format = "league"
        tt.id = 1
        grandmaster = MagicMock()
        grandmaster.id = 3
        preset = MagicMock()
        preset.name = "Test Preset"
        preset.game_config = {
            "version": "1.0",
            "skill_config": {"original": True},
            "simulation_config": {"original": True},
            "format_config": {"league": {"ranking_rules": {}}},
        }
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            if n[0] == 1:
                q.first.return_value = tt
            elif n[0] == 2:
                q.first.return_value = grandmaster
            else:
                q.first.return_value = preset
            return q
        db.query.side_effect = _side
        mock_tournament = MagicMock()
        mock_tournament.id = 7
        overrides = {
            "skill_config": {"skills_tested": ["dribbling"]},
            "simulation_config": {"player_selection": "manual"},
        }
        o = _orch(db)
        o.test_run_id = "test-preset"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with patch(f"{_BASE}.Semester", return_value=mock_tournament), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.game_configuration.GameConfiguration") as MockGC, \
             patch("app.models.game_preset.GamePreset"):
            o._create_tournament("league", ["dribbling"], 4,
                                 game_preset_id=99, game_config_overrides=overrides)
        # game_preset_id_value must be set (HEAD_TO_HEAD, not INDIVIDUAL_RANKING)
        gc_call_kwargs = MockGC.call_args[1]
        assert gc_call_kwargs["game_preset_id"] == 99
        assert o.tournament_id == 7

    def test_game_preset_individual_ranking_overrides_format_config(self):
        """CT-05b: game_preset + individual_ranking=True → format_config key replaced with INDIVIDUAL_RANKING"""
        db = MagicMock()
        tt = MagicMock()
        tt.validate_player_count.return_value = (True, "")
        tt.format = "league"
        tt.id = 1
        grandmaster = MagicMock()
        grandmaster.id = 3
        preset = MagicMock()
        preset.name = "Test Preset"
        preset.game_config = {
            "version": "1.0",
            "skill_config": {},
            "format_config": {"league": {"ranking_rules": {"primary": "points"}}},
        }
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            if n[0] == 1:
                q.first.return_value = tt
            elif n[0] == 2:
                q.first.return_value = grandmaster
            else:
                q.first.return_value = preset
            return q
        db.query.side_effect = _side
        mock_tournament = MagicMock()
        mock_tournament.id = 7
        overrides = {
            "individual_config": {
                "scoring_type": "DISTANCE_BASED",
                "number_of_rounds": 1,
            }
        }
        o = _orch(db)
        o.test_run_id = "test-ir-preset"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        game_config_captured = {}
        original_gc = __builtins__  # capture via side_effect below
        with patch(f"{_BASE}.Semester", return_value=mock_tournament), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.game_configuration.GameConfiguration") as MockGC, \
             patch("app.models.game_preset.GamePreset"):
            o._create_tournament("league", ["dribbling"], 4,
                                 game_preset_id=99, game_config_overrides=overrides)
        # game_preset_id_value=None (INDIVIDUAL_RANKING)
        gc_call_kwargs = MockGC.call_args[1]
        assert gc_call_kwargs["game_preset_id"] is None
        # format_config key must be INDIVIDUAL_RANKING (not "league")
        final_cfg = gc_call_kwargs["game_config"]
        assert "INDIVIDUAL_RANKING" in final_cfg["format_config"]
        assert "league" not in final_cfg["format_config"]

    def test_game_preset_not_found_falls_back_to_basic_config(self):
        """CT-06: game_preset_id provided, preset NOT found → warning + build basic config"""
        db = MagicMock()
        tt = MagicMock()
        tt.validate_player_count.return_value = (True, "")
        tt.format = "league"
        tt.id = 1
        grandmaster = MagicMock()
        grandmaster.id = 3
        n = [0]
        def _side(*args):
            n[0] += 1
            q = MagicMock()
            q.filter.return_value = q
            if n[0] == 1:
                q.first.return_value = tt
            elif n[0] == 2:
                q.first.return_value = grandmaster
            else:
                q.first.return_value = None  # preset not found
            return q
        db.query.side_effect = _side
        mock_tournament = MagicMock()
        mock_tournament.id = 7
        o = _orch(db)
        o.test_run_id = "test-no-preset"
        o.start_time = datetime(2026, 3, 1, 10, 0, 0)
        with patch(f"{_BASE}.Semester", return_value=mock_tournament), \
             patch("app.models.tournament_configuration.TournamentConfiguration"), \
             patch("app.models.tournament_reward_config.TournamentRewardConfig"), \
             patch("app.models.game_configuration.GameConfiguration") as MockGC, \
             patch("app.models.game_preset.GamePreset"):
            o._create_tournament("league", ["dribbling"], 4, game_preset_id=999)
        # Must still produce a game_config (fallback to basic)
        gc_call_kwargs = MockGC.call_args[1]
        assert gc_call_kwargs["game_config"] is not None
        assert "format_config" in gc_call_kwargs["game_config"]
        assert o.tournament_id == 7


# ─── _distribute_rewards ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestDistributeRewards:
    def test_success_path_sets_status_and_returns_result(self):
        """DR-01: _distribute_rewards calls orchestrator, sets REWARDS_DISTRIBUTED"""
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.total_participants = 4
        tournament = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = tournament
        o = _orch(db)
        o.tournament_id = 7
        with patch(f"{_BASE}.tournament_reward_orchestrator") as mock_orch:
            mock_orch.distribute_rewards_for_tournament.return_value = mock_result
            result = o._distribute_rewards()
        assert result is mock_result
        assert tournament.tournament_status == "REWARDS_DISTRIBUTED"
        db.commit.assert_called()
        assert "Rewards distributed" in o.execution_steps[-1]
        assert "SANDBOX MODE" in o.execution_steps[-1]
        # Verify is_sandbox_mode=True was passed
        call_kwargs = mock_orch.distribute_rewards_for_tournament.call_args[1]
        assert call_kwargs["is_sandbox_mode"] is True
        assert call_kwargs["tournament_id"] == 7


# ─── _calculate_verdict ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestCalculateVerdict:
    def test_delegates_to_verdict_calculator(self):
        """CV-01: _calculate_verdict creates SandboxVerdictCalculator and delegates"""
        o = _orch()
        o.tournament_id = 7
        mock_verdict = {"verdict": "WORKING", "skill_progression": {}}
        mock_calc = MagicMock()
        mock_calc.calculate_verdict.return_value = mock_verdict
        with patch("app.services.sandbox_verdict_calculator.SandboxVerdictCalculator",
                   return_value=mock_calc):
            result = o._calculate_verdict(
                user_ids=[42, 43],
                skills_to_test=["dribbling"],
                distribution_result=MagicMock(total_participants=2),
                skills_before_snapshot={42: {"dribbling": 60.0}},
            )
        assert result is mock_verdict
        mock_calc.calculate_verdict.assert_called_once_with(
            tournament_id=7,
            expected_participant_count=2,
            skills_to_test=["dribbling"],
            distribution_result=mock_calc.calculate_verdict.call_args[1]["distribution_result"],
            skills_before_snapshot={42: {"dribbling": 60.0}},
        )


# ─── execute_test ────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestExecuteTest:
    def _mocked_orch(self):
        o = _orch()
        o._create_tournament = MagicMock()
        o._enroll_participants = MagicMock(return_value=[42, 43])
        o._snapshot_skills_before = MagicMock()
        o._generate_rankings = MagicMock()
        o._transition_to_completed = MagicMock()
        o._distribute_rewards = MagicMock(
            return_value=MagicMock(total_participants=2)
        )
        o._calculate_verdict = MagicMock(return_value={
            "verdict": "WORKING",
            "skill_progression": {},
            "top_performers": [],
            "bottom_performers": [],
            "insights": []
        })
        o._cleanup_sandbox_data = MagicMock()
        o.tournament_id = 7
        return o

    def test_success_path_returns_complete_result(self):
        """ET-01"""
        o = self._mocked_orch()
        result = o.execute_test("league", ["dribbling"], 2)
        assert result["verdict"] == "WORKING"
        assert result["tournament"]["id"] == 7
        assert result["tournament"]["type"] == "LEAGUE"
        assert result["export_data"]["pdf_ready"] is True
        assert "steps_completed" in result["execution_summary"]
        o._cleanup_sandbox_data.assert_called_once()

    def test_exception_path_returns_not_working(self):
        """ET-02"""
        o = self._mocked_orch()
        o._create_tournament.side_effect = RuntimeError("Tournament creation failed")
        result = o.execute_test("league", ["dribbling"], 2)
        assert result["verdict"] == "NOT_WORKING"
        assert result["export_data"]["pdf_ready"] is False
        assert result["error"]["message"] == "Tournament creation failed"
        assert result["tournament"]["type"] == "LEAGUE"
        assert len(result["insights"]) == 2  # ERROR + Error message
        assert result["insights"][0]["severity"] == "ERROR"
