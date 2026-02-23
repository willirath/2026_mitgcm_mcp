"""Build a structured catalogue of MITgcm verification/tutorial experiments.

All fields are derived automatically from experiment files — no hand-labelling.
"""

from pathlib import Path

from .parse import parse_data_namelist, parse_packages_conf, parse_size_h

MITGCM = Path("MITgcm")
EXPERIMENT_DIRS = [MITGCM / "verification"]

# Package name fragments that imply a domain class.
# Checked as substrings of lowercased package names, in priority order.
_COUPLED_HINTS = ("oasis", "cpl_aim", "cpl_ocn", "compon_interf")
_ATMOS_HINTS = ("aim", "fizhi", "atm_compon")
_OCEAN_HINTS = ("seaice", "kpp", "obcs", "gmredi", "saltplume", "shelfice", "streamice")


def _domain_class(packages: list[str]) -> str:
    pkg_lower = [p.lower() for p in packages]
    for p in pkg_lower:
        if any(h in p for h in _COUPLED_HINTS):
            return "coupled"
    for p in pkg_lower:
        if any(h in p for h in _ATMOS_HINTS):
            return "atmosphere"
    for p in pkg_lower:
        if any(h in p for h in _OCEAN_HINTS):
            return "ocean"
    return "idealized"


def build_catalogue(dirs: list[Path] | None = None) -> list[dict]:
    """Return structured catalogue of all verification/tutorial experiments.

    Each entry is a dict with keys:
      name          : str        — directory name
      tutorial      : bool       — True if name starts with "tutorial_"
      packages      : list[str]
      domain_class  : str        — "ocean"|"atmosphere"|"coupled"|"idealized"
      Nx, Ny, Nr    : int|None   — total domain dimensions
      grid_type     : str        — "cartesian"|"spherical_polar"|"curvilinear"
      nonhydrostatic: bool
      free_surface  : bool
      eos_type      : str
      files         : list[str]  — all files relative to the experiment root
    """
    dirs = dirs or EXPERIMENT_DIRS
    entries = []

    for base_dir in dirs:
        if not base_dir.exists():
            continue
        for exp_dir in sorted(base_dir.iterdir()):
            if not exp_dir.is_dir() or exp_dir.name == "README.md":
                continue

            entry: dict = {
                "name": exp_dir.name,
                "tutorial": exp_dir.name.startswith("tutorial_"),
            }

            # Packages
            pkg_file = exp_dir / "code" / "packages.conf"
            entry["packages"] = parse_packages_conf(pkg_file) if pkg_file.exists() else []
            entry["domain_class"] = _domain_class(entry["packages"])

            # Grid dimensions from SIZE.h
            size_file = exp_dir / "code" / "SIZE.h"
            dims = parse_size_h(size_file) if size_file.exists() else {}
            entry["Nx"] = dims.get("Nx")
            entry["Ny"] = dims.get("Ny")
            entry["Nr"] = dims.get("Nr")

            # Physics flags from input/data
            data_file = exp_dir / "input" / "data"
            physics = parse_data_namelist(data_file) if data_file.exists() else {}
            entry["grid_type"] = physics.get("grid_type", "cartesian")
            entry["nonhydrostatic"] = physics.get("nonhydrostatic", False)
            entry["free_surface"] = physics.get("free_surface", True)
            entry["eos_type"] = physics.get("eos_type", "LINEAR")

            # File listing — all files relative to the experiment root
            entry["files"] = sorted(
                p.relative_to(exp_dir).as_posix()
                for p in exp_dir.rglob("*")
                if p.is_file()
            )

            entries.append(entry)

    return entries
