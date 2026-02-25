"""FESOM2 setup catalogue: CI-tested configurations and reference namelists.

``list_setups()`` returns a unified list of setup records from two sources:

- **reference_namelist**: ``config/namelist.X.suffix`` files — complete,
  heavily-commented starting configurations for each experiment type.
- **ci_setup**: ``setups/*/setup.yml`` files — sparse namelist overrides used
  in CI regression testing. Each setup isolates a specific physics variant.

Each record schema
------------------
name      : str           — identifier (e.g. "toy_neverworld2", "test_pi_cavity")
source    : str           — "reference_namelist" | "ci_setup"
mesh      : str | None    — mesh name when specified
forcing   : str | None    — forcing dataset when specified
namelists : dict          — namelist file → group → param → value
            For reference_namelist: param value is {"value": str, "comment": str}
            For ci_setup: param value is the raw Python value (int/float/bool/str/dict)
fcheck    : dict          — variable → expected float (ci_setup only; {} otherwise)
notes     : str           — free-text description
"""

from pathlib import Path

import yaml


# ── Setup-specific notes ──────────────────────────────────────────────────────

_SETUP_NOTES: dict[str, str] = {
    "toy_neverworld2": (
        "Idealised Southern-Ocean-like double-gyre on a lon/lat mesh. "
        "Domain: Lx=60° (≈4700 km at 45°S), latitude -70° to +70°; "
        "re-entrant channel between -60° and -40° (Ly≈2200 km). "
        "Depth=4000 m, 15 vertical layers (toy resolution). "
        "f at channel centre (50°S) ≈ 1.11e-4 rad/s. "
        "Mesh files and generation script in experiments/fesom2/toy_neverworld2/mesh/."
    ),
    "toy_channel_dbgyre": (
        "Idealised double-gyre channel experiment on a Cartesian mesh."
    ),
    "toy_soufflet": (
        "Idealised baroclinic channel (Soufflet et al. 2016) on a Cartesian mesh."
    ),
}


# ── Fortran namelist parser ───────────────────────────────────────────────────


def _split_value_comment(rhs: str) -> tuple[str, str]:
    """Split ``value   ! comment`` into ``(value, comment)``.

    Respects single-quoted Fortran strings so that ``'it''s'`` is not
    split on the embedded apostrophe.
    """
    in_string = False
    for i, ch in enumerate(rhs):
        if ch == "'":
            in_string = not in_string
        elif ch == "!" and not in_string:
            return rhs[:i].strip(), rhs[i + 1 :].strip()
    return rhs.strip(), ""


def _parse_fortran_namelist(text: str) -> dict[str, dict[str, dict]]:
    """Parse a Fortran namelist file.

    Returns ``{group: {param: {"value": str, "comment": str}}}``.
    Group and parameter names are lowercased.
    Standalone comment lines (``! ...``) are skipped.
    Continuation comment lines (indented ``!``) are skipped.
    """
    result: dict[str, dict[str, dict]] = {}
    current_group: str | None = None
    current_params: dict[str, dict] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("!"):
            continue

        if line.startswith("&"):
            group_name = line[1:].split()[0].lower()
            current_group = group_name
            current_params = {}
            continue

        if line == "/" or line.startswith("/ ") or line.startswith("/!"):
            if current_group is not None:
                result[current_group] = current_params
                current_group = None
                current_params = {}
            continue

        if current_group is None:
            continue

        if "=" in line and not line.startswith("!"):
            lhs, _, rhs_and_comment = line.partition("=")
            param = lhs.strip().lower()
            if param:
                value, comment = _split_value_comment(rhs_and_comment)
                current_params[param] = {"value": value, "comment": comment}

    return result


# ── Reference namelist grouping ───────────────────────────────────────────────


def _group_reference_namelists(config_dir: Path) -> dict[str, dict[str, Path]]:
    """Scan ``config/`` and return ``{config_suffix: {namelist_type: path}}``.

    Matches files of the form ``namelist.X.suffix`` (exactly two dots after
    ``namelist``). Files with a single dot (e.g. ``namelist.ice_ERA5``) are
    not matched and are left for manual handling if needed.
    """
    groups: dict[str, dict[str, Path]] = {}
    for path in sorted(config_dir.glob("namelist.*.*")):
        parts = path.name.split(".", 2)
        if len(parts) < 3:
            continue
        nml_type = f"namelist.{parts[1]}"
        config_name = parts[2]
        groups.setdefault(config_name, {})[nml_type] = path
    return groups


def _build_reference_record(name: str, nml_paths: dict[str, Path]) -> dict:
    namelists = {}
    for nml_type, path in sorted(nml_paths.items()):
        namelists[nml_type] = _parse_fortran_namelist(
            path.read_text(encoding="utf-8")
        )
    return {
        "name": name,
        "source": "reference_namelist",
        "mesh": None,
        "forcing": None,
        "namelists": namelists,
        "fcheck": {},
        "notes": _SETUP_NOTES.get(name, ""),
    }


# ── CI setup parser ───────────────────────────────────────────────────────────


def _build_ci_record(name: str, setup_path: Path) -> dict:
    with setup_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    namelists = {
        k: v for k, v in raw.items() if isinstance(k, str) and k.startswith("namelist.")
    }

    return {
        "name": name,
        "source": "ci_setup",
        "mesh": raw.get("mesh"),
        "forcing": raw.get("forcing"),
        "namelists": namelists,
        "fcheck": raw.get("fcheck") or {},
        "notes": _SETUP_NOTES.get(name, ""),
    }


# ── Public API ────────────────────────────────────────────────────────────────


def list_setups(fesom2_root: str | Path) -> list[dict]:
    """Return all FESOM2 setup records.

    Parameters
    ----------
    fesom2_root:
        Path to the FESOM2 repository root (the submodule root).

    Returns
    -------
    list[dict]
        Records from ``config/namelist.*.X`` (source ``"reference_namelist"``)
        followed by records from ``setups/*/setup.yml`` (source ``"ci_setup"``),
        both sorted alphabetically by name.
    """
    root = Path(fesom2_root)
    records: list[dict] = []

    config_dir = root / "config"
    if config_dir.is_dir():
        for config_name, nml_paths in sorted(
            _group_reference_namelists(config_dir).items()
        ):
            records.append(_build_reference_record(config_name, nml_paths))

    setups_dir = root / "setups"
    if setups_dir.is_dir():
        for setup_yml in sorted(setups_dir.glob("*/setup.yml")):
            records.append(_build_ci_record(setup_yml.parent.name, setup_yml))

    return records
