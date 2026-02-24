"""Tests for src/verification_indexer/catalogue.py using synthetic fixtures."""

import textwrap
from pathlib import Path

import pytest

from src.mitgcm.verification_indexer.catalogue import _domain_class, build_catalogue


# ---------------------------------------------------------------------------
# _domain_class
# ---------------------------------------------------------------------------


def test_domain_class_ocean():
    assert _domain_class(["gfd", "kpp", "diagnostics"]) == "ocean"


def test_domain_class_atmosphere():
    assert _domain_class(["aim_v23", "diagnostics"]) == "atmosphere"


def test_domain_class_coupled():
    assert _domain_class(["gfd", "cpl_oasis3"]) == "coupled"


def test_domain_class_idealized():
    assert _domain_class(["gfd", "diagnostics"]) == "idealized"


def test_domain_class_empty():
    assert _domain_class([]) == "idealized"


def test_domain_class_coupled_takes_priority_over_ocean():
    assert _domain_class(["seaice", "cpl_oasis3"]) == "coupled"


def test_domain_class_atmos_takes_priority_over_idealized():
    assert _domain_class(["fizhi", "diagnostics"]) == "atmosphere"


# ---------------------------------------------------------------------------
# build_catalogue
# ---------------------------------------------------------------------------


def _make_experiment(base: Path, name: str, packages: list[str], size_h: str, data: str) -> Path:
    exp = base / name
    (exp / "code").mkdir(parents=True)
    (exp / "input").mkdir(parents=True)
    (exp / "code" / "packages.conf").write_text("\n".join(packages) + "\n")
    (exp / "code" / "SIZE.h").write_text(size_h)
    (exp / "input" / "data").write_text(data)
    return exp


_SIZE_H = textwrap.dedent("""\
      PARAMETER ( sNx =  20 )
      PARAMETER ( sNy =  20 )
      PARAMETER ( Nr  =   5 )
      PARAMETER ( nPx =   1 )
      PARAMETER ( nPy =   1 )
      PARAMETER ( nSx =   1 )
      PARAMETER ( nSy =   1 )
""")

_DATA_OCEAN = textwrap.dedent("""\
 &PARM01
  eosType='LINEAR',
 &END
 &PARM04
  usingCartesianGrid=.TRUE.,
 &END
""")

_DATA_SPHERICAL = textwrap.dedent("""\
 &PARM01
  eosType='JMD95Z',
 &END
 &PARM04
  usingSphericalPolarGrid=.TRUE.,
 &END
""")


def test_build_catalogue_basic(tmp_path):
    _make_experiment(tmp_path, "my_ocean_exp", ["gfd", "kpp"], _SIZE_H, _DATA_OCEAN)
    catalogue = build_catalogue(dirs=[tmp_path])
    assert len(catalogue) == 1
    e = catalogue[0]
    assert e["name"] == "my_ocean_exp"
    assert e["domain_class"] == "ocean"
    assert "kpp" in e["packages"]
    assert e["Nx"] == 20
    assert e["Ny"] == 20
    assert e["Nr"] == 5
    assert e["grid_type"] == "cartesian"
    assert e["eos_type"] == "LINEAR"
    assert e["free_surface"] is True


def test_build_catalogue_tutorial_flag(tmp_path):
    _make_experiment(tmp_path, "tutorial_rotating_tank", ["gfd"], _SIZE_H, _DATA_OCEAN)
    catalogue = build_catalogue(dirs=[tmp_path])
    assert catalogue[0]["tutorial"] is True


def test_build_catalogue_non_tutorial_flag(tmp_path):
    _make_experiment(tmp_path, "exp_ocean", ["gfd"], _SIZE_H, _DATA_OCEAN)
    catalogue = build_catalogue(dirs=[tmp_path])
    assert catalogue[0]["tutorial"] is False


def test_build_catalogue_spherical(tmp_path):
    _make_experiment(tmp_path, "global_ocean", ["gfd", "obcs"], _SIZE_H, _DATA_SPHERICAL)
    catalogue = build_catalogue(dirs=[tmp_path])
    e = catalogue[0]
    assert e["grid_type"] == "spherical_polar"
    assert e["eos_type"] == "JMD95Z"


def test_build_catalogue_missing_files(tmp_path):
    """Experiment with no code/ or input/ files should still produce an entry."""
    exp = tmp_path / "bare_exp"
    exp.mkdir()
    catalogue = build_catalogue(dirs=[tmp_path])
    assert len(catalogue) == 1
    e = catalogue[0]
    assert e["packages"] == []
    assert e["Nx"] is None
    assert e["grid_type"] == "cartesian"  # default


def test_build_catalogue_multiple_experiments(tmp_path):
    _make_experiment(tmp_path, "exp_a", ["gfd"], _SIZE_H, _DATA_OCEAN)
    _make_experiment(tmp_path, "exp_b", ["aim_v23"], _SIZE_H, _DATA_OCEAN)
    catalogue = build_catalogue(dirs=[tmp_path])
    names = [e["name"] for e in catalogue]
    assert "exp_a" in names
    assert "exp_b" in names
    classes = {e["name"]: e["domain_class"] for e in catalogue}
    assert classes["exp_a"] == "idealized"
    assert classes["exp_b"] == "atmosphere"


def test_build_catalogue_files_listing(tmp_path):
    _make_experiment(tmp_path, "exp_files", ["gfd"], _SIZE_H, _DATA_OCEAN)
    catalogue = build_catalogue(dirs=[tmp_path])
    files = catalogue[0]["files"]
    assert "code/packages.conf" in files
    assert "code/SIZE.h" in files
    assert "input/data" in files


def test_build_catalogue_skips_non_directories(tmp_path):
    """README.md and other files in the base dir are skipped."""
    _make_experiment(tmp_path, "real_exp", ["gfd"], _SIZE_H, _DATA_OCEAN)
    (tmp_path / "README.md").write_text("# readme")
    catalogue = build_catalogue(dirs=[tmp_path])
    assert len(catalogue) == 1


def test_build_catalogue_nonexistent_dir(tmp_path):
    """Non-existent base dir produces empty catalogue without error."""
    catalogue = build_catalogue(dirs=[tmp_path / "does_not_exist"])
    assert catalogue == []
