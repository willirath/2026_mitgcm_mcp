"""Tests for Tier 2: namelist → code linker.

Covers:
- extract.py: module-level namelist /group/ declaration parsing
- namelist_config.py: config file parameter + description extraction
- pipeline integration: namelist_refs and namelist_descriptions in DuckDB
"""

import tempfile
from pathlib import Path

import pytest

from src.fesom2.indexer.extract import extract_file
from src.fesom2.indexer.namelist_config import parse_config_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_f90(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".F90", mode="w", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def _write_nml(content: str, name: str = "namelist.test") -> Path:
    d = Path(tempfile.mkdtemp())
    p = d / name
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Source: namelist /group/ extraction
# ---------------------------------------------------------------------------

SIMPLE_NML_MODULE = """\
MODULE g_config
  integer :: step_per_day = 72
  integer :: run_length = 1
  character :: run_length_unit = 'y'
  namelist /timestep/ step_per_day, run_length, run_length_unit
END MODULE g_config
"""

def test_namelist_group_detected():
    mods, _ = extract_file(_write_f90(SIMPLE_NML_MODULE))
    groups = [g for g, _, _ in mods[0].namelist_groups]
    assert "timestep" in groups

def test_namelist_params_extracted():
    mods, _ = extract_file(_write_f90(SIMPLE_NML_MODULE))
    g, params, _ = mods[0].namelist_groups[0]
    assert "step_per_day" in params
    assert "run_length" in params
    assert "run_length_unit" in params

def test_namelist_line_number_recorded():
    mods, _ = extract_file(_write_f90(SIMPLE_NML_MODULE))
    _, _, line = mods[0].namelist_groups[0]
    assert line >= 1


MULTILINE_NML = """\
MODULE o_PARAM
  NAMELIST /oce_dyn/ C_d, A_ver, &
                     scale_area, &
                     Fer_GM
END MODULE o_PARAM
"""

def test_multiline_namelist_parsed():
    mods, _ = extract_file(_write_f90(MULTILINE_NML))
    g, params, _ = mods[0].namelist_groups[0]
    assert g == "oce_dyn"
    assert "C_d" in params
    assert "A_ver" in params
    assert "scale_area" in params
    assert "Fer_GM" in params


MULTI_GROUP_MODULE = """\
MODULE oce_mod
  namelist /group_a/ alpha, beta
  namelist /group_b/ gamma, delta
END MODULE oce_mod
"""

def test_multiple_namelist_groups_in_one_module():
    mods, _ = extract_file(_write_f90(MULTI_GROUP_MODULE))
    groups = [g for g, _, _ in mods[0].namelist_groups]
    assert "group_a" in groups
    assert "group_b" in groups

def test_params_assigned_to_correct_group():
    mods, _ = extract_file(_write_f90(MULTI_GROUP_MODULE))
    by_group = {g: params for g, params, _ in mods[0].namelist_groups}
    assert "alpha" in by_group["group_a"]
    assert "gamma" in by_group["group_b"]
    assert "alpha" not in by_group.get("group_b", [])


# ---------------------------------------------------------------------------
# Config file parsing
# ---------------------------------------------------------------------------

SIMPLE_CONFIG = """\
&timestep
step_per_day = 36  ! number of time steps per day
run_length   = 1   ! total run length
/

&paths
MeshPath = '/data/mesh/'  ! path to mesh files
/
"""

def test_config_groups_detected():
    rows = parse_config_file(_write_nml(SIMPLE_CONFIG))
    groups = {r[1] for r in rows}
    assert "timestep" in groups
    assert "paths" in groups

def test_config_params_detected():
    rows = parse_config_file(_write_nml(SIMPLE_CONFIG))
    params = {(r[1], r[2]) for r in rows}
    assert ("timestep", "step_per_day") in params
    assert ("timestep", "run_length") in params
    assert ("paths", "MeshPath") in params

def test_config_description_extracted():
    rows = parse_config_file(_write_nml(SIMPLE_CONFIG))
    by_param = {r[2]: r[3] for r in rows}
    assert "number of time steps per day" in by_param["step_per_day"]

def test_config_param_without_comment_has_empty_description():
    src = "&foo\nbar = 1\n/\n"
    rows = parse_config_file(_write_nml(src))
    assert rows[0][3] == ""

def test_config_continuation_comment_appended():
    src = """\
&foo
param = 1  ! first line description
           ! continued description
/
"""
    rows = parse_config_file(_write_nml(src))
    assert "continued description" in rows[0][3]

def test_config_pure_comment_lines_skipped():
    src = """\
&foo
! this is a section header
param = 1  ! description
/
"""
    rows = parse_config_file(_write_nml(src))
    assert len(rows) == 1
    assert rows[0][2] == "param"


# ---------------------------------------------------------------------------
# Pipeline integration: namelist_refs and namelist_descriptions in DuckDB
# ---------------------------------------------------------------------------

def _make_db(f90_content: str, nml_content: str) -> object:
    """Build a temporary DuckDB with one F90 file and one config file."""
    import duckdb
    from src.fesom2.indexer.schema import DDL
    from src.fesom2.indexer.extract import extract_file
    from src.fesom2.indexer.namelist_config import parse_config_file

    con = duckdb.connect(":memory:")
    con.execute(DDL)

    f90_path = _write_f90(f90_content)
    mods, _ = extract_file(f90_path)
    sub_id = 1
    for mod in mods:
        con.execute("INSERT INTO modules VALUES (?, ?, ?, ?, ?)",
                    [sub_id, mod.name, mod.file, mod.start_line, mod.end_line])
        for group, params, line in mod.namelist_groups:
            for param in params:
                con.execute("INSERT INTO namelist_refs VALUES (?, ?, ?, ?, ?)",
                            [param, group, mod.file, mod.name, line])
        sub_id += 1

    nml_path = _write_nml(nml_content)
    for config_file, group, param, desc in parse_config_file(nml_path):
        con.execute("INSERT INTO namelist_descriptions VALUES (?, ?, ?, ?)",
                    [param, group, config_file, desc])
    return con


def test_namelist_refs_populated():
    con = _make_db(SIMPLE_NML_MODULE, SIMPLE_CONFIG)
    rows = con.execute("SELECT param_name, namelist_group, module_name FROM namelist_refs").fetchall()
    param_names = [r[0] for r in rows]
    assert "step_per_day" in param_names

def test_namelist_refs_module_name_correct():
    con = _make_db(SIMPLE_NML_MODULE, SIMPLE_CONFIG)
    rows = con.execute(
        "SELECT module_name FROM namelist_refs WHERE param_name = 'step_per_day'"
    ).fetchall()
    assert rows[0][0] == "g_config"

def test_namelist_descriptions_populated():
    con = _make_db(SIMPLE_NML_MODULE, SIMPLE_CONFIG)
    rows = con.execute("SELECT param_name, description FROM namelist_descriptions").fetchall()
    by_param = {r[0]: r[1] for r in rows}
    assert "step_per_day" in by_param
    assert "number of time steps per day" in by_param["step_per_day"]

def test_namelist_to_code_query():
    """The key query: which module reads namelist parameter X?"""
    con = _make_db(SIMPLE_NML_MODULE, SIMPLE_CONFIG)
    rows = con.execute("""
        SELECT r.module_name, r.namelist_group, d.description
        FROM namelist_refs r
        LEFT JOIN namelist_descriptions d
          ON lower(r.param_name) = lower(d.param_name)
         AND lower(r.namelist_group) = lower(d.namelist_group)
        WHERE lower(r.param_name) = 'step_per_day'
    """).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "g_config"
    assert rows[0][1] == "timestep"
    assert "number of time steps per day" in rows[0][2]
