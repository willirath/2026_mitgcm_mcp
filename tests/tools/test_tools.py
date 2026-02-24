"""Tests for src/tools.py — all use the synthetic test_db fixture."""

import pytest
from src.mitgcm_tools import (
    _normalize_query,
    diagnostics_fill_to_source,
    find_subroutines,
    get_callees,
    get_callers,
    get_cpp_requirements,
    get_package_flags,
    get_subroutine,
    namelist_to_code,
)


# ---------------------------------------------------------------------------
# _normalize_query
# ---------------------------------------------------------------------------


def test_normalize_camel_case():
    """camelCase identifiers should be split into words."""
    assert _normalize_query("zonalWindFile") == "zonal Wind File"


def test_normalize_snake_case():
    """snake_case identifiers should have underscores replaced by spaces."""
    assert _normalize_query("no_slip_sides") == "no slip sides"


def test_normalize_mixed_query():
    """Mixed identifier + natural language should split only the identifier part."""
    result = _normalize_query("tauX direction convention")
    assert "tau X" in result
    assert "direction convention" in result


def test_normalize_allcaps_unchanged():
    """ALL_CAPS identifiers should have underscores replaced but case preserved."""
    result = _normalize_query("ALLOW_NONHYDROSTATIC")
    assert "_" not in result
    assert "ALLOW" in result


def test_normalize_plain_text_unchanged():
    """Plain natural-language queries should not be altered (no camelCase/underscores)."""
    q = "non hydrostatic pressure solve"
    assert _normalize_query(q) == q


# ---------------------------------------------------------------------------
# get_subroutine
# ---------------------------------------------------------------------------


def test_get_subroutine_found(test_db):
    result = get_subroutine("CG3D", _db_path=test_db)
    assert result is not None
    assert result["name"] == "CG3D"
    assert result["package"] == "model"
    assert "SUBROUTINE CG3D" in result["source_text"]


def test_get_subroutine_not_found(test_db):
    result = get_subroutine("NONEXISTENT", _db_path=test_db)
    assert result is None


def test_get_subroutine_case_insensitive(test_db):
    result = get_subroutine("cg3d", _db_path=test_db)
    assert result is not None
    assert result["name"] == "CG3D"


def test_get_subroutine_mixed_case(test_db):
    result = get_subroutine("Cg3D", _db_path=test_db)
    assert result is not None
    assert result["name"] == "CG3D"


# ---------------------------------------------------------------------------
# find_subroutines
# ---------------------------------------------------------------------------


def test_find_subroutines_unique_name(test_db):
    results = find_subroutines("CG3D", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["name"] == "CG3D"
    assert results[0]["package"] == "model"


def test_find_subroutines_not_found(test_db):
    results = find_subroutines("NONEXISTENT", _db_path=test_db)
    assert results == []


def test_find_subroutines_no_source_text(test_db):
    results = find_subroutines("CG3D", _db_path=test_db)
    assert len(results) == 1
    assert "source_text" not in results[0]


# ---------------------------------------------------------------------------
# get_callers
# ---------------------------------------------------------------------------


def test_get_callers_found(test_db):
    results = get_callers("CG3D", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["name"] == "PRE_CG3D"


def test_get_callers_empty(test_db):
    results = get_callers("PRE_CG3D", _db_path=test_db)
    assert results == []


def test_get_callers_not_found(test_db):
    results = get_callers("NONEXISTENT", _db_path=test_db)
    assert results == []


def test_get_callers_case_insensitive(test_db):
    results = get_callers("cg3d", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["name"] == "PRE_CG3D"


# ---------------------------------------------------------------------------
# get_callees
# ---------------------------------------------------------------------------


def test_get_callees_found(test_db):
    results = get_callees("PRE_CG3D", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["callee_name"] == "CG3D"


def test_get_callees_empty(test_db):
    results = get_callees("CG3D", _db_path=test_db)
    assert results == []


def test_get_callees_case_insensitive(test_db):
    results = get_callees("pre_cg3d", _db_path=test_db)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# namelist_to_code
# ---------------------------------------------------------------------------


def test_namelist_to_code_found(test_db):
    results = namelist_to_code("cg3dMaxIters", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["name"] == "CG3D"
    assert results[0]["namelist_group"] == "PARM02"


def test_namelist_to_code_not_found(test_db):
    results = namelist_to_code("nonExistentParam", _db_path=test_db)
    assert results == []


def test_namelist_to_code_case_insensitive(test_db):
    results = namelist_to_code("CG3DMAXITERS", _db_path=test_db)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# diagnostics_fill_to_source
# ---------------------------------------------------------------------------


def test_diagnostics_fill_to_source_found(test_db):
    results = diagnostics_fill_to_source("RHOAnoma", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["name"] == "CG3D"
    assert results[0]["array_name"] == "rho3d"


def test_diagnostics_fill_to_source_padded_field_name(test_db):
    # Field stored with trailing space should match without it
    results = diagnostics_fill_to_source("WdRHO_P", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["array_name"] == "wdrho3d"


def test_diagnostics_fill_to_source_not_found(test_db):
    results = diagnostics_fill_to_source("NONEXISTENT", _db_path=test_db)
    assert results == []


# ---------------------------------------------------------------------------
# get_cpp_requirements
# ---------------------------------------------------------------------------


def test_get_cpp_requirements_found(test_db):
    results = get_cpp_requirements("CG3D", _db_path=test_db)
    assert results == ["ALLOW_NONHYDROST"]


def test_get_cpp_requirements_not_found(test_db):
    results = get_cpp_requirements("NONEXISTENT", _db_path=test_db)
    assert results == []


def test_get_cpp_requirements_case_insensitive(test_db):
    results = get_cpp_requirements("cg3d", _db_path=test_db)
    assert results == ["ALLOW_NONHYDROST"]


# ---------------------------------------------------------------------------
# get_package_flags
# ---------------------------------------------------------------------------


def test_get_package_flags_found(test_db):
    results = get_package_flags("model", _db_path=test_db)
    assert len(results) == 1
    assert results[0]["cpp_flag"] == "ALLOW_NONHYDROST"
    assert "non-hydrostatic" in results[0]["description"]


def test_get_package_flags_not_found(test_db):
    results = get_package_flags("nonexistent_pkg", _db_path=test_db)
    assert results == []


def test_get_package_flags_case_insensitive(test_db):
    results = get_package_flags("MODEL", _db_path=test_db)
    assert len(results) == 1
