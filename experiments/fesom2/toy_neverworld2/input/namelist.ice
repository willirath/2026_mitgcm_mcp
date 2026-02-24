! Sea ice — not active for this experiment (use_ice = .false. in namelist.config).
! FESOM2 opens this file unconditionally at startup; contents are not used.

&ice_dyn
whichEVP        = 0
Pstar           = 30000.0
ellipse         = 2.0
c_pressure      = 20.0
delta_min       = 1.0e-11
evp_rheol_steps = 120
alpha_evp       = 250
beta_evp        = 250
c_aevp          = 0.15
Cd_oce_ice      = 0.0055
ice_gamma_fct   = 0.5
ice_diff        = 0.0
theta_io        = 0.0
ice_ave_steps   = 1
/

&ice_therm
Sice           = 4.0
iclasses       = 7
new_iclasses   = .false.
h_cutoff       = 3.0
h0             = 0.5
h0_s           = 0.5
hmin           = 0.01
armin          = 0.01
emiss_ice      = 0.97
emiss_wat      = 0.97
albsn          = 0.81
albsnm         = 0.77
albi           = 0.7
albim          = 0.68
albw           = 0.1
open_water_albedo = 0
con            = 2.1656
consn          = 0.31
snowdist       = .true.
c_melt         = 0.5
/
