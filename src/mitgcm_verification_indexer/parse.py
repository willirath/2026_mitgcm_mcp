"""Parse MITgcm experiment configuration files.

Covers:
- packages.conf  — list of enabled packages
- SIZE.h         — grid dimensions via regex (avoids Fortran parser dependency)
- input/data     — key physics flags via f90nml
"""

import re
from pathlib import Path

import f90nml


def parse_packages_conf(path: Path) -> list[str]:
    """Return list of enabled packages from packages.conf.

    Strips comments (lines starting with #) and blank lines.
    """
    packages = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            packages.append(line)
    return packages


# Matches:  PARAMETER ( sNx =  20 )  or  PARAMETER(sNx=20)
_PARAM_RE = re.compile(
    r"\bPARAMETER\s*\(\s*{name}\s*=\s*(\d+)\s*\)",
    re.IGNORECASE,
)


def _extract_int_param(text: str, name: str) -> int | None:
    m = re.search(
        rf"\bPARAMETER\s*\(\s*{name}\s*=\s*(\d+)\s*\)",
        text,
        re.IGNORECASE,
    )
    return int(m.group(1)) if m else None


def parse_size_h(path: Path) -> dict:
    """Extract grid dimensions from a SIZE.h file.

    Returns a dict with keys: sNx, sNy, Nr, nPx, nPy, nSx, nSy, Nx, Ny.
    Nx = sNx * nPx * nSx; Ny = sNy * nPy * nSy.
    Missing values default to 1 for multipliers, None for sNx/sNy/Nr.
    """
    text = path.read_text(errors="replace")
    result: dict = {}
    for name in ("sNx", "sNy", "Nr", "nPx", "nPy", "nSx", "nSy"):
        result[name] = _extract_int_param(text, name)

    snx = result.get("sNx") or 0
    sny = result.get("sNy") or 0
    npx = result.get("nPx") or 1
    npy = result.get("nPy") or 1
    nsx = result.get("nSx") or 1
    nsy = result.get("nSy") or 1
    result["Nx"] = snx * npx * nsx if snx else None
    result["Ny"] = sny * npy * nsy if sny else None
    return result


def parse_data_namelist(path: Path) -> dict:
    """Extract key physics flags from input/data using f90nml.

    Returns a dict with keys:
      grid_type      : "cartesian" | "spherical_polar" | "curvilinear"
      nonhydrostatic : bool
      free_surface   : bool (True = free surface, False = rigid lid)
      eos_type       : str  (e.g. "LINEAR", "JMD95Z", "MDJWF")

    Falls back to safe defaults on parse errors.
    """
    defaults = {
        "grid_type": "cartesian",
        "nonhydrostatic": False,
        "free_surface": True,
        "eos_type": "LINEAR",
    }
    try:
        nml = f90nml.read(str(path))
    except Exception:
        return defaults

    result = dict(defaults)

    # PARM01 — basic physics
    p1 = {k.lower(): v for k, v in nml.get("parm01", {}).items()}
    eos = p1.get("eostype", "LINEAR")
    result["eos_type"] = str(eos).upper().strip("'\" ")
    result["nonhydrostatic"] = bool(p1.get("nonhydrostatic", False))
    result["free_surface"] = not bool(p1.get("rigidlid", False))

    # PARM04 — grid type
    p4 = {k.lower(): v for k, v in nml.get("parm04", {}).items()}
    if p4.get("usingsphericalpolargrid", False):
        result["grid_type"] = "spherical_polar"
    elif p4.get("usingcurvilineargrid", False):
        result["grid_type"] = "curvilinear"
    else:
        result["grid_type"] = "cartesian"

    return result
