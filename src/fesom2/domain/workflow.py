"""Recommended tool workflows for common FESOM2 agent tasks."""

_WORKFLOWS: dict = {
    "design_experiment": {
        "description": (
            "Design a new FESOM2 experiment from physical parameters. "
            "Start from the closest reference namelist or CI setup, then "
            "adapt namelist parameters to your geometry and physics."
        ),
        "steps": [
            {
                "tool": "suggest_experiment_config_tool",
                "purpose": (
                    "Get a skeleton namelist configuration for your experiment "
                    "class (baroclinic_channel, pi_control, rotating_convection). "
                    "Use the returned namelists and notes as your starting checklist."
                ),
            },
            {
                "tool": "list_setups_tool",
                "purpose": (
                    "Browse reference namelists (source='reference_namelist') for "
                    "complete annotated starting configs, and CI setups "
                    "(source='ci_setup') to see which parameter changes distinguish "
                    "physics variants (e.g. cavity, icepack, zstar, linfs). "
                    "Filter by name to find the closest match to your experiment."
                ),
            },
            {
                "tool": "translate_lab_params_tool",
                "purpose": (
                    "Convert physical parameters (domain size, rotation rate, "
                    "temperature contrast) to concrete namelist values "
                    "(step_per_day, f_plane_lat, tAlpha, etc.)."
                ),
            },
            {
                "tool": "check_scales_tool",
                "purpose": (
                    "Compute Rossby, Ekman, Burger numbers and verify CFL. "
                    "Resolve all flagged warnings before running."
                ),
            },
            {
                "tool": "lookup_gotcha_tool",
                "purpose": (
                    "Search the FESOM2 gotcha catalogue for known traps relevant to "
                    "your setup (e.g. 'ALE', 'step_per_day', 'EVP', 'METIS', "
                    "'forcing interpolation', 'namelist.io', 'cavity')."
                ),
            },
            {
                "tool": "get_namelist_structure_tool",
                "purpose": (
                    "Orient yourself in namelist space: see which namelist files "
                    "exist, which groups each file contains, and what each group "
                    "controls. Use before editing unfamiliar namelist files."
                ),
            },
        ],
        "notes": [
            "FESOM2 is CMake-based — there are no CPP flags to set beyond the build options.",
            "Always precompute METIS partition files and forcing interpolation weights before the first run.",
            "step_per_day must satisfy 86400 mod step_per_day == 0; FESOM2 enforces this at startup.",
            "For toy experiments (toy_ocean=.true.), set which_toy to 'neverworld2', 'soufflet', or 'dbgyre'.",
            "Output fields must be listed explicitly in namelist.io — unlisted fields produce no output silently.",
        ],
    },
    "debug_configuration": {
        "description": "Diagnose why a FESOM2 configuration does not run correctly.",
        "steps": [
            {
                "tool": "lookup_gotcha_tool",
                "purpose": (
                    "Search by symptom first (e.g. 'step_per_day', 'CFL', "
                    "'forcing interpolation', 'METIS', 'ALE layer collapse', "
                    "'EVP subcycling', 'namelist.io output')."
                ),
            },
            {
                "tool": "namelist_to_code_tool",
                "purpose": (
                    "Find which module reads a suspect namelist parameter. "
                    "Also returns the inline comment description from config files."
                ),
            },
            {
                "tool": "get_source_tool",
                "purpose": (
                    "Read the module source to understand what the parameter "
                    "controls and what values are valid."
                ),
            },
            {
                "tool": "search_docs_tool",
                "purpose": (
                    "Search FESOM2 documentation and namelist descriptions "
                    "for guidance on a parameter or behaviour."
                ),
            },
            {
                "tool": "search_code_tool",
                "purpose": (
                    "Semantic search when you don't know the module name — "
                    "e.g. search for the error message string or the phenomenon "
                    "you're trying to debug."
                ),
            },
        ],
        "notes": [],
    },
    "understand_module": {
        "description": "Learn what a FESOM2 F90 module does and how it fits into the model.",
        "steps": [
            {
                "tool": "find_modules_tool",
                "purpose": "Find the module by name (case-insensitive).",
            },
            {
                "tool": "get_module_tool",
                "purpose": (
                    "Get module metadata: file path, line range, and list of "
                    "subroutines and functions contained in the module."
                ),
            },
            {
                "tool": "get_module_uses_tool",
                "purpose": (
                    "See which other modules this module USEs — "
                    "the module dependency graph."
                ),
            },
            {
                "tool": "get_source_tool",
                "purpose": (
                    "Read key subroutines within the module, paginated. "
                    "Start with the init or readparms routine."
                ),
            },
            {
                "tool": "get_callers_tool",
                "purpose": "Find what calls subroutines in this module.",
            },
            {
                "tool": "get_callees_tool",
                "purpose": "Find what subroutines in this module call.",
            },
            {
                "tool": "search_docs_tool",
                "purpose": "Look for documentation covering this module or its physics.",
            },
        ],
        "notes": [
            "FESOM2 uses F90 modules (MODULE ... CONTAINS ... END MODULE), not separate files per subroutine.",
            "Module names often carry prefixes: oce_ (ocean dynamics), ice_ (sea ice), gen_ (infrastructure), io_ (I/O).",
            "MOD_DYN, MOD_ICE, MOD_MESH, MOD_PARTIT are shared data structure modules — they define arrays, not algorithms.",
        ],
    },
    "explore_code": {
        "description": "Navigate FESOM2 source to answer a specific code question.",
        "steps": [
            {
                "tool": "search_code_tool",
                "purpose": "Semantic search when you don't know the subroutine or module name.",
            },
            {
                "tool": "find_subroutines_tool",
                "purpose": "Look up a subroutine by exact name (case-insensitive).",
            },
            {
                "tool": "get_source_tool",
                "purpose": "Read subroutine source, paginated with offset/limit.",
            },
            {
                "tool": "get_callers_tool",
                "purpose": "Find what calls this subroutine.",
            },
            {
                "tool": "get_callees_tool",
                "purpose": "Find what this subroutine calls.",
            },
        ],
        "notes": [],
    },
}


def get_workflow(task: str | None = None) -> dict:
    """Return recommended tool sequences for common FESOM2 tasks.

    Parameters
    ----------
    task : str or None
        One of ``"design_experiment"``, ``"debug_configuration"``,
        ``"understand_module"``, ``"explore_code"``.
        If None, all workflows are returned.

    Returns
    -------
    dict
        Mapping of task name to workflow dict with keys:
        ``description``, ``steps`` (list of ``{tool, purpose}``), ``notes``.
        Empty dict if the task name is not recognised.
    """
    if task is not None:
        key = task.lower().strip().replace(" ", "_")
        return {key: _WORKFLOWS[key]} if key in _WORKFLOWS else {}
    return dict(_WORKFLOWS)
