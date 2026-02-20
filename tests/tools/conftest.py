"""Shared fixtures for tools tests."""

import pytest
from src.indexer.schema import connect


@pytest.fixture(scope="session")
def test_db(tmp_path_factory):
    """Session-scoped DuckDB file with minimal synthetic rows."""
    db_path = tmp_path_factory.mktemp("db") / "test.duckdb"

    con = connect(db_path)

    # 2 subroutines
    con.execute(
        "INSERT INTO subroutines (id, name, file, package, line_start, line_end, source_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [1, "CG3D", "model/src/cg3d.F", "model", 1, 100, "SUBROUTINE CG3D\nEND"],
    )
    con.execute(
        "INSERT INTO subroutines (id, name, file, package, line_start, line_end, source_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [2, "PRE_CG3D", "model/src/pre_cg3d.F", "model", 1, 50, "SUBROUTINE PRE_CG3D\nEND"],
    )

    # 1 call: PRE_CG3D → CG3D
    con.execute("INSERT INTO calls (caller_id, callee_name) VALUES (?, ?)", [2, "CG3D"])

    # 1 namelist_ref: cg3dMaxIters → subroutine 1, group PARM02
    con.execute(
        "INSERT INTO namelist_refs (param_name, subroutine_id, namelist_group) VALUES (?, ?, ?)",
        ["cg3dMaxIters", 1, "PARM02"],
    )

    # 1 diagnostics_fill: field RHOAnoma, subroutine 1, array rho3d
    con.execute(
        "INSERT INTO diagnostics_fills (field_name, subroutine_id, array_name) VALUES (?, ?, ?)",
        ["RHOAnoma", 1, "rho3d"],
    )

    # 1 diagnostics_fill with trailing space (to test trim)
    con.execute(
        "INSERT INTO diagnostics_fills (field_name, subroutine_id, array_name) VALUES (?, ?, ?)",
        ["WdRHO_P ", 1, "wdrho3d"],
    )

    # 1 cpp_guard: subroutine 1 guarded by ALLOW_NONHYDROST
    con.execute(
        "INSERT INTO cpp_guards (subroutine_id, cpp_flag) VALUES (?, ?)",
        [1, "ALLOW_NONHYDROST"],
    )

    # 1 package_options row
    con.execute(
        "INSERT INTO package_options (package_name, cpp_flag, description) VALUES (?, ?, ?)",
        ["model", "ALLOW_NONHYDROST", "Enable non-hydrostatic solver"],
    )

    con.close()
    return db_path


@pytest.fixture(scope="session")
def adv_db(tmp_path_factory):
    """Session-scoped DuckDB for adversarial edge cases.

    Subroutines
    -----------
    10  SOLVE_FOR_P   nonhydrost  calls CG3D (twice), CG2D, EXTERNAL_ROUTINE
                                  two CPP guards; one namelist ref; two diag fills
    11  CG3D          nonhydrost  two callers (SOLVE_FOR_P, INIT_CG3D)
                                  one CPP guard; two namelist params (same group)
                                  one diag fill with trailing space in stored name
    12  CG2D          nonhydrost  one caller (SOLVE_FOR_P); one CPP guard
                                  one diag fill (same field as CG3D → two sources)
    13  INIT_CG3D     model       one callee (CG3D); no guards
                                  same namelist param as CG3D but different group
    14  LEAF_SUB      model       no callers, no callees, no guards, no refs, no fills
    """
    db_path = tmp_path_factory.mktemp("advdb") / "adv.duckdb"
    con = connect(db_path)

    subs = [
        (10, "SOLVE_FOR_P", "nonhydrost/src/solve_for_p.F", "nonhydrost", 1, 200, "SUBROUTINE SOLVE_FOR_P\nEND"),
        (11, "CG3D",        "nonhydrost/src/cg3d.F",        "nonhydrost", 1, 350, "SUBROUTINE CG3D\nEND"),
        (12, "CG2D",        "nonhydrost/src/cg2d.F",        "nonhydrost", 1, 300, "SUBROUTINE CG2D\nEND"),
        (13, "INIT_CG3D",   "model/src/init_cg3d.F",        "model",      1,  80, "SUBROUTINE INIT_CG3D\nEND"),
        (14, "LEAF_SUB",    "model/src/leaf_sub.F",          "model",      1,  20, "SUBROUTINE LEAF_SUB\nEND"),
    ]
    for row in subs:
        con.execute(
            "INSERT INTO subroutines (id, name, file, package, line_start, line_end, source_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
            list(row),
        )

    # calls — SOLVE_FOR_P → CG3D appears twice (dedup test), plus CG2D and an unknown external
    calls = [
        (10, "CG3D"),
        (10, "CG3D"),           # duplicate row — get_callees must deduplicate
        (10, "CG2D"),
        (10, "EXTERNAL_ROUTINE"),  # callee not in subroutines table
        (13, "CG3D"),           # INIT_CG3D also calls CG3D → two callers for CG3D
    ]
    for caller_id, callee_name in calls:
        con.execute("INSERT INTO calls (caller_id, callee_name) VALUES (?, ?)", [caller_id, callee_name])

    # namelist_refs
    namelist_refs = [
        ("cg3dMaxIters",        11, "PARM03"),   # CG3D
        ("cg3dTargetResidual",  11, "PARM03"),   # CG3D — second param, same group
        ("cg3dMaxIters",        13, "PARM02"),   # INIT_CG3D — same param, different group
        ("nonHydrostSolver",    10, "PARM04"),   # SOLVE_FOR_P
    ]
    for param, sub_id, group in namelist_refs:
        con.execute(
            "INSERT INTO namelist_refs (param_name, subroutine_id, namelist_group) VALUES (?, ?, ?)",
            [param, sub_id, group],
        )

    # diagnostics_fills — PHInhyd filled by both CG3D (trailing space) and CG2D
    diag_fills = [
        ("PHInhyd ",   11, "phi3d"),    # trailing space in stored name
        ("PHInhyd",    12, "phi2d"),    # clean name, same field → two sources
        ("PHISURF  ",  10, "phisurf"),  # two trailing spaces
    ]
    for field, sub_id, arr in diag_fills:
        con.execute(
            "INSERT INTO diagnostics_fills (field_name, subroutine_id, array_name) VALUES (?, ?, ?)",
            [field, sub_id, arr],
        )

    # cpp_guards — SOLVE_FOR_P has two; CG3D and CG2D one each; INIT_CG3D and LEAF_SUB none
    cpp_guards = [
        (10, "ALLOW_NONHYDROST"),
        (10, "ALLOW_CG2D_NSA"),
        (11, "ALLOW_NONHYDROST"),
        (12, "ALLOW_NONHYDROST"),
    ]
    for sub_id, flag in cpp_guards:
        con.execute("INSERT INTO cpp_guards (subroutine_id, cpp_flag) VALUES (?, ?)", [sub_id, flag])

    # package_options — nonhydrost has two flags; model has none in this fixture
    pkg_opts = [
        ("nonhydrost", "ALLOW_NONHYDROST", "Enable non-hydrostatic pressure solver"),
        ("nonhydrost", "ALLOW_CG2D_NSA",   "Enable CG2D non-symmetric solver variant"),
    ]
    for pkg, flag, desc in pkg_opts:
        con.execute(
            "INSERT INTO package_options (package_name, cpp_flag, description) VALUES (?, ?, ?)",
            [pkg, flag, desc],
        )

    con.close()
    return db_path
