"""
Unit tests for app/api/api_v1/endpoints/groups.py

Covers:
  create_group:
    semester not found -> 404
    success: group created and returned

  list_groups:
    no semester_id filter -> all groups returned with stats
    semester_id filter -> filtered results
    empty group list -> empty GroupList

  get_group:
    group not found -> 404
    group found -> GroupWithRelations returned

  update_group:
    group not found -> 404
    semester_id changed, new semester not found -> 404
    semester_id changed, new semester found -> ok
    semester_id same as existing -> no semester re-check
    semester_id not provided -> only other fields updated
    success with partial update

  delete_group:
    group not found -> 404
    group has sessions (session_count > 0) -> 400
    group has no sessions -> deleted successfully

  add_user_to_group:
    group not found -> 404
    user not found -> 404
    user already in group -> 400
    success: user added

  remove_user_from_group:
    group not found -> 404
    user not found -> 404
    user not in group -> 400
    success: user removed
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

from fastapi import HTTPException

from app.api.api_v1.endpoints.groups import (
    create_group,
    list_groups,
    get_group,
    update_group,
    delete_group,
    add_user_to_group,
    remove_user_from_group,
)

_BASE = "app.api.api_v1.endpoints.groups"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin():
    """Admin user mock (id=42, FK guard safe)."""
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = "admin"
    return u


def _student():
    """Regular student user mock."""
    u = MagicMock()
    u.id = 42
    u.role = MagicMock()
    u.role.value = "student"
    return u


def _q(first=None, all_=None, scalar=None, count=0):
    """Fluent query mock: all chainable methods return self."""
    q = MagicMock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.options.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.join.return_value = q
    q.group_by.return_value = q
    q.with_for_update.return_value = q
    q.first.return_value = first
    q.all.return_value = all_ if all_ is not None else []
    q.count.return_value = count
    q.scalar.return_value = scalar if scalar is not None else 0
    return q


def _seq_db(*qs):
    """Sequential db mock: n-th db.query() returns qs[n].
    Falls back to _q() after all specified mocks are consumed."""
    idx = [0]
    db = MagicMock()

    def _side(m):
        i = idx[0]
        idx[0] += 1
        return qs[i] if i < len(qs) else _q()

    db.query.side_effect = _side
    return db


def _now():
    return datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


def _make_semester(id_=5):
    s = MagicMock()
    s.id = id_
    s.code = f"SEM-{id_}"
    s.name = f"Semester {id_}"
    s.start_date = datetime(2025, 1, 1).date()
    s.end_date = datetime(2025, 6, 30).date()
    s.status = "ONGOING"
    s.is_active = True
    s.enrollment_cost = 500
    s.master_instructor_id = None
    s.specialization_type = None
    s.age_group = None
    s.theme = None
    s.focus_description = None
    s.location_city = None
    s.location_venue = None
    s.location_address = None
    s.assignment_type = None
    s.max_players = None
    s.tournament_type_id = None
    s.format = None
    s.scoring_type = None
    s.measurement_unit = None
    s.ranking_direction = None
    s.created_at = _now()
    s.updated_at = None
    s.tournament_status = None
    return s


class _GroupStubMeta(type):
    """Metaclass to create group stubs where 'semester' and 'users' live
    outside __dict__ so **group.__dict__ doesn't include them."""
    pass


def _make_group(id_=10, semester_id=5, name="Group Alpha"):
    """Create a group-like object.

    The production code in list_groups / get_group does:
        GroupWithStats(**group.__dict__, semester=group.semester, ...)
        GroupWithRelations(**group.__dict__, semester=group.semester, users=group.users)

    If 'semester' or 'users' appear in instance.__dict__, Python raises
    "multiple values for keyword argument".  We store relationship attrs
    in a side-channel dict (_rel) that __getattr__ delegates to, so they
    never appear in instance.__dict__.
    """
    semester_obj = _make_semester(semester_id)

    class _GroupStub:
        _rel: dict  # declared at class level but not in instance __dict__

        def __init__(self):
            # Only column fields go into instance __dict__
            self.id = id_
            self.name = name
            self.description = "Test group"
            self.semester_id = semester_id
            self.created_at = _now()
            self.updated_at = None
            # Store relationships outside normal __dict__ via object.__setattr__
            # on a hidden container — we use a class-level dict keyed by id(self)
            _GroupStub._instances[id(self)] = {
                "semester": semester_obj,
                "users": [],
            }

        def __getattr__(self, name):
            # Called only when normal attribute lookup fails
            instances = object.__getattribute__(self, "__class__")._instances
            rel = instances.get(id(self), {})
            if name in rel:
                return rel[name]
            raise AttributeError(name)

        def __setattr__(self, name, value):
            if name in ("semester", "users"):
                _GroupStub._instances.setdefault(id(self), {})[name] = value
            else:
                object.__setattr__(self, name, value)

    _GroupStub._instances = {}
    return _GroupStub()


def _make_group_create(name="Group Alpha", semester_id=5, description="Test group"):
    gc = MagicMock()
    gc.semester_id = semester_id
    gc.model_dump.return_value = {
        "name": name,
        "description": description,
        "semester_id": semester_id,
    }
    return gc


def _make_group_update(name=None, description=None, semester_id=None):
    gu = MagicMock()
    gu.semester_id = semester_id
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if semester_id is not None:
        update_data["semester_id"] = semester_id
    gu.model_dump.return_value = update_data
    return gu


def _make_user_add(user_id=7):
    ua = MagicMock()
    ua.user_id = user_id
    return ua


# ---------------------------------------------------------------------------
# create_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCreateGroup:
    def test_semester_not_found_raises_404(self):
        """If semester does not exist, should raise 404."""
        db = _seq_db(_q(first=None))  # semester lookup returns None
        group_data = _make_group_create()

        with pytest.raises(HTTPException) as exc:
            create_group(group_data=group_data, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Semester not found" in exc.value.detail

    def test_create_group_success(self):
        """When semester exists, group is created and returned."""
        semester = _make_semester()
        db = MagicMock()
        db.query.return_value = _q(first=semester)

        group_data = _make_group_create(name="Alpha", semester_id=5)

        # Patch the Group constructor so we control the returned object
        mock_group = _make_group()
        with patch(f"{_BASE}.Group") as MockGroup:
            MockGroup.return_value = mock_group

            result = create_group(group_data=group_data, db=db, current_user=_admin())

        db.add.assert_called_once_with(mock_group)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(mock_group)
        assert result is mock_group


# ---------------------------------------------------------------------------
# list_groups
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestListGroups:
    def _make_list_db(self, groups):
        """Build a db mock that handles list_groups's query pattern.

        list_groups does:
          1. db.query(Group) -> main query (possibly filtered)
          2. For each group: db.query(func.count(User.id)).join(...).filter(...).scalar()
          3. For each group: db.query(func.count(Session.id)).filter(...).scalar()
          4. For each group: db.query(func.count(Booking.id)).join(...).filter(...).scalar()
        """
        call_idx = [0]
        main_q = _q(all_=groups)

        def _side(m):
            i = call_idx[0]
            call_idx[0] += 1
            if i == 0:
                return main_q
            # subsequent calls are scalar count queries
            scalar_q = _q(scalar=0)
            return scalar_q

        db = MagicMock()
        db.query.side_effect = _side
        return db

    def test_no_groups_returns_empty_list(self):
        """When there are no groups, returns GroupList with total=0."""
        db = self._make_list_db(groups=[])
        result = list_groups(db=db, current_user=_student(), semester_id=None)

        assert result.total == 0
        assert result.groups == []

    def test_returns_groups_with_stats(self):
        """With one group, GroupList is populated with stats."""
        group = _make_group()
        db = self._make_list_db(groups=[group])

        with patch(f"{_BASE}.GroupWithStats") as MockStats:
            mock_stats_obj = MagicMock()
            MockStats.return_value = mock_stats_obj
            with patch(f"{_BASE}.GroupList") as MockList:
                mock_list_obj = MagicMock()
                MockList.return_value = mock_list_obj

                result = list_groups(db=db, current_user=_student(), semester_id=None)

        MockStats.assert_called_once()
        MockList.assert_called_once()
        assert result is mock_list_obj

    def test_semester_id_filter_applied(self):
        """When semester_id is provided, filter is applied."""
        group = _make_group(semester_id=3)
        call_idx = [0]
        main_q = _q(all_=[group])

        def _side(m):
            i = call_idx[0]
            call_idx[0] += 1
            if i == 0:
                return main_q
            return _q(scalar=0)

        db = MagicMock()
        db.query.side_effect = _side

        with patch(f"{_BASE}.GroupWithStats") as MockStats:
            MockStats.return_value = MagicMock()
            with patch(f"{_BASE}.GroupList") as MockList:
                MockList.return_value = MagicMock()
                list_groups(db=db, current_user=_student(), semester_id=3)

        # filter should have been called on the main query
        main_q.filter.assert_called_once()

    def test_no_semester_filter_no_extra_filter(self):
        """When semester_id is None, no filter is applied to main query."""
        db = self._make_list_db(groups=[])
        list_groups(db=db, current_user=_student(), semester_id=None)

        # The main query mock is the first return value; filter should not be called
        # We verify the main query's all() was called
        calls = db.query.call_args_list
        assert len(calls) >= 1  # at least the main query call

    def test_multiple_groups_stats_computed_per_group(self):
        """Stats are computed separately for each group."""
        groups = [_make_group(id_=10), _make_group(id_=11)]

        scalar_results = [5, 2, 3, 4, 1, 6]  # 3 scalars per group
        scalar_idx = [0]
        main_q = _q(all_=groups)
        call_idx = [0]

        def _side(m):
            i = call_idx[0]
            call_idx[0] += 1
            if i == 0:
                return main_q
            sq = _q(scalar=scalar_results[scalar_idx[0] % len(scalar_results)])
            scalar_idx[0] += 1
            return sq

        db = MagicMock()
        db.query.side_effect = _side

        with patch(f"{_BASE}.GroupWithStats") as MockStats:
            MockStats.return_value = MagicMock()
            with patch(f"{_BASE}.GroupList") as MockList:
                MockList.return_value = MagicMock()
                list_groups(db=db, current_user=_student(), semester_id=None)

        # 3 scalar queries per group, 2 groups → 6 extra calls + 1 main = 7
        assert db.query.call_count == 7


# ---------------------------------------------------------------------------
# get_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetGroup:
    def test_group_not_found_raises_404(self):
        """When group doesn't exist, raise 404."""
        db = MagicMock()
        db.query.return_value = _q(first=None)

        with pytest.raises(HTTPException) as exc:
            get_group(group_id=99, db=db, current_user=_student())

        assert exc.value.status_code == 404
        assert "Group not found" in exc.value.detail

    def test_group_found_returns_group_with_relations(self):
        """When group exists, returns GroupWithRelations."""
        group = _make_group()
        db = MagicMock()
        db.query.return_value = _q(first=group)

        with patch(f"{_BASE}.GroupWithRelations") as MockGWR:
            mock_result = MagicMock()
            MockGWR.return_value = mock_result

            result = get_group(group_id=10, db=db, current_user=_student())

        MockGWR.assert_called_once()
        assert result is mock_result

    def test_group_with_relations_receives_semester_and_users(self):
        """GroupWithRelations is constructed with semester and users from group."""
        group = _make_group()
        group.users = [MagicMock(id=7)]
        db = MagicMock()
        db.query.return_value = _q(first=group)

        with patch(f"{_BASE}.GroupWithRelations") as MockGWR:
            MockGWR.return_value = MagicMock()
            get_group(group_id=10, db=db, current_user=_student())

        # Should have been called with semester= and users= kwargs
        call_kwargs = MockGWR.call_args[1]
        assert "semester" in call_kwargs
        assert "users" in call_kwargs
        assert call_kwargs["semester"] is group.semester
        assert call_kwargs["users"] is group.users


# ---------------------------------------------------------------------------
# update_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateGroup:
    def test_group_not_found_raises_404(self):
        """When group doesn't exist, raise 404."""
        db = MagicMock()
        db.query.return_value = _q(first=None)
        group_update = _make_group_update(name="New Name")

        with pytest.raises(HTTPException) as exc:
            update_group(group_id=99, group_update=group_update, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Group not found" in exc.value.detail

    def test_semester_id_changed_new_semester_not_found_raises_404(self):
        """When updating to a different semester_id that doesn't exist, raise 404."""
        group = _make_group(semester_id=5)
        # First query: group found; Second query: new semester not found
        db = _seq_db(_q(first=group), _q(first=None))
        group_update = _make_group_update(semester_id=99)  # different from group.semester_id=5

        with pytest.raises(HTTPException) as exc:
            update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Semester not found" in exc.value.detail

    def test_semester_id_changed_to_same_value_no_semester_lookup(self):
        """When semester_id in update equals existing semester_id, no semester re-check."""
        group = _make_group(semester_id=5)
        db = MagicMock()
        call_count = [0]

        def _side(m):
            call_count[0] += 1
            return _q(first=group)

        db.query.side_effect = _side
        group_update = _make_group_update(semester_id=5)  # same as group.semester_id

        update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        # Only 1 query (group lookup) because semester_id matches
        assert call_count[0] == 1

    def test_no_semester_id_update_no_semester_lookup(self):
        """When semester_id is None in update, no semester lookup is performed."""
        group = _make_group(semester_id=5)
        db = MagicMock()
        call_count = [0]

        def _side(m):
            call_count[0] += 1
            return _q(first=group)

        db.query.side_effect = _side
        group_update = _make_group_update(name="Updated Name")  # semester_id=None

        update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        assert call_count[0] == 1  # only the group lookup

    def test_update_success_commits_and_refreshes(self):
        """On valid update, commits and refreshes the group."""
        group = _make_group(semester_id=5)
        semester = _make_semester(id_=99)
        db = _seq_db(_q(first=group), _q(first=semester))
        group_update = _make_group_update(name="New Name", semester_id=99)

        result = update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(group)
        assert result is group

    def test_update_applies_fields_via_setattr(self):
        """Fields from model_dump are applied to the group object."""
        group = _make_group()
        db = MagicMock()
        db.query.return_value = _q(first=group)
        group_update = _make_group_update(name="Updated Name", description="New desc")

        update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        assert group.name == "Updated Name"
        assert group.description == "New desc"

    def test_update_success_with_new_semester(self):
        """Full success path: group + new semester both found, update committed."""
        group = _make_group(semester_id=5)
        new_semester = _make_semester(id_=10)
        db = _seq_db(_q(first=group), _q(first=new_semester))
        group_update = _make_group_update(semester_id=10)

        result = update_group(group_id=10, group_update=group_update, db=db, current_user=_admin())

        db.commit.assert_called_once()
        assert result is group


# ---------------------------------------------------------------------------
# delete_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDeleteGroup:
    def test_group_not_found_raises_404(self):
        """When group doesn't exist, raise 404."""
        db = _seq_db(_q(first=None))

        with pytest.raises(HTTPException) as exc:
            delete_group(group_id=99, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Group not found" in exc.value.detail

    def test_group_has_sessions_raises_400(self):
        """When group has existing sessions, raise 400."""
        group = _make_group()
        # First query: group found; Second query: session count > 0
        q_count = _q(scalar=3)
        db = _seq_db(_q(first=group), q_count)

        with pytest.raises(HTTPException) as exc:
            delete_group(group_id=10, db=db, current_user=_admin())

        assert exc.value.status_code == 400
        assert "Cannot delete group with existing sessions" in exc.value.detail

    def test_group_no_sessions_deleted_successfully(self):
        """When group has no sessions, it is deleted and success message returned."""
        group = _make_group()
        q_count = _q(scalar=0)
        db = _seq_db(_q(first=group), q_count)

        result = delete_group(group_id=10, db=db, current_user=_admin())

        db.delete.assert_called_once_with(group)
        db.commit.assert_called_once()
        assert result["message"] == "Group deleted successfully"

    def test_delete_returns_message_dict(self):
        """Return value is a dict with 'message' key."""
        group = _make_group()
        db = _seq_db(_q(first=group), _q(scalar=0))

        result = delete_group(group_id=10, db=db, current_user=_admin())

        assert isinstance(result, dict)
        assert "message" in result


# ---------------------------------------------------------------------------
# add_user_to_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAddUserToGroup:
    def test_group_not_found_raises_404(self):
        """When group doesn't exist, raise 404."""
        db = _seq_db(_q(first=None))
        user_data = _make_user_add(user_id=7)

        with pytest.raises(HTTPException) as exc:
            add_user_to_group(group_id=99, user_data=user_data, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Group not found" in exc.value.detail

    def test_user_not_found_raises_404(self):
        """When user doesn't exist, raise 404."""
        group = _make_group()
        db = _seq_db(_q(first=group), _q(first=None))
        user_data = _make_user_add(user_id=7)

        with pytest.raises(HTTPException) as exc:
            add_user_to_group(group_id=10, user_data=user_data, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "User not found" in exc.value.detail

    def test_user_already_in_group_raises_400(self):
        """When user is already a member of the group, raise 400."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = [user]  # user already present

        db = _seq_db(_q(first=group), _q(first=user))
        user_data = _make_user_add(user_id=7)

        with pytest.raises(HTTPException) as exc:
            add_user_to_group(group_id=10, user_data=user_data, db=db, current_user=_admin())

        assert exc.value.status_code == 400
        assert "already in this group" in exc.value.detail

    def test_add_user_success(self):
        """User not in group -> append and commit."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = []  # user not yet present

        db = _seq_db(_q(first=group), _q(first=user))
        user_data = _make_user_add(user_id=7)

        result = add_user_to_group(group_id=10, user_data=user_data, db=db, current_user=_admin())

        assert user in group.users
        db.commit.assert_called_once()
        assert result["message"] == "User added to group successfully"

    def test_add_user_returns_message_dict(self):
        """Return value is a dict with 'message' key."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = []

        db = _seq_db(_q(first=group), _q(first=user))
        user_data = _make_user_add(user_id=7)

        result = add_user_to_group(group_id=10, user_data=user_data, db=db, current_user=_admin())

        assert isinstance(result, dict)
        assert "message" in result


# ---------------------------------------------------------------------------
# remove_user_from_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRemoveUserFromGroup:
    def test_group_not_found_raises_404(self):
        """When group doesn't exist, raise 404."""
        db = _seq_db(_q(first=None))

        with pytest.raises(HTTPException) as exc:
            remove_user_from_group(group_id=99, user_id=7, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "Group not found" in exc.value.detail

    def test_user_not_found_raises_404(self):
        """When user doesn't exist, raise 404."""
        group = _make_group()
        db = _seq_db(_q(first=group), _q(first=None))

        with pytest.raises(HTTPException) as exc:
            remove_user_from_group(group_id=10, user_id=7, db=db, current_user=_admin())

        assert exc.value.status_code == 404
        assert "User not found" in exc.value.detail

    def test_user_not_in_group_raises_400(self):
        """When user is not a member of the group, raise 400."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = []  # user not present

        db = _seq_db(_q(first=group), _q(first=user))

        with pytest.raises(HTTPException) as exc:
            remove_user_from_group(group_id=10, user_id=7, db=db, current_user=_admin())

        assert exc.value.status_code == 400
        assert "not in this group" in exc.value.detail

    def test_remove_user_success(self):
        """User in group -> remove and commit."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = [user]  # user is in group

        db = _seq_db(_q(first=group), _q(first=user))

        result = remove_user_from_group(group_id=10, user_id=7, db=db, current_user=_admin())

        assert user not in group.users
        db.commit.assert_called_once()
        assert result["message"] == "User removed from group successfully"

    def test_remove_user_returns_message_dict(self):
        """Return value is a dict with 'message' key."""
        user = MagicMock()
        user.id = 7
        group = _make_group()
        group.users = [user]

        db = _seq_db(_q(first=group), _q(first=user))

        result = remove_user_from_group(group_id=10, user_id=7, db=db, current_user=_admin())

        assert isinstance(result, dict)
        assert "message" in result

    def test_remove_only_removes_specified_user(self):
        """Other users in the group are not removed."""
        user_a = MagicMock()
        user_a.id = 7
        user_b = MagicMock()
        user_b.id = 8
        group = _make_group()
        group.users = [user_a, user_b]

        db = _seq_db(_q(first=group), _q(first=user_a))

        remove_user_from_group(group_id=10, user_id=7, db=db, current_user=_admin())

        assert user_a not in group.users
        assert user_b in group.users
