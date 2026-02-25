"""Tests for src/fesom2/setups.py — uses synthetic fixtures only."""

import textwrap

import pytest

from src.fesom2.setups import (
    _parse_fortran_namelist,
    _split_value_comment,
    list_setups,
)


# ── _split_value_comment ──────────────────────────────────────────────────────


def test_split_plain_value():
    assert _split_value_comment("  42  ") == ("42", "")


def test_split_value_with_comment():
    value, comment = _split_value_comment("  42  ! number of steps")
    assert value == "42"
    assert comment == "number of steps"


def test_split_quoted_string_no_false_split():
    # The ! inside the comment is after the quoted string
    value, comment = _split_value_comment("  'JRA'  ! forcing type")
    assert value == "'JRA'"
    assert comment == "forcing type"


def test_split_quoted_string_with_embedded_apostrophe():
    # Fortran double-apostrophe inside string: 'it''s fine'
    value, comment = _split_value_comment("  'it''s fine'  ! description")
    assert value == "'it''s fine'"
    assert "description" in comment


def test_split_logical():
    value, comment = _split_value_comment("  .true.  ! enable sea ice")
    assert value == ".true."
    assert "sea ice" in comment


# ── _parse_fortran_namelist ───────────────────────────────────────────────────

_SIMPLE_NML = textwrap.dedent("""\
    ! File-level comment — ignored
    &timestep
    step_per_day = 48    ! steps per day
    run_length   = 10    ! years
    /
    &run_config
    use_ice = .false.    ! disable ice
    toy_ocean = .true.   ! toy mode
    /
""")


def test_parse_groups():
    result = _parse_fortran_namelist(_SIMPLE_NML)
    assert "timestep" in result
    assert "run_config" in result


def test_parse_param_value():
    result = _parse_fortran_namelist(_SIMPLE_NML)
    assert result["timestep"]["step_per_day"]["value"] == "48"


def test_parse_param_comment():
    result = _parse_fortran_namelist(_SIMPLE_NML)
    assert "steps per day" in result["timestep"]["step_per_day"]["comment"]


def test_parse_logical():
    result = _parse_fortran_namelist(_SIMPLE_NML)
    assert result["run_config"]["use_ice"]["value"] == ".false."


def test_parse_param_names_lowercased():
    nml = "&Timestep\nStep_Per_Day = 32 ! comment\n/"
    result = _parse_fortran_namelist(nml)
    assert "timestep" in result
    assert "step_per_day" in result["timestep"]


def test_parse_group_names_lowercased():
    nml = "&RUN_CONFIG\nuse_ice = .true.\n/"
    result = _parse_fortran_namelist(nml)
    assert "run_config" in result


def test_parse_standalone_comment_lines_skipped():
    nml = textwrap.dedent("""\
        &timestep
        ! This is a standalone comment
        step_per_day = 32 ! steps
        ! Another comment
        run_length = 1    ! years
        /
    """)
    result = _parse_fortran_namelist(nml)
    # Standalone comment lines should not appear as params
    assert len(result["timestep"]) == 2
    assert "step_per_day" in result["timestep"]
    assert "run_length" in result["timestep"]


def test_parse_multiple_groups():
    nml = "&grp1\na = 1 ! one\n/\n&grp2\nb = 2 ! two\n/"
    result = _parse_fortran_namelist(nml)
    assert result["grp1"]["a"]["value"] == "1"
    assert result["grp2"]["b"]["value"] == "2"


def test_parse_string_value():
    nml = "&paths\nMeshPath = '/data/mesh/' ! mesh directory\n/"
    result = _parse_fortran_namelist(nml)
    assert result["paths"]["meshpath"]["value"] == "'/data/mesh/'"


def test_parse_empty_file():
    assert _parse_fortran_namelist("") == {}


def test_parse_no_comments():
    nml = "&timestep\nstep_per_day = 96\n/"
    result = _parse_fortran_namelist(nml)
    assert result["timestep"]["step_per_day"]["comment"] == ""


# ── list_setups — synthetic filesystem ───────────────────────────────────────


@pytest.fixture()
def fake_fesom2_root(tmp_path):
    """Create a minimal synthetic FESOM2 repo layout."""
    # Reference namelist: two files for toy_test config
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "namelist.config.toy_test").write_text(
        textwrap.dedent("""\
            &timestep
            step_per_day = 72   ! steps per day
            run_length   = 5    ! years
            /
            &run_config
            use_ice   = .false. ! no ice
            toy_ocean = .true.  ! toy mode
            /
        """),
        encoding="utf-8",
    )
    (config_dir / "namelist.oce.toy_test").write_text(
        textwrap.dedent("""\
            &oce_dyn
            K_GM_max = 1000.0   ! GM diffusivity cap
            Fer_GM   = .false.  ! disable Ferrari GM
            /
        """),
        encoding="utf-8",
    )

    # Reference namelist: forcing-only (two-part name, single namelist file)
    (config_dir / "namelist.forcing.TESTCORE").write_text(
        textwrap.dedent("""\
            &forcing
            wind_data_source = 'CORE2' ! wind source
            /
        """),
        encoding="utf-8",
    )

    # CI setup: test_alpha
    setup_a = tmp_path / "setups" / "test_alpha"
    setup_a.mkdir(parents=True)
    (setup_a / "setup.yml").write_text(
        textwrap.dedent("""\
            mesh: alpha_mesh
            forcing: JRA55
            ntasks: 4
            namelist.config:
                timestep:
                    step_per_day: 48
                    run_length: 1
                    run_length_unit: "d"
                run_config:
                    use_ice: False
            fcheck:
                sst: 10.5
                salt: 34.8
        """),
        encoding="utf-8",
    )

    # CI setup: test_beta (no fcheck)
    setup_b = tmp_path / "setups" / "test_beta"
    setup_b.mkdir(parents=True)
    (setup_b / "setup.yml").write_text(
        textwrap.dedent("""\
            mesh: beta_mesh
            forcing: ERA5
            namelist.config:
                run_config:
                    use_cavity: True
        """),
        encoding="utf-8",
    )

    return tmp_path


def test_list_setups_returns_list(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    assert isinstance(result, list)


def test_list_setups_count(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    # 2 reference namelist groups (toy_test, TESTCORE) + 2 CI setups
    assert len(result) == 4


def test_reference_namelist_source(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    ref = [r for r in result if r["source"] == "reference_namelist"]
    assert len(ref) == 2


def test_ci_setup_source(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    ci = [r for r in result if r["source"] == "ci_setup"]
    assert len(ci) == 2


def test_reference_namelist_has_two_files(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    toy = next(r for r in result if r["name"] == "toy_test")
    assert "namelist.config" in toy["namelists"]
    assert "namelist.oce" in toy["namelists"]


def test_reference_namelist_param_value(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    toy = next(r for r in result if r["name"] == "toy_test")
    step = toy["namelists"]["namelist.config"]["timestep"]["step_per_day"]
    assert step["value"] == "72"


def test_reference_namelist_param_comment(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    toy = next(r for r in result if r["name"] == "toy_test")
    step = toy["namelists"]["namelist.config"]["timestep"]["step_per_day"]
    assert "steps per day" in step["comment"]


def test_reference_namelist_fcheck_empty(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    toy = next(r for r in result if r["name"] == "toy_test")
    assert toy["fcheck"] == {}


def test_reference_namelist_mesh_none(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    toy = next(r for r in result if r["name"] == "toy_test")
    assert toy["mesh"] is None


def test_forcing_only_reference(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    forcing = next(r for r in result if r["name"] == "TESTCORE")
    assert "namelist.forcing" in forcing["namelists"]
    assert forcing["namelists"]["namelist.forcing"]["forcing"]["wind_data_source"]["value"] == "'CORE2'"


def test_ci_setup_mesh(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    alpha = next(r for r in result if r["name"] == "test_alpha")
    assert alpha["mesh"] == "alpha_mesh"


def test_ci_setup_forcing(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    alpha = next(r for r in result if r["name"] == "test_alpha")
    assert alpha["forcing"] == "JRA55"


def test_ci_setup_fcheck(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    alpha = next(r for r in result if r["name"] == "test_alpha")
    assert alpha["fcheck"]["sst"] == pytest.approx(10.5)
    assert alpha["fcheck"]["salt"] == pytest.approx(34.8)


def test_ci_setup_no_fcheck(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    beta = next(r for r in result if r["name"] == "test_beta")
    assert beta["fcheck"] == {}


def test_ci_setup_namelist_overrides(fake_fesom2_root):
    result = list_setups(fake_fesom2_root)
    alpha = next(r for r in result if r["name"] == "test_alpha")
    cfg = alpha["namelists"]["namelist.config"]
    assert cfg["timestep"]["step_per_day"] == 48
    assert cfg["run_config"]["use_ice"] is False


def test_all_records_have_required_keys(fake_fesom2_root):
    for record in list_setups(fake_fesom2_root):
        for key in ("name", "source", "mesh", "forcing", "namelists", "fcheck", "notes"):
            assert key in record, f"Missing key {key!r} in record {record['name']!r}"


def test_all_records_have_nonempty_name(fake_fesom2_root):
    for record in list_setups(fake_fesom2_root):
        assert record["name"].strip()


def test_missing_config_dir_ok(tmp_path):
    """list_setups should not raise if config/ is absent."""
    (tmp_path / "setups" / "only_ci").mkdir(parents=True)
    (tmp_path / "setups" / "only_ci" / "setup.yml").write_text(
        "mesh: m\nforcing: f\n", encoding="utf-8"
    )
    result = list_setups(tmp_path)
    assert len(result) == 1
    assert result[0]["source"] == "ci_setup"


def test_missing_setups_dir_ok(tmp_path):
    """list_setups should not raise if setups/ is absent."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "namelist.config.toy_x").write_text(
        "&grp\na = 1\n/\n", encoding="utf-8"
    )
    result = list_setups(tmp_path)
    assert len(result) == 1
    assert result[0]["source"] == "reference_namelist"
