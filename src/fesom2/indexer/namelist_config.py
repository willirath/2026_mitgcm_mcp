"""Parse FESOM2 namelist config files (config/namelist.*).

Extracts (config_file, group_name, param_name, description) tuples.
Description is taken from the inline comment (after !) on the parameter's
assignment line.  Continuation comment lines (pure ! lines immediately
following) are appended to the description.
"""

import re
from pathlib import Path

FESOM2_ROOT = Path("FESOM2")
CONFIG_DIR = FESOM2_ROOT / "config"

# Match the start of a namelist group:  &group_name
RE_GROUP = re.compile(r'^\s*&(\w+)\s*$')
# End of group
RE_GROUP_END = re.compile(r'^\s*/\s*$')
# Parameter assignment:  name = value  [! comment]
RE_PARAM = re.compile(r'^\s*(\w+)\s*=')
# Inline comment
RE_INLINE_COMMENT = re.compile(r'!(.*)$')
# Pure comment line
RE_COMMENT = re.compile(r'^\s*!')


def config_files(config_dir: Path = CONFIG_DIR) -> list[Path]:
    """Return all namelist.* files in config_dir."""
    return sorted(
        p for p in config_dir.iterdir()
        if p.is_file() and p.name.startswith("namelist.")
    )


def parse_config_file(path: Path) -> list[tuple[str, str, str, str]]:
    """Parse one namelist config file.

    Returns list of (config_file, group_name, param_name, description).
    """
    try:
        lines = path.read_text(errors='replace').splitlines()
    except OSError:
        return []

    rel = str(path)
    results: list[tuple[str, str, str, str]] = []
    current_group = ''
    i = 0

    while i < len(lines):
        line = lines[i]

        # Group start
        m = RE_GROUP.match(line)
        if m:
            current_group = m.group(1)
            i += 1
            continue

        # Group end
        if RE_GROUP_END.match(line):
            current_group = ''
            i += 1
            continue

        # Skip if not inside a group
        if not current_group:
            i += 1
            continue

        # Skip pure comment and blank lines
        if RE_COMMENT.match(line) or not line.strip():
            i += 1
            continue

        # Parameter line
        pm = RE_PARAM.match(line)
        if pm:
            param = pm.group(1)
            # Grab inline comment from this line
            cm = RE_INLINE_COMMENT.search(line)
            desc = cm.group(1).strip() if cm else ''

            # Collect continuation pure-comment lines
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if RE_COMMENT.match(next_line) and not RE_GROUP.match(next_line):
                    extra = RE_INLINE_COMMENT.search(next_line)
                    if extra:
                        extra_text = extra.group(1).strip()
                        if extra_text:
                            desc = (desc + ' ' + extra_text).strip()
                    j += 1
                else:
                    break
            i = j

            results.append((rel, current_group, param, desc))
            continue

        i += 1

    return results


def parse_all_config_files(config_dir: Path = CONFIG_DIR) -> list[tuple[str, str, str, str]]:
    """Parse all namelist config files. Returns deduplicated list of
    (config_file, group_name, param_name, description).
    The canonical (first seen) description is kept when duplicates exist
    across variant files (e.g. namelist.oce.core2 vs namelist.oce).
    """
    seen: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for path in config_files(config_dir):
        for row in parse_config_file(path):
            _, group, param, _ = row
            key = (group.lower(), param.lower())
            if key not in seen:
                seen[key] = row
    return list(seen.values())
