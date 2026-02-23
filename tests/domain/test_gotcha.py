"""Unit tests for src/domain/gotcha.py."""

import pytest

from src.domain.gotcha import lookup_gotcha


def test_nonhydrostatic_found():
    """lookup_gotcha('nonhydrostatic') should return at least one entry."""
    results = lookup_gotcha("nonhydrostatic")
    assert len(results) >= 1


def test_case_insensitive():
    """Lookup should be case-insensitive."""
    lower = lookup_gotcha("nonhydrostatic")
    upper = lookup_gotcha("NONHYDROSTATIC")
    assert lower == upper


def test_unknown_returns_empty():
    """An unrecognised topic should return an empty list."""
    assert lookup_gotcha("completely unknown xyz") == []


def test_eos_found():
    """lookup_gotcha('linear eos') should return an entry mentioning sBeta."""
    results = lookup_gotcha("linear eos")
    assert len(results) >= 1
    assert any("sbeta" in entry["detail"].lower() or "sBeta" in entry["detail"] for entry in results)


def test_spinup_found():
    """lookup_gotcha('spin-up') should return at least one entry."""
    results = lookup_gotcha("spin-up")
    assert len(results) >= 1


def test_entry_has_required_keys():
    """Every matched entry should have title, keywords, summary, detail."""
    results = lookup_gotcha("nonhydrostatic")
    for entry in results:
        assert "title" in entry
        assert "keywords" in entry
        assert "summary" in entry
        assert "detail" in entry


def test_cg3d_matches_nonhydrostatic():
    """lookup_gotcha('cg3d') should match the non-hydrostatic entry."""
    results = lookup_gotcha("cg3d")
    assert len(results) >= 1
    titles = [e["title"].lower() for e in results]
    assert any("non-hydrostatic" in t or "nonhydrostatic" in t for t in titles)


def test_diagnostics_found():
    """lookup_gotcha('diagnostics') should return at least one entry."""
    results = lookup_gotcha("diagnostics")
    assert len(results) >= 1


def test_sidewall_found():
    """lookup_gotcha('sidewall') should return an entry about boundary conditions."""
    results = lookup_gotcha("sidewall")
    assert len(results) >= 1


def test_readbinaryprec_found():
    """lookup_gotcha('readbinaryprec') should return the binary precision entry."""
    results = lookup_gotcha("readbinaryprec")
    assert len(results) >= 1
    assert any("precision" in e["title"].lower() or "readbinaryprec" in e["title"].lower() for e in results)


def test_float64_matches_readbinaryprec():
    """lookup_gotcha('float64') should match the binary precision entry."""
    results = lookup_gotcha("float64")
    assert len(results) >= 1
    assert any("readBinaryPrec" in e["detail"] or "readbinaryprec" in e["title"].lower() for e in results)


def test_phihyd_found():
    """lookup_gotcha('phihyd') should return the INCLUDE_PHIHYD entry."""
    results = lookup_gotcha("phihyd")
    assert len(results) >= 1
    assert any("INCLUDE_PHIHYD" in e["detail"] for e in results)


def test_gfd_packages_found():
    """lookup_gotcha('packages.conf') should return the gfd group entry."""
    results = lookup_gotcha("packages.conf")
    assert len(results) >= 1
    assert any("gfd" in e["detail"] for e in results)


def test_size_h_max_olx_found():
    """lookup_gotcha('MAX_OLX') should return the SIZE.h entry."""
    results = lookup_gotcha("MAX_OLX")
    assert len(results) >= 1
    assert any("SIZE.h" in e["title"] or "MAX_OLX" in e["detail"] for e in results)


def test_mpi_flag_found():
    """lookup_gotcha('-mpi') should return the genmake2 MPI entry."""
    results = lookup_gotcha("-mpi")
    assert len(results) >= 1
    assert any("genmake2" in e["title"].lower() or "-mpi" in e["detail"] for e in results)
