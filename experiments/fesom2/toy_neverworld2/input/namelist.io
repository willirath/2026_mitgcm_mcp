&diag_list
ldiag_solver      = .false.
lcurt_stress_surf = .false.
ldiag_curl_vel3   = .false.
ldiag_Ri          = .false.
ldiag_turbflux    = .false.
ldiag_salt3D      = .false.
ldiag_dMOC        = .false.
ldiag_DVD         = .false.
ldiag_forc        = .false.
ldiag_extflds     = .false.
ldiag_destine     = .false.
ldiag_trflx       = .false.
ldiag_uvw_sqr     = .false.
ldiag_trgrd_xyz   = .false.
ldiag_cmor        = .false.
/

&nml_general
io_listsize       = 120
vec_autorotate    = .false.
compression_level = 1
/

&nml_list
io_list =
  'sst       ', 1, 'd', 4,   ! sea surface temperature [°C]
  'ssh       ', 1, 'd', 4,   ! sea surface height [m]
  'MLD1      ', 1, 'd', 4,   ! mixed layer depth [m]
  'tx_sur    ', 1, 'd', 4,   ! zonal wind stress [N/m²]
  'ty_sur    ', 1, 'd', 4,   ! meridional wind stress [N/m²]
  'temp      ', 1, 'd', 4,   ! 3D temperature [°C]
  'salt      ', 1, 'd', 8,   ! 3D salinity [psu]
  'u         ', 1, 'd', 4,   ! 3D zonal velocity [m/s]
  'v         ', 1, 'd', 4,   ! 3D meridional velocity [m/s]
  'w         ', 1, 'd', 4,   ! 3D vertical velocity [m/s]
/
