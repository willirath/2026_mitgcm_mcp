"""Tests documenting behaviour when two subroutines share the same name in different packages.

Fixture: dup_db
---------------
Subroutines
  20  SHARED_SUB   pkg_a   pkg_a/src/shared_sub.F   — the "first" (lower id)
  21  SHARED_SUB   pkg_b   pkg_b/src/shared_sub.F   — the "second" (higher id)
  22  CALLER_A     pkg_a   pkg_a/src/caller_a.F     — calls the pkg_a copy
  23  CALLER_B     pkg_b   pkg_b/src/caller_b.F     — calls the pkg_b copy
  24  CALLEE_ONLY  pkg_a   pkg_a/src/callee_only.F  — called by pkg_a SHARED_SUB only

Calls
  22 (CALLER_A)   → "SHARED_SUB"    (intended to reach id 20, pkg_a)
  23 (CALLER_B)   → "SHARED_SUB"    (intended to reach id 21, pkg_b)
  20 (SHARED_SUB/pkg_a) → "CALLEE_ONLY"
  21 (SHARED_SUB/pkg_b) → "UNIQUE_CALLEE"   (a name not in the subroutines table)

Current bugs (all xfail)
  - get_subroutine("SHARED_SUB") silently returns only id 20; id 21 is unreachable
  - get_callers("SHARED_SUB") returns callers of *both* copies indistinguishably
  - get_callees("SHARED_SUB") merges callees of both copies

Desired behaviour (also xfail — fix not yet implemented)
  - A disambiguation mechanism allows callers to specify which copy they want
    (e.g. by package, file, or id)
  - get_callers scoped to one copy returns only that copy's callers
  - get_callees scoped to one copy returns only that copy's callees
"""

import pytest
from src.tools import get_callees, get_callers, get_subroutine
from src.indexer.schema import connect


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def dup_db(tmp_path_factory):
    """Session-scoped DuckDB with two subroutines sharing the same name."""
    db_path = tmp_path_factory.mktemp("dupdb") / "dup.duckdb"
    con = connect(db_path)

    subs = [
        (20, "SHARED_SUB",  "pkg_a/src/shared_sub.F",  "pkg_a", 1, 100, "SUBROUTINE SHARED_SUB\n! pkg_a copy\nEND"),
        (21, "SHARED_SUB",  "pkg_b/src/shared_sub.F",  "pkg_b", 1, 120, "SUBROUTINE SHARED_SUB\n! pkg_b copy\nEND"),
        (22, "CALLER_A",    "pkg_a/src/caller_a.F",    "pkg_a", 1,  50, "SUBROUTINE CALLER_A\nEND"),
        (23, "CALLER_B",    "pkg_b/src/caller_b.F",    "pkg_b", 1,  60, "SUBROUTINE CALLER_B\nEND"),
        (24, "CALLEE_ONLY", "pkg_a/src/callee_only.F", "pkg_a", 1,  30, "SUBROUTINE CALLEE_ONLY\nEND"),
    ]
    for row in subs:
        con.execute(
            "INSERT INTO subroutines (id, name, file, package, line_start, line_end, source_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
            list(row),
        )

    calls = [
        (22, "SHARED_SUB"),    # CALLER_A   → intended target: pkg_a copy (id 20)
        (23, "SHARED_SUB"),    # CALLER_B   → intended target: pkg_b copy (id 21)
        (20, "CALLEE_ONLY"),   # pkg_a SHARED_SUB calls CALLEE_ONLY
        (21, "UNIQUE_CALLEE"), # pkg_b SHARED_SUB calls UNIQUE_CALLEE (not in table)
    ]
    for caller_id, callee_name in calls:
        con.execute("INSERT INTO calls (caller_id, callee_name) VALUES (?, ?)", [caller_id, callee_name])

    con.close()
    return db_path


# ---------------------------------------------------------------------------
# Current (buggy) behaviour — documented with xfail where the result is wrong
# ---------------------------------------------------------------------------


class TestGetSubroutineCurrentBehaviour:
    """get_subroutine silently returns only one of the two SHARED_SUB entries."""

    def test_returns_something(self, dup_db):
        """get_subroutine does return a result — it is not None."""
        result = get_subroutine("SHARED_SUB", _db_path=dup_db)
        assert result is not None

    def test_returns_lowest_id(self, dup_db):
        """The result is always the row with the lowest database id (id 20, pkg_a).

        This is an artefact of DuckDB's unspecified but de-facto stable row
        ordering: fetchone() picks the first matching row, which happens to be
        the one inserted first (lowest id).
        """
        result = get_subroutine("SHARED_SUB", _db_path=dup_db)
        assert result["id"] == 20
        assert result["package"] == "pkg_a"

    @pytest.mark.xfail(reason="Bug: pkg_b copy (id 21) is silently shadowed; get_subroutine returns only one row")
    def test_pkg_b_copy_is_reachable(self, dup_db):
        """The pkg_b copy (id 21) should also be reachable — currently it is not."""
        result = get_subroutine("SHARED_SUB", _db_path=dup_db)
        # Under current code this always gives pkg_a; pkg_b is unreachable via this call.
        # The test checks for the pkg_b copy specifically; it must fail until the bug is fixed.
        assert result["package"] == "pkg_b"

    @pytest.mark.xfail(reason="Bug: get_subroutine returns a single dict, not a list; cannot expose both copies")
    def test_both_copies_returned(self, dup_db):
        """get_subroutine must somehow expose both copies when the name is ambiguous.

        Under the current signature (returns dict | None) this is impossible.
        The desired fix would either raise, return a list, or require a
        package/file qualifier.  This test documents that the current single-
        dict return cannot satisfy the requirement.
        """
        result = get_subroutine("SHARED_SUB", _db_path=dup_db)
        # A dict is not a list — the assertion will fail, confirming the bug.
        assert isinstance(result, list)
        assert len(result) == 2


class TestGetCallersCurrentBehaviour:
    """get_callers("SHARED_SUB") mixes callers intended for both copies."""

    def test_returns_two_callers(self, dup_db):
        """Both CALLER_A and CALLER_B are returned — the name match is ambiguous."""
        results = get_callers("SHARED_SUB", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert names == {"CALLER_A", "CALLER_B"}

    @pytest.mark.xfail(reason="Bug: callers cannot be scoped to one copy; pkg_a copy's callers bleed into pkg_b results")
    def test_pkg_a_callers_excludes_caller_b(self, dup_db):
        """When scoped to the pkg_a copy, only CALLER_A should appear.

        There is currently no way to express this constraint through the
        get_callers API; the unscoped call always returns both.
        """
        results = get_callers("SHARED_SUB", _db_path=dup_db)
        # Under current code, CALLER_B appears even though it was intended for
        # the pkg_b copy.  This assertion will fail, documenting the bug.
        names = {r["name"] for r in results}
        assert "CALLER_B" not in names

    @pytest.mark.xfail(reason="Bug: callers cannot be scoped to one copy; pkg_b copy's callers bleed into pkg_a results")
    def test_pkg_b_callers_excludes_caller_a(self, dup_db):
        """When scoped to the pkg_b copy, only CALLER_B should appear.

        The current get_callers("SHARED_SUB") returns both; there is no way
        to distinguish between the two copies.
        """
        results = get_callers("SHARED_SUB", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert "CALLER_A" not in names


class TestGetCalleesCurrentBehaviour:
    """get_callees("SHARED_SUB") merges callees from both copies."""

    def test_returns_callees_from_both_copies(self, dup_db):
        """CALLEE_ONLY (from pkg_a) and UNIQUE_CALLEE (from pkg_b) both appear."""
        results = get_callees("SHARED_SUB", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert names == {"CALLEE_ONLY", "UNIQUE_CALLEE"}

    @pytest.mark.xfail(reason="Bug: callees cannot be scoped to pkg_a copy; pkg_b callees contaminate the result")
    def test_pkg_a_callees_excludes_unique_callee(self, dup_db):
        """When scoped to the pkg_a copy, only CALLEE_ONLY should appear.

        Currently get_callees merges rows from caller_id 20 and 21, because
        both subroutines match upper(s.name) = upper('SHARED_SUB').
        """
        results = get_callees("SHARED_SUB", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert "UNIQUE_CALLEE" not in names

    @pytest.mark.xfail(reason="Bug: callees cannot be scoped to pkg_b copy; pkg_a callees contaminate the result")
    def test_pkg_b_callees_excludes_callee_only(self, dup_db):
        """When scoped to the pkg_b copy, only UNIQUE_CALLEE should appear.

        Currently both callees are returned regardless of which copy is intended.
        """
        results = get_callees("SHARED_SUB", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert "CALLEE_ONLY" not in names


# ---------------------------------------------------------------------------
# Desired (correct) behaviour — all xfail because the fix is not implemented
# ---------------------------------------------------------------------------


class TestDesiredBehaviourGetSubroutine:
    """The fix should allow retrieving each copy of a duplicate-named subroutine."""

    def test_lookup_by_package_returns_pkg_a(self, dup_db):
        """After the fix, get_subroutine('SHARED_SUB', package='pkg_a') should return id 20."""
        # The current signature has no 'package' parameter — this will raise TypeError.
        result = get_subroutine("SHARED_SUB", package="pkg_a", _db_path=dup_db)
        assert result is not None
        assert result["id"] == 20
        assert result["package"] == "pkg_a"

    def test_lookup_by_package_returns_pkg_b(self, dup_db):
        """After the fix, get_subroutine('SHARED_SUB', package='pkg_b') should return id 21."""
        result = get_subroutine("SHARED_SUB", package="pkg_b", _db_path=dup_db)
        assert result is not None
        assert result["id"] == 21
        assert result["package"] == "pkg_b"

    def test_ambiguous_lookup_raises_or_warns(self, dup_db):
        """An unqualified lookup of a duplicate name should not silently drop one copy.

        The desired behaviour is either a raised exception, a warning, or
        returning a list.  Currently no exception is raised.
        """
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_subroutine("SHARED_SUB", _db_path=dup_db)
        # Expect a warning to have been issued — currently none is raised.
        assert len(caught) >= 1, "Expected a warning for ambiguous name lookup; got none"


class TestDesiredBehaviourGetCallers:
    """The fix should allow scoping get_callers to one copy of a duplicate-named subroutine."""

    def test_callers_scoped_to_pkg_a(self, dup_db):
        """After the fix, callers of the pkg_a copy should be only CALLER_A."""
        results = get_callers("SHARED_SUB", package="pkg_a", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert names == {"CALLER_A"}

    def test_callers_scoped_to_pkg_b(self, dup_db):
        """After the fix, callers of the pkg_b copy should be only CALLER_B."""
        results = get_callers("SHARED_SUB", package="pkg_b", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert names == {"CALLER_B"}


class TestDesiredBehaviourGetCallees:
    """The fix should allow scoping get_callees to one copy of a duplicate-named subroutine."""

    def test_callees_scoped_to_pkg_a(self, dup_db):
        """After the fix, callees of the pkg_a copy (id 20) should be only CALLEE_ONLY."""
        results = get_callees("SHARED_SUB", package="pkg_a", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert names == {"CALLEE_ONLY"}

    def test_callees_scoped_to_pkg_b(self, dup_db):
        """After the fix, callees of the pkg_b copy (id 21) should be only UNIQUE_CALLEE."""
        results = get_callees("SHARED_SUB", package="pkg_b", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert names == {"UNIQUE_CALLEE"}
