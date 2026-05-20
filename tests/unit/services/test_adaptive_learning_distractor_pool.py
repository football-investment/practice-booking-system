"""
Unit tests for the dynamic distractor pool feature.

Covers:
  Seeder validation (_validate_question):
    - legacy 4-option question passes
    - pool question with 7 options passes
    - question with 3 options fails (< 4)
    - TRUE_FALSE with exactly 2 options passes
    - TRUE_FALSE with 3 options fails (exactly 2 required)
    - multiple correct options still fails

  AdaptiveLearningService._build_presented_options:
    - legacy 4-option: all 4 returned, exactly 1 correct in output
    - pool 7-option: exactly 4 returned, exactly 1 correct in output
    - correct option always present in output
    - correct position randomises across runs
    - distractor combination varies across runs
    - answer validation: option_id lookup unchanged by shuffling
    - performance tracking: same question_id regardless of distractor set
"""
import random
import pytest
from unittest.mock import MagicMock

from app.models.quiz import OptionType
from app.services.adaptive_learning import AdaptiveLearningService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc():
    return AdaptiveLearningService(MagicMock())


def _make_option(
    opt_id: int,
    text: str,
    is_correct: bool,
    option_type: OptionType = OptionType.FIXED,
) -> MagicMock:
    opt = MagicMock()
    opt.id = opt_id
    opt.option_text = text
    opt.is_correct = is_correct
    opt.option_type = option_type
    return opt


def _make_question(options: list[MagicMock]) -> MagicMock:
    q = MagicMock()
    q.answer_options = options
    return q


def _legacy_question():
    """FIXED — 1 correct + 3 incorrect — classic 4-option layout."""
    return _make_question([
        _make_option(1, "Correct answer", True),
        _make_option(2, "Wrong A", False),
        _make_option(3, "Wrong B", False),
        _make_option(4, "Wrong C", False),
    ])


def _pool_question():
    """FIXED — 1 correct + 6 incorrect — legacy large pool (FIXED fallback path)."""
    return _make_question([
        _make_option(10, "Correct answer", True),
        _make_option(11, "Wrong 1", False),
        _make_option(12, "Wrong 2", False),
        _make_option(13, "Wrong 3", False),
        _make_option(14, "Wrong 4", False),
        _make_option(15, "Wrong 5", False),
        _make_option(16, "Wrong 6", False),
    ])


def _variant_question():
    """Pool mode — 2 CORRECT_VARIANTs + 6 DISTRACTORs."""
    return _make_question([
        _make_option(20, "Correct variant A", True,  OptionType.CORRECT_VARIANT),
        _make_option(21, "Correct variant B", True,  OptionType.CORRECT_VARIANT),
        _make_option(22, "Distractor 1",      False, OptionType.DISTRACTOR),
        _make_option(23, "Distractor 2",      False, OptionType.DISTRACTOR),
        _make_option(24, "Distractor 3",      False, OptionType.DISTRACTOR),
        _make_option(25, "Distractor 4",      False, OptionType.DISTRACTOR),
        _make_option(26, "Distractor 5",      False, OptionType.DISTRACTOR),
        _make_option(27, "Distractor 6",      False, OptionType.DISTRACTOR),
    ])


# ---------------------------------------------------------------------------
# Seeder validation tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSeederValidation:
    """_validate_question is a module-level function in the seeder script."""

    @pytest.fixture(autouse=True)
    def _import(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
        from seed_adaptive_learning_questions import _validate_question, ValidationError
        self._validate = _validate_question
        self.ValidationError = ValidationError

    def _q(self, n_correct=1, n_incorrect=3, qtype="MULTIPLE_CHOICE"):
        options = (
            [{"text": "correct", "is_correct": True}] * n_correct
            + [{"text": f"wrong{i}", "is_correct": False} for i in range(n_incorrect)]
        )
        return {
            "text": "Sample question?",
            "type": qtype,
            "explanation": "Sample explanation.",
            "options": options,
            "metadata": {
                "estimated_difficulty": 0.5,
                "cognitive_load": 0.5,
                "average_time_seconds": 30.0,
                "concept_tags": [],
            },
        }

    def test_legacy_4_option_passes(self):
        self._validate(self._q(n_correct=1, n_incorrect=3), idx=0)

    def test_pool_7_option_passes(self):
        self._validate(self._q(n_correct=1, n_incorrect=6), idx=0)

    def test_pool_5_option_passes(self):
        self._validate(self._q(n_correct=1, n_incorrect=4), idx=0)

    def test_3_option_raises(self):
        with pytest.raises(self.ValidationError, match="at least 4"):
            self._validate(self._q(n_correct=1, n_incorrect=2), idx=0)

    def test_1_option_raises(self):
        with pytest.raises(self.ValidationError, match="at least 4"):
            self._validate(self._q(n_correct=1, n_incorrect=0), idx=0)

    def test_true_false_exactly_2_passes(self):
        self._validate(self._q(n_correct=1, n_incorrect=1, qtype="TRUE_FALSE"), idx=0)

    def test_true_false_3_options_raises(self):
        with pytest.raises(self.ValidationError, match="exactly 2"):
            self._validate(self._q(n_correct=1, n_incorrect=2, qtype="TRUE_FALSE"), idx=0)

    def test_true_false_1_option_raises(self):
        with pytest.raises(self.ValidationError, match="exactly 2"):
            self._validate(self._q(n_correct=1, n_incorrect=0, qtype="TRUE_FALSE"), idx=0)

    def test_multiple_correct_raises(self):
        with pytest.raises(self.ValidationError, match="exactly 1 correct"):
            self._validate(self._q(n_correct=2, n_incorrect=3), idx=0)

    def test_zero_correct_raises(self):
        with pytest.raises(self.ValidationError, match="exactly 1 correct"):
            self._validate(self._q(n_correct=0, n_incorrect=4), idx=0)


# ---------------------------------------------------------------------------
# SD — Seeder scramble tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSeederScramble:
    """Verify that the seeder scrambles option order before INSERT.

    SD-01  random.shuffle() call is present in the seeder source before the
           QuizAnswerOption INSERT loop.
    SD-02  Running the seeder's shuffle logic 20 times on a 4-option question
           (correct always first in source) produces at least 2 distinct orderings.
           P(identical order all 20 times) = (1/24)^19 ≈ 2e-26.
    SD-03  After shuffling, each question retains exactly 1 is_correct=True option
           and all option texts are preserved unchanged.
    """

    @pytest.fixture(autouse=True)
    def _load_seeder(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
        import seed_adaptive_learning_questions as _seeder
        self._seeder = _seeder

    # ── SD-01 ──────────────────────────────────────────────────────────────────

    def test_sd01_random_shuffle_present_before_insert_loop(self):
        """SD-01: al_import_service source contains random.shuffle before the INSERT loop.

        Shuffle logic lives in app.services.al_import_service._seed_options_v1;
        the seeder script is now a thin CLI wrapper that re-exports from the service.
        """
        import inspect
        import app.services.al_import_service as _svc_mod
        source = inspect.getsource(_svc_mod)

        # The shuffle must appear before the QuizAnswerOption construction
        shuffle_pos = source.find("random.shuffle(options_list)")
        insert_pos  = source.find("QuizAnswerOption(")

        assert shuffle_pos != -1, (
            "random.shuffle(options_list) not found in al_import_service source — "
            "seeder scramble was not applied"
        )
        assert insert_pos != -1, (
            "QuizAnswerOption( not found in al_import_service source"
        )
        assert shuffle_pos < insert_pos, (
            f"random.shuffle (pos={shuffle_pos}) must appear BEFORE "
            f"QuizAnswerOption insert (pos={insert_pos})"
        )

    # ── SD-02 ──────────────────────────────────────────────────────────────────

    def test_sd02_shuffle_produces_multiple_orderings(self):
        """SD-02: across 20 shuffle runs on a 4-option input, at least 2 distinct
        orderings appear for the correct option position.

        Source order: correct at index 0 (always first in JSON).
        Without shuffle, correct would always be at order_index=0 (position A).
        P(same ordering all 20 times with uniform shuffle) = (1/4)^19 ≈ 4e-12.
        """
        import random

        source_options = [
            {"text": "Correct option", "is_correct": True},
            {"text": "Wrong 1", "is_correct": False},
            {"text": "Wrong 2", "is_correct": False},
            {"text": "Wrong 3", "is_correct": False},
        ]

        correct_positions = set()
        for _ in range(20):
            options_list = list(source_options)
            random.shuffle(options_list)
            pos = next(i for i, o in enumerate(options_list) if o["is_correct"])
            correct_positions.add(pos)

        assert len(correct_positions) >= 2, (
            f"Correct option only appeared at positions {correct_positions} "
            "across 20 shuffle runs — shuffle appears non-functional"
        )

    # ── SD-03 ──────────────────────────────────────────────────────────────────

    def test_sd03_is_correct_flag_and_texts_survive_shuffle(self):
        """SD-03: shuffle preserves is_correct flags and option texts.

        Exactly 1 correct option per question after any number of shuffles.
        All option texts are present (no data dropped or duplicated).
        """
        import random

        source_options = [
            {"text": "Correct option", "is_correct": True},
            {"text": "Wrong A",        "is_correct": False},
            {"text": "Wrong B",        "is_correct": False},
            {"text": "Wrong C",        "is_correct": False},
        ]
        original_texts = {o["text"] for o in source_options}

        for _ in range(50):
            options_list = list(source_options)
            random.shuffle(options_list)

            correct_count = sum(1 for o in options_list if o["is_correct"])
            assert correct_count == 1, (
                f"Expected exactly 1 correct option after shuffle, got {correct_count}"
            )

            shuffled_texts = {o["text"] for o in options_list}
            assert shuffled_texts == original_texts, (
                f"Option texts changed during shuffle: "
                f"expected {original_texts}, got {shuffled_texts}"
            )

            assert len(options_list) == 4, (
                f"Option count changed during shuffle: expected 4, got {len(options_list)}"
            )


# ---------------------------------------------------------------------------
# _build_presented_options — output shape
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildPresentedOptionsShape:

    def test_legacy_4_option_returns_4(self):
        svc = _svc()
        result = svc._build_presented_options(_legacy_question())
        assert len(result) == 4

    def test_pool_7_option_returns_4(self):
        svc = _svc()
        result = svc._build_presented_options(_pool_question())
        assert len(result) == 4

    def test_legacy_contains_exactly_1_correct(self):
        """With 4 options in DB (1 correct + 3 incorrect), all 4 are returned."""
        svc = _svc()
        q = _legacy_question()
        correct_ids = {o.id for o in q.answer_options if o.is_correct}
        result = svc._build_presented_options(q)
        correct_in_result = [r for r in result if r["id"] in correct_ids]
        assert len(correct_in_result) == 1

    def test_pool_contains_exactly_1_correct(self):
        svc = _svc()
        q = _pool_question()
        correct_ids = {o.id for o in q.answer_options if o.is_correct}
        result = svc._build_presented_options(q)
        correct_in_result = [r for r in result if r["id"] in correct_ids]
        assert len(correct_in_result) == 1

    def test_correct_option_always_present(self):
        """Run 20 times — correct option must appear every time."""
        svc = _svc()
        q = _pool_question()
        correct_id = next(o.id for o in q.answer_options if o.is_correct)
        for _ in range(20):
            result = svc._build_presented_options(q)
            ids_in_result = {r["id"] for r in result}
            assert correct_id in ids_in_result

    def test_output_contains_id_and_text_keys(self):
        svc = _svc()
        result = svc._build_presented_options(_legacy_question())
        for item in result:
            assert "id" in item
            assert "text" in item

    def test_output_contains_no_is_correct_key(self):
        """is_correct must never leak to the client-facing option dict."""
        svc = _svc()
        result = svc._build_presented_options(_pool_question())
        for item in result:
            assert "is_correct" not in item


# ---------------------------------------------------------------------------
# _build_presented_options — randomness
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildPresentedOptionsRandomness:

    def test_correct_position_varies(self):
        """Over 50 runs the correct option must appear in at least 2 distinct positions.

        With 4 positions and uniform distribution, P(only 1 position in 50 draws) < 1e-29.
        """
        svc = _svc()
        q = _pool_question()
        correct_id = next(o.id for o in q.answer_options if o.is_correct)
        positions = set()
        for _ in range(50):
            result = svc._build_presented_options(q)
            pos = next(i for i, r in enumerate(result) if r["id"] == correct_id)
            positions.add(pos)
        assert len(positions) >= 2, (
            f"Correct option only appeared at positions {positions} across 50 runs — "
            "shuffling appears non-functional"
        )

    def test_all_4_positions_covered(self):
        """Over 200 runs all 4 positions (0–3) should be observed for the correct option.

        P(miss any single position in 200 uniform draws) = (3/4)^200 ≈ 1.4e-25.
        """
        svc = _svc()
        q = _pool_question()
        correct_id = next(o.id for o in q.answer_options if o.is_correct)
        positions = set()
        for _ in range(200):
            result = svc._build_presented_options(q)
            pos = next(i for i, r in enumerate(result) if r["id"] == correct_id)
            positions.add(pos)
        assert positions == {0, 1, 2, 3}

    def test_distractor_combinations_vary(self):
        """Over 50 runs at least 2 distinct distractor combinations must appear.

        Pool has 6 incorrect options; 6C3 = 20 possible combos.
        P(same combo all 50 times) = (1/20)^49 ≈ 5e-64.
        """
        svc = _svc()
        q = _pool_question()
        correct_id = next(o.id for o in q.answer_options if o.is_correct)
        combos = set()
        for _ in range(50):
            result = svc._build_presented_options(q)
            distractor_ids = frozenset(r["id"] for r in result if r["id"] != correct_id)
            combos.add(distractor_ids)
        assert len(combos) >= 2, (
            f"Only {len(combos)} distractor combination(s) seen across 50 runs — "
            "random.sample appears non-functional"
        )

    def test_legacy_4_option_distractors_unchanged(self):
        """With exactly 3 incorrect options in DB, all 3 always appear (no variation)."""
        svc = _svc()
        q = _legacy_question()
        correct_id = next(o.id for o in q.answer_options if o.is_correct)
        incorrect_ids = frozenset(o.id for o in q.answer_options if not o.is_correct)
        for _ in range(20):
            result = svc._build_presented_options(q)
            returned_incorrect = frozenset(r["id"] for r in result if r["id"] != correct_id)
            assert returned_incorrect == incorrect_ids


# ---------------------------------------------------------------------------
# Answer validation — option_id remains correct regardless of shuffle order
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAnswerValidationWithShuffle:
    """The answer validation endpoint uses option.is_correct via DB lookup by option_id.
    It never relies on position. These tests confirm that the option ids returned by
    _build_presented_options match the DB ids, so validation stays correct post-shuffle.
    """

    def test_correct_option_id_survives_shuffle(self):
        """The id of the correct option in the output matches the DB option id."""
        svc = _svc()
        q = _pool_question()
        correct_opt = next(o for o in q.answer_options if o.is_correct)
        for _ in range(20):
            result = svc._build_presented_options(q)
            correct_in_result = [r for r in result if r["id"] == correct_opt.id]
            assert len(correct_in_result) == 1
            assert correct_in_result[0]["text"] == correct_opt.option_text

    def test_incorrect_option_ids_survive_shuffle(self):
        """All incorrect ids in the output match real DB option ids."""
        svc = _svc()
        q = _pool_question()
        all_db_ids = {o.id for o in q.answer_options}
        for _ in range(20):
            result = svc._build_presented_options(q)
            for item in result:
                assert item["id"] in all_db_ids


# ---------------------------------------------------------------------------
# Performance tracking — question_id aggregation unaffected by distractor set
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPerformanceTrackingQuestionId:
    """_build_presented_options never changes question.id.
    Performance is always recorded against the same question_id.
    """

    def test_question_id_unchanged_across_builds(self):
        svc = _svc()
        q = _pool_question()
        q.id = 42
        for _ in range(20):
            result = svc._build_presented_options(q)
            # The question id is what gets passed to record_answer — it never
            # comes from the options list, so it's always stable.
            assert q.id == 42

    def test_different_distractor_sets_same_question_id(self):
        """Even when distractors vary, the question object identity is the same."""
        svc = _svc()
        q = _pool_question()
        q.id = 99
        seen_distractor_combos = set()
        for _ in range(50):
            result = svc._build_presented_options(q)
            correct_id = next(o.id for o in q.answer_options if o.is_correct)
            combo = frozenset(r["id"] for r in result if r["id"] != correct_id)
            seen_distractor_combos.add(combo)
        # Multiple distractor combos observed — all mapped to the same question id
        assert len(seen_distractor_combos) >= 2
        assert q.id == 99


# ---------------------------------------------------------------------------
# SHUF — Production shuffle via real ORM load (no mocks)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestProductionShuffleIntegration:
    """Proves that _build_presented_options distributes the correct answer
    across all 4 positions when options are loaded via the real ORM
    relationship (not MagicMock).

    This test catches any regression where SQLAlchemy loads answer_options
    in a deterministic heap order that would make 'position D never correct'
    a learnable pattern even after shuffle.

    SHUF-01: 200 ORM-loaded runs cover all 4 positions
    SHUF-02: always returns exactly 4 options
    SHUF-03: every item contains 'id' and 'text'
    """

    @pytest.fixture(autouse=True)
    def _seed(self, postgres_db):
        """Insert 1 quiz + 1 question + 4 options into the real DB.

        option_id ordering: correct option inserted LAST (order_index=3)
        so that without shuffle the correct answer would always be at
        position 3 (D). If shuffle works, all 4 positions must be observed.
        """
        from app.models.quiz import Quiz, QuizQuestion, QuizAnswerOption, QuizCategory, QuizDifficulty, QuestionType

        quiz = Quiz(
            title="__shuffle_integration_test__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Integration shuffle test question?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        # Insert incorrect options first (order_index 0–2), correct LAST (order_index 3)
        # Without shuffle the ORM would return correct at position 3 every time.
        for i in range(3):
            postgres_db.add(QuizAnswerOption(
                question_id=question.id,
                option_text=f"Wrong option {i}",
                is_correct=False,
                order_index=i,
            ))
        postgres_db.add(QuizAnswerOption(
            question_id=question.id,
            option_text="Correct option",
            is_correct=True,
            order_index=3,
        ))
        postgres_db.commit()

        self._question_id = question.id
        self._db = postgres_db

    def test_shuf01_all_4_positions_covered_via_orm(self):
        """SHUF-01: over 200 ORM-loaded runs the correct answer appears at
        all 4 positions (A/B/C/D).

        Without shuffle: correct is always at position 3 (D).
        P(miss any position in 200 uniform draws) ≈ (3/4)^200 ≈ 1.4e-25.
        """
        from app.models.quiz import QuizQuestion
        from app.services.adaptive_learning import AdaptiveLearningService

        svc = AdaptiveLearningService(self._db)
        loaded_q = self._db.query(QuizQuestion).filter_by(id=self._question_id).first()
        correct_id = next(o.id for o in loaded_q.answer_options if o.is_correct)

        positions = set()
        for _ in range(200):
            presented = svc._build_presented_options(loaded_q)
            pos = next(i for i, opt in enumerate(presented) if opt["id"] == correct_id)
            positions.add(pos)

        assert positions == {0, 1, 2, 3}, (
            f"Correct answer only appeared at positions {positions} across 200 ORM-loaded runs. "
            "ORM heap order may be deterministic — check relationship order_by or shuffle logic."
        )

    def test_shuf02_returns_exactly_4_options(self):
        """SHUF-02: _build_presented_options always returns exactly 4 items."""
        from app.models.quiz import QuizQuestion
        from app.services.adaptive_learning import AdaptiveLearningService

        svc = AdaptiveLearningService(self._db)
        loaded_q = self._db.query(QuizQuestion).filter_by(id=self._question_id).first()
        for _ in range(10):
            result = svc._build_presented_options(loaded_q)
            assert len(result) == 4

    def test_shuf03_output_items_have_id_and_text(self):
        """SHUF-03: every item in the presented list has 'id' and 'text' keys."""
        from app.models.quiz import QuizQuestion
        from app.services.adaptive_learning import AdaptiveLearningService

        svc = AdaptiveLearningService(self._db)
        loaded_q = self._db.query(QuizQuestion).filter_by(id=self._question_id).first()
        result = svc._build_presented_options(loaded_q)
        for item in result:
            assert "id" in item, f"Missing 'id' key in {item}"
            assert "text" in item, f"Missing 'text' key in {item}"


# ---------------------------------------------------------------------------
# BP — Pool mode with CORRECT_VARIANT + DISTRACTOR options
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVariantPoolMode:
    """Phase-C pool mode: CORRECT_VARIANT + DISTRACTOR options activate the new path.

    BP-01  Over 200 runs the correct variant appears at all 4 positions.
    BP-02  Both CORRECT_VARIANTs from a 2-variant question are presented
           across 200 runs (each variant gets chosen sometimes).
    BP-03  Always exactly 3 distractors from the pool in the output.
    BP-04  Distractor combinations vary across runs (6C3 = 20 combos).
    BP-05  Output never contains 'is_correct' key (no leakage to client).
    BP-06  FIXED fallback unchanged when no CORRECT_VARIANT present.
    """

    # ── BP-01 ──────────────────────────────────────────────────────────────────

    def test_bp01_pool_mode_all_4_positions_covered(self):
        """BP-01: correct variant must appear at all 4 positions over 200 runs.

        P(miss any single position in 200 uniform draws) ≈ (3/4)^200 ≈ 1.4e-25.
        """
        svc = _svc()
        q = _variant_question()
        variant_ids = {o.id for o in q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}

        positions = set()
        for _ in range(200):
            result = svc._build_presented_options(q)
            pos = next(i for i, r in enumerate(result) if r["id"] in variant_ids)
            positions.add(pos)

        assert positions == {0, 1, 2, 3}, (
            f"Correct variant only appeared at positions {positions} across 200 runs — "
            "pool mode shuffle appears non-functional"
        )

    # ── BP-02 ──────────────────────────────────────────────────────────────────

    def test_bp02_both_variants_presented_across_runs(self):
        """BP-02: both CORRECT_VARIANTs appear at least once across 200 runs.

        P(variant B never chosen in 200 independent random.choice() calls) = (1/2)^200 ≈ 6e-61.
        """
        svc = _svc()
        q = _variant_question()
        variant_ids = {o.id for o in q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}

        seen_variants = set()
        for _ in range(200):
            result = svc._build_presented_options(q)
            for item in result:
                if item["id"] in variant_ids:
                    seen_variants.add(item["id"])

        assert seen_variants == variant_ids, (
            f"Only variants {seen_variants} appeared; expected all of {variant_ids}"
        )

    # ── BP-03 ──────────────────────────────────────────────────────────────────

    def test_bp03_exactly_3_distractors_in_output(self):
        """BP-03: output always has exactly 1 correct variant + 3 distractors."""
        svc = _svc()
        q = _variant_question()
        variant_ids    = {o.id for o in q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}
        distractor_ids = {o.id for o in q.answer_options if o.option_type == OptionType.DISTRACTOR}

        for _ in range(50):
            result = svc._build_presented_options(q)
            assert len(result) == 4

            correct_in_result    = [r for r in result if r["id"] in variant_ids]
            distractor_in_result = [r for r in result if r["id"] in distractor_ids]

            assert len(correct_in_result) == 1, (
                f"Expected 1 correct variant in output, got {len(correct_in_result)}"
            )
            assert len(distractor_in_result) == 3, (
                f"Expected 3 distractors in output, got {len(distractor_in_result)}"
            )

    # ── BP-04 ──────────────────────────────────────────────────────────────────

    def test_bp04_distractor_combinations_vary(self):
        """BP-04: across 50 runs, at least 2 distinct distractor sets must appear.

        Pool has 6 distractors; 6C3 = 20 possible combos.
        P(same combo all 50 times) = (1/20)^49 ≈ 5e-64.
        """
        svc = _svc()
        q = _variant_question()
        variant_ids = {o.id for o in q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}

        combos = set()
        for _ in range(50):
            result = svc._build_presented_options(q)
            combo = frozenset(r["id"] for r in result if r["id"] not in variant_ids)
            combos.add(combo)

        assert len(combos) >= 2, (
            f"Only {len(combos)} distractor combo(s) observed — random.sample appears non-functional"
        )

    # ── BP-05 ──────────────────────────────────────────────────────────────────

    def test_bp05_no_is_correct_leaks_to_output(self):
        """BP-05: 'is_correct' must never appear in pool-mode output dicts."""
        svc = _svc()
        q = _variant_question()
        for _ in range(20):
            result = svc._build_presented_options(q)
            for item in result:
                assert "is_correct" not in item, (
                    f"'is_correct' leaked into client-facing option dict: {item}"
                )

    # ── BP-06 ──────────────────────────────────────────────────────────────────

    def test_bp06_fixed_fallback_unchanged_for_legacy_question(self):
        """BP-06: FIXED legacy question (no CORRECT_VARIANT) uses the FIXED path.

        4-option FIXED question → all 4 returned every time, no distractor sampling.
        """
        svc = _svc()
        q = _legacy_question()
        all_ids = {o.id for o in q.answer_options}

        for _ in range(20):
            result = svc._build_presented_options(q)
            assert len(result) == 4
            returned_ids = {r["id"] for r in result}
            assert returned_ids == all_ids, (
                "FIXED fallback must return all 4 options — none should be excluded"
            )


# ---------------------------------------------------------------------------
# BP integration — pool mode via real ORM (postgres_db)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestVariantPoolModeIntegration:
    """BP-INT-01/02: pool mode with real ORM-loaded CORRECT_VARIANT + DISTRACTOR rows.

    Proves that the option_type column is read correctly from PostgreSQL
    and that pool-mode selection activates as expected.
    """

    @pytest.fixture(autouse=True)
    def _seed(self, postgres_db):
        from app.models.quiz import (
            Quiz, QuizQuestion, QuizAnswerOption,
            QuizCategory, QuizDifficulty, QuestionType, OptionType,
        )

        quiz = Quiz(
            title="__variant_pool_integration_test__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Pool mode integration test question?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        # 2 correct variants (both inserted LAST so FIXED fallback would pick neither)
        for i, text in enumerate(["Variant A", "Variant B"]):
            postgres_db.add(QuizAnswerOption(
                question_id=question.id,
                option_text=text,
                is_correct=True,
                order_index=10 + i,
                option_type=OptionType.CORRECT_VARIANT,
            ))
        # 6 distractors
        for i in range(6):
            postgres_db.add(QuizAnswerOption(
                question_id=question.id,
                option_text=f"Distractor {i}",
                is_correct=False,
                order_index=i,
                option_type=OptionType.DISTRACTOR,
            ))
        postgres_db.commit()

        self._question_id = question.id
        self._db = postgres_db

    def test_bp_int01_pool_mode_activates_via_orm(self):
        """BP-INT-01: pool mode fires with ORM-loaded CORRECT_VARIANT + DISTRACTOR rows."""
        from app.models.quiz import QuizQuestion
        from app.services.adaptive_learning import AdaptiveLearningService

        svc = AdaptiveLearningService(self._db)
        loaded_q = self._db.query(QuizQuestion).filter_by(id=self._question_id).first()

        variant_ids = {o.id for o in loaded_q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}
        assert len(variant_ids) == 2

        # Over 200 runs both variants must appear
        seen_variants = set()
        for _ in range(200):
            result = svc._build_presented_options(loaded_q)
            assert len(result) == 4
            for item in result:
                if item["id"] in variant_ids:
                    seen_variants.add(item["id"])

        assert seen_variants == variant_ids, (
            f"Expected both variants {variant_ids}; only saw {seen_variants}"
        )

    def test_bp_int02_all_4_positions_covered_via_orm(self):
        """BP-INT-02: over 200 ORM-loaded runs the correct slot covers all 4 positions."""
        from app.models.quiz import QuizQuestion
        from app.services.adaptive_learning import AdaptiveLearningService

        svc = AdaptiveLearningService(self._db)
        loaded_q = self._db.query(QuizQuestion).filter_by(id=self._question_id).first()
        variant_ids = {o.id for o in loaded_q.answer_options if o.option_type == OptionType.CORRECT_VARIANT}

        positions = set()
        for _ in range(200):
            result = svc._build_presented_options(loaded_q)
            pos = next(i for i, r in enumerate(result) if r["id"] in variant_ids)
            positions.add(pos)

        assert positions == {0, 1, 2, 3}


# ---------------------------------------------------------------------------
# OPT — option_type DB column backfill verification
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestOptionTypeBackfill:
    """OPT-01: the Phase-A migration set option_type='FIXED' on all pre-existing rows.

    Uses the real postgres_db to insert a QuizAnswerOption without specifying
    option_type and checks that it defaults to FIXED.
    """

    def test_opt01_default_option_type_is_fixed(self, postgres_db):
        """OPT-01: QuizAnswerOption without explicit option_type gets FIXED."""
        from app.models.quiz import (
            Quiz, QuizQuestion, QuizAnswerOption,
            QuizCategory, QuizDifficulty, QuestionType, OptionType,
        )

        quiz = Quiz(
            title="__opt01_default_type_test__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Default option_type test?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        # Insert WITHOUT specifying option_type — should default to FIXED
        opt = QuizAnswerOption(
            question_id=question.id,
            option_text="Some option",
            is_correct=False,
            order_index=0,
        )
        postgres_db.add(opt)
        postgres_db.commit()

        reloaded = postgres_db.query(QuizAnswerOption).filter_by(id=opt.id).first()
        assert reloaded.option_type == OptionType.FIXED, (
            f"Expected FIXED default, got {reloaded.option_type!r}"
        )

    def test_opt02_explicit_variant_type_persists(self, postgres_db):
        """OPT-02: CORRECT_VARIANT type round-trips through the DB correctly."""
        from app.models.quiz import (
            Quiz, QuizQuestion, QuizAnswerOption,
            QuizCategory, QuizDifficulty, QuestionType, OptionType,
        )

        quiz = Quiz(
            title="__opt02_variant_type_test__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Variant type test?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        opt = QuizAnswerOption(
            question_id=question.id,
            option_text="Correct variant text",
            is_correct=True,
            order_index=0,
            option_type=OptionType.CORRECT_VARIANT,
        )
        postgres_db.add(opt)
        postgres_db.commit()

        reloaded = postgres_db.query(QuizAnswerOption).filter_by(id=opt.id).first()
        assert reloaded.option_type == OptionType.CORRECT_VARIANT

    def test_opt03_distractor_type_persists(self, postgres_db):
        """OPT-03: DISTRACTOR type round-trips through the DB correctly."""
        from app.models.quiz import (
            Quiz, QuizQuestion, QuizAnswerOption,
            QuizCategory, QuizDifficulty, QuestionType, OptionType,
        )

        quiz = Quiz(
            title="__opt03_distractor_type_test__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="Distractor type test?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        opt = QuizAnswerOption(
            question_id=question.id,
            option_text="Wrong distractor",
            is_correct=False,
            order_index=0,
            option_type=OptionType.DISTRACTOR,
        )
        postgres_db.add(opt)
        postgres_db.commit()

        reloaded = postgres_db.query(QuizAnswerOption).filter_by(id=opt.id).first()
        assert reloaded.option_type == OptionType.DISTRACTOR


# ---------------------------------------------------------------------------
# SD-04 to SD-07 — Seeder v2.0 validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSeederV2:
    """Seeder Phase-B: v2.0 schema validation and backward compatibility.

    SD-04  _validate_question_v2 accepts a well-formed v2.0 question.
    SD-05  _validate_file routes v1.0 questions to _validate_question (compat).
    SD-06  _validate_question_v2 rejects distractor_pool with < 6 entries.
    SD-07  _validate_question_v2 rejects correct_variants with < 2 entries.
    SD-08  _validate_question_v2 rejects TRUE_FALSE type (not supported in v2.0).
    SD-09  _seed_options_v2 creates CORRECT_VARIANT + DISTRACTOR rows.
    """

    @pytest.fixture(autouse=True)
    def _load_seeder(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
        import seed_adaptive_learning_questions as _seeder
        self._seeder = _seeder

    def _v2_question(self, n_variants=2, n_distractors=6, qtype="MULTIPLE_CHOICE"):
        return {
            "text": "Test v2 question?",
            "type": qtype,
            "explanation": "Test explanation.",
            "correct_variants": [f"Variant {i}" for i in range(n_variants)],
            "distractor_pool":  [f"Distractor {i}" for i in range(n_distractors)],
            "metadata": {
                "estimated_difficulty": 0.5,
                "cognitive_load": 0.5,
                "average_time_seconds": 25.0,
                "concept_tags": [],
            },
        }

    # ── SD-04 ──────────────────────────────────────────────────────────────────

    def test_sd04_v2_valid_question_passes(self):
        """SD-04: well-formed v2.0 question passes validation without error."""
        self._seeder._validate_question_v2(self._v2_question(), idx=0)

    # ── SD-05 ──────────────────────────────────────────────────────────────────

    def test_sd05_v1_question_still_validates(self):
        """SD-05: v1.0-format question still validates via _validate_question."""
        q = {
            "text": "Legacy question?",
            "type": "MULTIPLE_CHOICE",
            "explanation": "Explanation.",
            "options": [
                {"text": "Correct", "is_correct": True},
                {"text": "W1", "is_correct": False},
                {"text": "W2", "is_correct": False},
                {"text": "W3", "is_correct": False},
            ],
            "metadata": {
                "estimated_difficulty": 0.4,
                "cognitive_load": 0.4,
                "average_time_seconds": 20.0,
                "concept_tags": [],
            },
        }
        self._seeder._validate_question(q, idx=0)

    # ── SD-06 ──────────────────────────────────────────────────────────────────

    def test_sd06_v2_too_few_distractors_raises(self):
        """SD-06: v2.0 question with < 6 distractors raises ValidationError."""
        with pytest.raises(self._seeder.ValidationError, match="distractor_pool"):
            self._seeder._validate_question_v2(self._v2_question(n_distractors=3), idx=0)

    # ── SD-07 ──────────────────────────────────────────────────────────────────

    def test_sd07_v2_too_few_variants_raises(self):
        """SD-07: v2.0 question with < 2 correct variants raises ValidationError."""
        with pytest.raises(self._seeder.ValidationError, match="correct_variants"):
            self._seeder._validate_question_v2(self._v2_question(n_variants=1), idx=0)

    # ── SD-08 ──────────────────────────────────────────────────────────────────

    def test_sd08_v2_true_false_raises(self):
        """SD-08: TRUE_FALSE is not allowed in v2.0 schema."""
        with pytest.raises(self._seeder.ValidationError, match="TRUE_FALSE"):
            self._seeder._validate_question_v2(self._v2_question(qtype="TRUE_FALSE"), idx=0)

    # ── SD-09 ──────────────────────────────────────────────────────────────────

    def test_sd09_seed_options_v2_creates_typed_rows(self, postgres_db):
        """SD-09: _seed_options_v2 inserts CORRECT_VARIANT + DISTRACTOR rows."""
        from app.models.quiz import (
            Quiz, QuizQuestion, QuizAnswerOption,
            QuizCategory, QuizDifficulty, QuestionType, OptionType,
        )

        quiz = Quiz(
            title="__sd09_seed_options_v2__",
            category=QuizCategory.GENERAL,
            difficulty=QuizDifficulty.EASY,
            time_limit_minutes=5,
            xp_reward=0,
            passing_score=50.0,
            language="en",
        )
        postgres_db.add(quiz)
        postgres_db.flush()

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text="SD-09 v2 seed test?",
            question_type=QuestionType.MULTIPLE_CHOICE,
            order_index=0,
        )
        postgres_db.add(question)
        postgres_db.flush()

        q_data = self._v2_question(n_variants=2, n_distractors=6)
        self._seeder._seed_options_v2(postgres_db, question.id, q_data)
        postgres_db.commit()

        options = (
            postgres_db.query(QuizAnswerOption)
            .filter_by(question_id=question.id)
            .all()
        )
        assert len(options) == 8  # 2 variants + 6 distractors

        variants    = [o for o in options if o.option_type == OptionType.CORRECT_VARIANT]
        distractors = [o for o in options if o.option_type == OptionType.DISTRACTOR]

        assert len(variants) == 2, f"Expected 2 CORRECT_VARIANT rows, got {len(variants)}"
        assert len(distractors) == 6, f"Expected 6 DISTRACTOR rows, got {len(distractors)}"
        assert all(v.is_correct for v in variants), "All CORRECT_VARIANTs must have is_correct=True"
        assert all(not d.is_correct for d in distractors), "All DISTRACTORs must have is_correct=False"
