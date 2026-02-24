"""Adversarial tests for src/tools.py.

Uses the adv_db fixture (see conftest.py) which has 5 subroutines covering:
- multiple callers / callees
- duplicate call rows (dedup expected)
- callee not present in subroutines table
- same namelist param in multiple subroutines with different groups
- multiple namelist params in one subroutine
- same diagnostics field filled by multiple subroutines
- trailing / multiple trailing spaces in stored field names
- subroutine with two CPP guards
- package with multiple flags
- fully isolated subroutine (no callers, callees, guards, refs, fills)
"""

import pytest
from src.mitgcm_tools import (
    diagnostics_fill_to_source,
    get_callees,
    get_callers,
    get_cpp_requirements,
    get_package_flags,
    get_subroutine,
    namelist_to_code,
)


# ---------------------------------------------------------------------------
# get_callers — multiple callers
# ---------------------------------------------------------------------------


def test_get_callers_multiple(adv_db):
    """CG3D is called by both SOLVE_FOR_P and INIT_CG3D."""
    results = get_callers("CG3D", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert names == {"SOLVE_FOR_P", "INIT_CG3D"}


def test_get_callers_single(adv_db):
    """CG2D is called only by SOLVE_FOR_P."""
    results = get_callers("CG2D", _db_path=adv_db)
    assert len(results) == 1
    assert results[0]["name"] == "SOLVE_FOR_P"


def test_get_callers_isolated(adv_db):
    """LEAF_SUB has no callers."""
    assert get_callers("LEAF_SUB", _db_path=adv_db) == []


# ---------------------------------------------------------------------------
# get_callees — multiple callees, dedup, unknown callee
# ---------------------------------------------------------------------------


def test_get_callees_multiple(adv_db):
    """SOLVE_FOR_P calls CG3D (twice in table), CG2D, and EXTERNAL_ROUTINE."""
    results = get_callees("SOLVE_FOR_P", _db_path=adv_db)
    names = {r["callee_name"] for r in results}
    assert names == {"CG3D", "CG2D", "EXTERNAL_ROUTINE"}


def test_get_callees_deduplicates(adv_db):
    """Duplicate call rows for the same callee must not produce duplicate results."""
    results = get_callees("SOLVE_FOR_P", _db_path=adv_db)
    callee_names = [r["callee_name"] for r in results]
    assert callee_names.count("CG3D") == 1


def test_get_callees_external_callee_included(adv_db):
    """A callee not present in the subroutines table is still returned by name."""
    results = get_callees("SOLVE_FOR_P", _db_path=adv_db)
    names = {r["callee_name"] for r in results}
    assert "EXTERNAL_ROUTINE" in names


def test_get_callees_isolated(adv_db):
    """LEAF_SUB calls nothing."""
    assert get_callees("LEAF_SUB", _db_path=adv_db) == []


# ---------------------------------------------------------------------------
# namelist_to_code — same param in multiple subroutines / groups
# ---------------------------------------------------------------------------


def test_namelist_multiple_subroutines(adv_db):
    """cg3dMaxIters appears in both CG3D and INIT_CG3D."""
    results = namelist_to_code("cg3dMaxIters", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert names == {"CG3D", "INIT_CG3D"}


def test_namelist_different_groups_for_same_param(adv_db):
    """cg3dMaxIters is in PARM03 for CG3D and PARM02 for INIT_CG3D."""
    results = namelist_to_code("cg3dMaxIters", _db_path=adv_db)
    groups = {r["name"]: r["namelist_group"] for r in results}
    assert groups["CG3D"] == "PARM03"
    assert groups["INIT_CG3D"] == "PARM02"


def test_namelist_second_param_same_subroutine(adv_db):
    """cg3dTargetResidual is in CG3D only."""
    results = namelist_to_code("cg3dTargetResidual", _db_path=adv_db)
    assert len(results) == 1
    assert results[0]["name"] == "CG3D"
    assert results[0]["namelist_group"] == "PARM03"


def test_namelist_unique_param(adv_db):
    """nonHydrostSolver appears only in SOLVE_FOR_P."""
    results = namelist_to_code("nonHydrostSolver", _db_path=adv_db)
    assert len(results) == 1
    assert results[0]["name"] == "SOLVE_FOR_P"


def test_namelist_isolated_subroutine_has_no_refs(adv_db):
    """LEAF_SUB is not referenced by any namelist param."""
    # No param maps to LEAF_SUB — any lookup that would have returned it returns []
    results = namelist_to_code("cg3dMaxIters", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert "LEAF_SUB" not in names


# ---------------------------------------------------------------------------
# diagnostics_fill_to_source — whitespace, multiple sources
# ---------------------------------------------------------------------------


def test_diag_fill_multiple_sources(adv_db):
    """PHInhyd is filled by both CG3D and CG2D."""
    results = diagnostics_fill_to_source("PHInhyd", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert names == {"CG3D", "CG2D"}


def test_diag_fill_query_with_trailing_space_matches(adv_db):
    """Query 'PHInhyd ' (trailing space) should still match stored 'PHInhyd '."""
    results = diagnostics_fill_to_source("PHInhyd ", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert "CG3D" in names


def test_diag_fill_two_trailing_spaces_stored(adv_db):
    """'PHISURF  ' (two trailing spaces) stored; query without spaces must match."""
    results = diagnostics_fill_to_source("PHISURF", _db_path=adv_db)
    assert len(results) == 1
    assert results[0]["name"] == "SOLVE_FOR_P"


def test_diag_fill_query_with_extra_spaces_matches(adv_db):
    """Query 'PHISURF  ' (two trailing spaces) matches stored 'PHISURF  '."""
    results = diagnostics_fill_to_source("PHISURF  ", _db_path=adv_db)
    assert len(results) == 1


def test_diag_fill_case_insensitive(adv_db):
    """Field lookup is case-insensitive."""
    results = diagnostics_fill_to_source("phinHYD", _db_path=adv_db)
    names = {r["name"] for r in results}
    assert names == {"CG3D", "CG2D"}


# ---------------------------------------------------------------------------
# get_cpp_requirements — multiple guards, unguarded subroutine
# ---------------------------------------------------------------------------


def test_cpp_requirements_two_guards(adv_db):
    """SOLVE_FOR_P is guarded by both ALLOW_NONHYDROST and ALLOW_CG2D_NSA."""
    results = get_cpp_requirements("SOLVE_FOR_P", _db_path=adv_db)
    assert set(results) == {"ALLOW_NONHYDROST", "ALLOW_CG2D_NSA"}


def test_cpp_requirements_one_guard(adv_db):
    """CG3D has exactly one guard."""
    results = get_cpp_requirements("CG3D", _db_path=adv_db)
    assert results == ["ALLOW_NONHYDROST"]


def test_cpp_requirements_unguarded(adv_db):
    """INIT_CG3D has no CPP guards."""
    assert get_cpp_requirements("INIT_CG3D", _db_path=adv_db) == []


def test_cpp_requirements_isolated(adv_db):
    """LEAF_SUB has no CPP guards."""
    assert get_cpp_requirements("LEAF_SUB", _db_path=adv_db) == []


# ---------------------------------------------------------------------------
# get_package_flags — multiple flags per package, package with no flags
# ---------------------------------------------------------------------------


def test_package_flags_multiple(adv_db):
    """nonhydrost package defines two CPP flags."""
    results = get_package_flags("nonhydrost", _db_path=adv_db)
    flags = {r["cpp_flag"] for r in results}
    assert flags == {"ALLOW_NONHYDROST", "ALLOW_CG2D_NSA"}


def test_package_flags_descriptions_present(adv_db):
    """Each flag entry includes a non-empty description."""
    results = get_package_flags("nonhydrost", _db_path=adv_db)
    for r in results:
        assert r["description"]


def test_package_flags_model_not_in_fixture(adv_db):
    """model package has no flags in this fixture."""
    assert get_package_flags("model", _db_path=adv_db) == []


# ---------------------------------------------------------------------------
# get_subroutine — metadata fields for a richer subroutine
# ---------------------------------------------------------------------------


def test_get_subroutine_fields_complete(adv_db):
    """All expected keys are present in the returned dict."""
    result = get_subroutine("SOLVE_FOR_P", _db_path=adv_db)
    assert result is not None
    assert set(result.keys()) == {"id", "name", "file", "package", "line_start", "line_end", "source_text"}


def test_get_subroutine_package_nonhydrost(adv_db):
    result = get_subroutine("CG2D", _db_path=adv_db)
    assert result["package"] == "nonhydrost"
