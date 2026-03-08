"""
Unit tests for app/api/api_v1/endpoints/game_presets/crud.py
Covers: get_all_presets, get_preset_by_id, get_preset_by_code,
        create_preset, update_preset, soft_delete_preset, hard_delete_preset
All 14 branches exercised.
"""
import pytest
from unittest.mock import MagicMock, call

from app.api.api_v1.endpoints.game_presets.crud import (
    get_all_presets,
    get_preset_by_id,
    get_preset_by_code,
    create_preset,
    update_preset,
    soft_delete_preset,
    hard_delete_preset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(all_val=None, first_val=None):
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = all_val if all_val is not None else []
    q.first.return_value = first_val
    return q


def _preset(pid=1, code="footvolley", name="Footvolley", is_active=True):
    p = MagicMock()
    p.id = pid
    p.code = code
    p.name = name
    p.is_active = is_active
    return p


def _db_q(q):
    db = MagicMock()
    db.query.return_value = q
    return db


def _db_first(first_val=None):
    return _db_q(_q(first_val=first_val))


# ---------------------------------------------------------------------------
# get_all_presets
# ---------------------------------------------------------------------------

class TestGetAllPresets:

    def test_gp01_active_only_true_applies_filter(self):
        """GP-01: active_only=True → filter applied on query."""
        p = _preset()
        q = _q(all_val=[p])
        db = _db_q(q)
        result = get_all_presets(db, active_only=True)
        q.filter.assert_called_once()
        assert len(result) == 1

    def test_gp02_active_only_false_skips_filter(self):
        """GP-02: active_only=False → filter NOT applied."""
        p1 = _preset(pid=1)
        p2 = _preset(pid=2, is_active=False)
        q = _q(all_val=[p1, p2])
        db = _db_q(q)
        result = get_all_presets(db, active_only=False)
        q.filter.assert_not_called()
        assert len(result) == 2

    def test_gp03_empty_result(self):
        """GP-03: no presets in DB → empty list."""
        q = _q(all_val=[])
        db = _db_q(q)
        result = get_all_presets(db, active_only=True)
        assert result == []


# ---------------------------------------------------------------------------
# get_preset_by_id
# ---------------------------------------------------------------------------

class TestGetPresetById:

    def test_gpid01_found(self):
        """GPID-01: preset exists → returns preset."""
        p = _preset()
        db = _db_first(first_val=p)
        result = get_preset_by_id(db, 1)
        assert result is p

    def test_gpid02_not_found(self):
        """GPID-02: preset missing → None."""
        db = _db_first(first_val=None)
        result = get_preset_by_id(db, 999)
        assert result is None


# ---------------------------------------------------------------------------
# get_preset_by_code
# ---------------------------------------------------------------------------

class TestGetPresetByCode:

    def test_gpc01_found(self):
        """GPC-01: code matches → preset returned."""
        p = _preset(code="footvolley")
        db = _db_first(first_val=p)
        result = get_preset_by_code(db, "footvolley")
        assert result is p

    def test_gpc02_not_found(self):
        """GPC-02: code not in DB → None."""
        db = _db_first(first_val=None)
        result = get_preset_by_code(db, "nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# create_preset
# ---------------------------------------------------------------------------

class TestCreatePreset:

    def test_cp01_minimal_required_args(self):
        """CP-01: minimal args → GamePreset added, committed, refreshed."""
        db = MagicMock()
        result = create_preset(
            db=db,
            code="footvolley",
            name="Footvolley",
            game_config={"skill_config": {}},
        )
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_cp02_with_optional_description_and_created_by(self):
        """CP-02: description + created_by → model constructed with these fields."""
        db = MagicMock()
        create_preset(
            db=db,
            code="footvolley",
            name="Footvolley",
            game_config={"skill_config": {}},
            description="A fun beach game",
            created_by=42,
        )
        db.add.assert_called_once()
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# update_preset
# ---------------------------------------------------------------------------

class TestUpdatePreset:

    def _db_for_update(self, preset):
        """DB mock where get_preset_by_id (query.filter.first) returns preset."""
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = preset
        db.query.return_value = q
        return db

    def test_up01_not_found_returns_none(self):
        """UP-01: preset not found → None, no commit."""
        db = self._db_for_update(None)
        result = update_preset(db, preset_id=999)
        assert result is None
        db.commit.assert_not_called()

    def test_up02_name_provided_updates_name(self):
        """UP-02: name is not None → preset.name updated."""
        p = _preset(name="Old")
        db = self._db_for_update(p)
        update_preset(db, preset_id=1, name="New Name")
        assert p.name == "New Name"
        db.commit.assert_called_once()

    def test_up03_description_provided_updates_description(self):
        """UP-03: description is not None → preset.description updated."""
        p = _preset()
        db = self._db_for_update(p)
        update_preset(db, preset_id=1, description="Updated desc")
        assert p.description == "Updated desc"

    def test_up04_game_config_provided_updates_config(self):
        """UP-04: game_config is not None → preset.game_config updated."""
        p = _preset()
        db = self._db_for_update(p)
        new_cfg = {"rules": {"max_points": 15}}
        update_preset(db, preset_id=1, game_config=new_cfg)
        assert p.game_config == new_cfg

    def test_up05_is_active_provided_updates_active(self):
        """UP-05: is_active is not None → preset.is_active updated."""
        p = _preset(is_active=True)
        db = self._db_for_update(p)
        update_preset(db, preset_id=1, is_active=False)
        assert p.is_active is False

    def test_up06_all_none_fields_skipped_still_commits(self):
        """UP-06: all params None → no field assignments, still commits."""
        p = _preset(name="Unchanged")
        db = self._db_for_update(p)
        update_preset(db, preset_id=1)
        assert p.name == "Unchanged"
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# soft_delete_preset
# ---------------------------------------------------------------------------

class TestSoftDeletePreset:

    def _db(self, preset):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = preset
        db.query.return_value = q
        return db

    def test_sd01_found_sets_is_active_false(self):
        """SD-01: delegates to update_preset → is_active=False set."""
        p = _preset(is_active=True)
        db = self._db(p)
        result = soft_delete_preset(db, 1)
        assert p.is_active is False

    def test_sd02_not_found_returns_none(self):
        """SD-02: not found → None."""
        db = self._db(None)
        result = soft_delete_preset(db, 999)
        assert result is None


# ---------------------------------------------------------------------------
# hard_delete_preset
# ---------------------------------------------------------------------------

class TestHardDeletePreset:

    def _db(self, preset):
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = preset
        db.query.return_value = q
        return db

    def test_hd01_not_found_returns_false(self):
        """HD-01: preset not found → False, no delete."""
        db = self._db(None)
        result = hard_delete_preset(db, 999)
        assert result is False
        db.delete.assert_not_called()

    def test_hd02_found_deletes_and_returns_true(self):
        """HD-02: found → db.delete called, committed, returns True."""
        p = _preset()
        db = self._db(p)
        result = hard_delete_preset(db, 1)
        assert result is True
        db.delete.assert_called_once_with(p)
        db.commit.assert_called_once()
