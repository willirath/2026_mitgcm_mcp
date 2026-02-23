"""Tests for src/verification_indexer/parse.py using synthetic fixtures."""

import textwrap
from pathlib import Path

import pytest

from src.verification_indexer.parse import (
    parse_data_namelist,
    parse_packages_conf,
    parse_size_h,
)


# ---------------------------------------------------------------------------
# parse_packages_conf
# ---------------------------------------------------------------------------


def test_packages_conf_basic(tmp_path):
    p = tmp_path / "packages.conf"
    p.write_text("gfd\nkpp\ndiagnostics\n")
    assert parse_packages_conf(p) == ["gfd", "kpp", "diagnostics"]


def test_packages_conf_strips_comments(tmp_path):
    p = tmp_path / "packages.conf"
    p.write_text("# This is a comment\ngfd\n# another comment\nkpp\n")
    assert parse_packages_conf(p) == ["gfd", "kpp"]


def test_packages_conf_strips_blank_lines(tmp_path):
    p = tmp_path / "packages.conf"
    p.write_text("\ngfd\n\nkpp\n\n")
    assert parse_packages_conf(p) == ["gfd", "kpp"]


def test_packages_conf_empty(tmp_path):
    p = tmp_path / "packages.conf"
    p.write_text("# only comments\n")
    assert parse_packages_conf(p) == []


# ---------------------------------------------------------------------------
# parse_size_h
# ---------------------------------------------------------------------------

_SIZE_H_TYPICAL = textwrap.dedent("""\
      INTEGER sNx
      PARAMETER ( sNx =  30 )
      INTEGER sNy
      PARAMETER ( sNy =  20 )
      INTEGER Nr
      PARAMETER ( Nr =  10 )
      INTEGER nSx
      PARAMETER ( nSx =   1 )
      INTEGER nSy
      PARAMETER ( nSy =   1 )
      INTEGER nPx
      PARAMETER ( nPx =   2 )
      INTEGER nPy
      PARAMETER ( nPy =   1 )
""")


def test_size_h_basic(tmp_path):
    p = tmp_path / "SIZE.h"
    p.write_text(_SIZE_H_TYPICAL)
    result = parse_size_h(p)
    assert result["sNx"] == 30
    assert result["sNy"] == 20
    assert result["Nr"] == 10
    assert result["nPx"] == 2
    assert result["nPy"] == 1
    # Nx = sNx * nPx * nSx = 30 * 2 * 1 = 60
    assert result["Nx"] == 60
    # Ny = sNy * nPy * nSy = 20 * 1 * 1 = 20
    assert result["Ny"] == 20


def test_size_h_no_mpi(tmp_path):
    """nPx/nPy absent → treated as 1."""
    p = tmp_path / "SIZE.h"
    p.write_text("      PARAMETER ( sNx =  10 )\n      PARAMETER ( sNy =  10 )\n      PARAMETER ( Nr =   5 )\n")
    result = parse_size_h(p)
    assert result["Nx"] == 10
    assert result["Ny"] == 10


def test_size_h_missing_snx(tmp_path):
    """sNx absent → Nx is None."""
    p = tmp_path / "SIZE.h"
    p.write_text("      PARAMETER ( sNy =  10 )\n      PARAMETER ( Nr =   5 )\n")
    result = parse_size_h(p)
    assert result["Nx"] is None
    assert result["Ny"] == 10


def test_size_h_compact_syntax(tmp_path):
    """No spaces around = in PARAMETER."""
    p = tmp_path / "SIZE.h"
    p.write_text("PARAMETER(sNx=16)\nPARAMETER(sNy=8)\nPARAMETER(Nr=4)\n")
    result = parse_size_h(p)
    assert result["sNx"] == 16
    assert result["Nx"] == 16


# ---------------------------------------------------------------------------
# parse_data_namelist
# ---------------------------------------------------------------------------

_DATA_LINEAR_CARTESIAN = textwrap.dedent("""\
 &PARM01
  viscAh=1.E-4,
  diffKhT=1.E-5,
  eosType='LINEAR',
  tAlpha=2.E-4,
  sBeta=0.,
 &END
 &PARM04
  usingCartesianGrid=.TRUE.,
  delX=30*500.,
  delY=20*500.,
  delZ=10*50.,
 &END
""")

_DATA_SPHERICAL_RIGIID_LID = textwrap.dedent("""\
 &PARM01
  rigidLid=.TRUE.,
  eosType='JMD95Z',
 &END
 &PARM04
  usingSphericalPolarGrid=.TRUE.,
 &END
""")

_DATA_NONHYDROSTATIC = textwrap.dedent("""\
 &PARM01
  nonHydrostatic=.TRUE.,
  eosType='LINEAR',
 &END
""")


def test_parse_data_linear_cartesian(tmp_path):
    p = tmp_path / "data"
    p.write_text(_DATA_LINEAR_CARTESIAN)
    result = parse_data_namelist(p)
    assert result["grid_type"] == "cartesian"
    assert result["eos_type"] == "LINEAR"
    assert result["nonhydrostatic"] is False
    assert result["free_surface"] is True


def test_parse_data_spherical_rigid_lid(tmp_path):
    p = tmp_path / "data"
    p.write_text(_DATA_SPHERICAL_RIGIID_LID)
    result = parse_data_namelist(p)
    assert result["grid_type"] == "spherical_polar"
    assert result["free_surface"] is False
    assert result["eos_type"] == "JMD95Z"


def test_parse_data_nonhydrostatic(tmp_path):
    p = tmp_path / "data"
    p.write_text(_DATA_NONHYDROSTATIC)
    result = parse_data_namelist(p)
    assert result["nonhydrostatic"] is True


def test_parse_data_missing_file_returns_defaults(tmp_path):
    p = tmp_path / "data"
    # File does not exist — caller is expected to check, but parse should not crash
    # on an empty/unparseable file
    p.write_text("this is not valid fortran namelist !!!")
    result = parse_data_namelist(p)
    # Should return safe defaults without raising
    assert "grid_type" in result
    assert "free_surface" in result
