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
from src.tools import find_subroutines, get_callees, get_callers, get_subroutine
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
    """get_subroutine raises ValueError when a name matches multiple packages."""

    def test_returns_something(self, dup_db):
        """get_subroutine raises ValueError for an ambiguous name — it no longer silently returns one result."""
        with pytest.raises(ValueError):
            get_subroutine("SHARED_SUB", _db_path=dup_db)

    def test_returns_lowest_id(self, dup_db):
        """The lowest-id-wins behaviour is gone; get_subroutine now raises ValueError for ambiguous names.

        Previously the function returned the pkg_a copy (id 20) silently. Now it
        raises so that callers are forced to disambiguate via package=.
        """
        with pytest.raises(ValueError):
            get_subroutine("SHARED_SUB", _db_path=dup_db)

    def test_pkg_b_copy_is_reachable(self, dup_db):
        """The pkg_b copy (id 21) is reachable via the package= parameter."""
        result = get_subroutine("SHARED_SUB", package="pkg_b", _db_path=dup_db)
        assert result["package"] == "pkg_b"


class TestGetCallersCurrentBehaviour:
    """get_callers("SHARED_SUB") mixes callers intended for both copies."""

    def test_returns_two_callers(self, dup_db):
        """Both CALLER_A and CALLER_B are returned — the name match is ambiguous."""
        results = get_callers("SHARED_SUB", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert names == {"CALLER_A", "CALLER_B"}

    def test_pkg_a_callers_excludes_caller_b(self, dup_db):
        """When scoped to the pkg_a copy via package=, only CALLER_A appears."""
        results = get_callers("SHARED_SUB", package="pkg_a", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert "CALLER_B" not in names

    def test_pkg_b_callers_excludes_caller_a(self, dup_db):
        """When scoped to the pkg_b copy via package=, only CALLER_B appears."""
        results = get_callers("SHARED_SUB", package="pkg_b", _db_path=dup_db)
        names = {r["name"] for r in results}
        assert "CALLER_A" not in names


class TestGetCalleesCurrentBehaviour:
    """get_callees("SHARED_SUB") merges callees from both copies."""

    def test_returns_callees_from_both_copies(self, dup_db):
        """CALLEE_ONLY (from pkg_a) and UNIQUE_CALLEE (from pkg_b) both appear."""
        results = get_callees("SHARED_SUB", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert names == {"CALLEE_ONLY", "UNIQUE_CALLEE"}

    def test_pkg_a_callees_excludes_unique_callee(self, dup_db):
        """When scoped to the pkg_a copy via package=, only CALLEE_ONLY appears."""
        results = get_callees("SHARED_SUB", package="pkg_a", _db_path=dup_db)
        names = {r["callee_name"] for r in results}
        assert "UNIQUE_CALLEE" not in names

    def test_pkg_b_callees_excludes_callee_only(self, dup_db):
        """When scoped to the pkg_b copy via package=, only UNIQUE_CALLEE appears."""
        results = get_callees("SHARED_SUB", package="pkg_b", _db_path=dup_db)
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
        """An unqualified lookup of a duplicate name raises ValueError.

        get_subroutine raises rather than silently dropping one copy, so
        callers are forced to disambiguate via package= or use find_subroutines().
        """
        with pytest.raises(ValueError):
            get_subroutine("SHARED_SUB", _db_path=dup_db)


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


# ---------------------------------------------------------------------------
# find_subroutines — discovers all copies of a name across packages
# ---------------------------------------------------------------------------


class TestFindSubroutines:
    """find_subroutines always returns all copies of a name."""

    def test_find_returns_both_copies(self, dup_db):
        """find_subroutines returns both the pkg_a and pkg_b copies of SHARED_SUB."""
        results = find_subroutines("SHARED_SUB", _db_path=dup_db)
        assert len(results) == 2
        assert {r["package"] for r in results} == {"pkg_a", "pkg_b"}

    def test_find_not_found_returns_empty(self, dup_db):
        """find_subroutines returns an empty list when the name does not exist."""
        results = find_subroutines("NONEXISTENT", _db_path=dup_db)
        assert results == []

    def test_find_case_insensitive(self, dup_db):
        """find_subroutines matches names case-insensitively."""
        results = find_subroutines("shared_sub", _db_path=dup_db)
        assert len(results) == 2

    def test_find_no_source_text(self, dup_db):
        """Returned dicts do not include source_text."""
        results = find_subroutines("SHARED_SUB", _db_path=dup_db)
        for r in results:
            assert "source_text" not in r
