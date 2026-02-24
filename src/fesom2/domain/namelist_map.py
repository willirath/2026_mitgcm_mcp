"""FESOM2 namelist file → group → description map.

All entries are explicit — FESOM2 namelists are well-organised into a small,
stable set of files and groups. The DuckDB namelist_refs table is used to
supplement with any groups not listed here.
"""

from pathlib import Path

_EXPLICIT: dict[str, dict[str, str]] = {
    "namelist.config": {
        "modelname": (
            "Run identification: ``runid`` string used as the prefix for all output "
            "and restart file names."
        ),
        "timestep": (
            "Time-stepping and run duration: ``step_per_day`` (number of baroclinic "
            "steps per day; must divide 86400 exactly), ``run_length`` and "
            "``run_length_unit`` ('y', 'm', 'd', 's'). "
            "The model time step is derived as dt = 86400 / step_per_day."
        ),
        "clockinit": (
            "Initial model time: ``timenew`` (seconds within the day), ``daynew`` "
            "(day of month), ``yearnew`` (year). Sets the starting point of the "
            "model calendar and controls which forcing year is read first."
        ),
        "paths": (
            "File system paths: ``MeshPath`` (directory containing nod2d.out, "
            "elem2d.out, etc.), ``ClimateDataPath`` (initial condition files), "
            "``ResultPath`` (output and fesom.clock directory)."
        ),
        "restart_log": (
            "Restart and log frequency: ``restart_length`` / ``restart_length_unit`` "
            "for netCDF restarts; ``raw_restart_length_unit`` / "
            "``bin_restart_length_unit`` for raw and binary restarts (use 'off' to "
            "disable). ``logfile_outfreq`` sets the log write interval in time steps."
        ),
        "ale_def": (
            "ALE vertical coordinate: ``which_ALE`` selects the scheme "
            "('linfs' = linear free surface, 'zlevel' = fixed z-levels, "
            "'zstar' = z-star with SSH scaling). "
            "``use_partial_cell`` enables partial bottom cells (not recommended "
            "for most setups)."
        ),
        "geometry": (
            "Domain geometry: ``cartesian`` (Cartesian vs spherical), "
            "``fplane`` (constant Coriolis), ``cyclic_length`` (zonal domain extent "
            "in degrees; 360 = global), ``rotated_grid`` and Euler angles "
            "(``alphaEuler``, ``betaEuler``, ``gammaEuler``) for rotated grids."
        ),
        "calendar": (
            "Calendar options: ``include_fleapyear`` (.true. for Gregorian, "
            ".false. for 365-day year). Controls whether the model advances through "
            "leap days."
        ),
        "run_config": (
            "Model component switches: ``use_ice`` (sea ice), ``use_cavity`` "
            "(ice-shelf cavities), ``use_floatice`` (icebergs), ``use_sw_pene`` "
            "(shortwave penetration), ``use_transit`` (transient tracers), "
            "``toy_ocean`` + ``which_toy`` for idealised configurations "
            "('neverworld2', 'soufflet', 'dbgyre')."
        ),
        "machine": (
            "Parallel decomposition: ``n_levels`` (hierarchy levels for domain "
            "decomposition) and ``n_part`` (number of partitions per level; "
            "total MPI ranks = product of n_part). Must match the METIS "
            "partition files in MeshPath."
        ),
        "icebergs": (
            "Iceberg module: ``use_icebergs``, ``ib_num`` (number of iceberg classes), "
            "``steps_per_ib_step`` (ocean steps per iceberg step), "
            "``ib_async_mode`` (0 = synchronous). "
            "Requires a cavity mesh with ``use_cavity=.true.``."
        ),
    },
    "namelist.oce": {
        "oce_dyn": (
            "Ocean dynamics and parameterisations: ``C_d`` (bottom drag), "
            "``A_ver`` (background vertical viscosity), ``mix_scheme`` "
            "('KPP', 'PP', 'TKE', 'TOY'), GM eddy parameterisation "
            "(``Fer_GM``, ``K_GM_max``, ``K_GM_min`` and scaling options), "
            "Redi isopycnal diffusion (``Redi``, ``Redi_Kmax``), "
            "``state_equation`` (0 = linear EOS, 1 = nonlinear), "
            "``use_global_tides``."
        ),
    },
    "namelist.tra": {
        "tracer_phys": (
            "Tracer physics: ``K_hor`` (horizontal tracer diffusivity, m²/s), "
            "``surf_relax_S`` and ``surf_relax_T`` (surface salinity/temperature "
            "restoring timescales, s⁻¹; set to 0 to disable), "
            "``balance_salt_water`` (salt conservation constraint), "
            "``use_momix`` (momentum mixing coupling)."
        ),
    },
    "namelist.dyn": {
        "dynamics_general": (
            "Dynamics solver options: ``use_wsplit`` (barotropic/baroclinic split "
            "for the vertical velocity solver)."
        ),
    },
    "namelist.ice": {
        "ice_dyn": (
            "Sea-ice dynamics: ``whichEVP`` selects the rheology solver "
            "(0 = disabled, 1 = classic EVP, 2 = modified mEVP). "
            "For mEVP (whichEVP=2): ``alpha`` and ``beta`` are damping parameters "
            "(typical: 500 at 1° resolution). "
            "For classic EVP (whichEVP=1): ``evp_rheol_steps`` sets subcycling count."
        ),
        "ice_thermo": (
            "Sea-ice thermodynamics: ice and snow albedo, melt pond parameters, "
            "heat flux formulation, and brine rejection options."
        ),
    },
    "namelist.forcing": {
        "nam_sbc": (
            "Surface boundary condition (forcing) configuration: "
            "``wind_data_source`` ('CORE2', 'JRA55', 'ERA5', 'NCEP'), "
            "directory paths for each forcing variable, "
            "``ncar_bulk_formulae`` (.true. to use NCAR bulk formula for turbulent fluxes). "
            "Interpolation weight files must be precomputed before the first run."
        ),
    },
    "namelist.io": {
        "nml_list": (
            "Output field list: ``io_list`` block specifies each variable to write, "
            "its output frequency (``freq``), unit ('d' = days, 'h' = hours), "
            "and precision (``prec``, 4 or 8 bytes). "
            "Only explicitly listed variables are written — unlisted fields produce "
            "no output without any warning."
        ),
        "diag_list": (
            "Scalar diagnostics: ``ldiag_energy`` (.true. to write global energy "
            "diagnostics to log). Other diagnostic flags controlling domain-mean "
            "output."
        ),
    },
    "namelist.cvmix": {
        "cvmix": (
            "CVMix vertical mixing library: scheme selection (KPP, TKE, PP) and "
            "coefficient tuning. Used when mix_scheme='KPP' or 'TKE' is set "
            "in namelist.oce."
        ),
    },
    "namelist.icepack": {
        "icepack": (
            "Icepack column physics library: thermodynamics scheme, melt pond "
            "model (CESM ponds), snow redistribution, and brine dynamics. "
            "Requires use_ice=.true. and icepack compilation option."
        ),
    },
    "namelist.transit": {
        "transit": (
            "Transient tracer module (CFCs, SF6): tracer names, forcing files, "
            "and output options. Requires use_transit=.true. in namelist.config."
        ),
    },
}


def get_namelist_structure(db_path: Path | None = None) -> dict[str, dict[str, str]]:
    """Return the FESOM2 namelist file → group → description map.

    The map covers all groups in ``_EXPLICIT``. If ``db_path`` is provided
    and the DuckDB index is available, groups from ``namelist_refs`` that are
    not already listed are added with generic descriptions.

    Parameters
    ----------
    db_path : Path or None
        Path to the FESOM2 DuckDB index. If None, uses the default path.
        If the index is absent, the explicit-only map is returned silently.

    Returns
    -------
    dict[str, dict[str, str]]
        Outer keys are namelist file names (e.g. ``'namelist.config'``).
        Inner keys are group names (e.g. ``'timestep'``).
        Values are description strings.
        Sorted alphabetically by file name.
    """
    result: dict[str, dict[str, str]] = {
        file: dict(groups) for file, groups in _EXPLICIT.items()
    }

    explicit_groups = {g for gs in _EXPLICIT.values() for g in gs}

    try:
        if db_path is None:
            from src.fesom2.indexer.schema import DB_PATH
            db_path = DB_PATH
        import duckdb
        con = duckdb.connect(str(db_path), read_only=True)
        rows = con.execute(
            "SELECT DISTINCT namelist_group, config_file FROM namelist_descriptions "
            "ORDER BY namelist_group"
        ).fetchall()
        con.close()
        for group, config_file in rows:
            if group.lower() in explicit_groups:
                continue
            # config_file looks like "namelist.config" or "namelist.oce"
            file_key = config_file if config_file else "namelist.config"
            result.setdefault(file_key, {})[group] = (
                f"Namelist group {group!r} in {config_file}."
            )
    except Exception:
        pass

    return dict(sorted(result.items()))
