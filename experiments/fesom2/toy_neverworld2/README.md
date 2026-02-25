# toy_neverworld2

Five-day integration of the FESOM2 neverworld2 toy configuration on a
laptop using the self-contained Docker image.

Neverworld2 is an idealised Southern-Ocean-like channel on a spherical
domain (60° zonal extent, ~8 500 nodes). It uses a linear equation of
state, analytical wind stress, and no atmospheric forcing files.

---

## Physical setup

| Parameter | Value |
|---|---|
| Domain | 60° × ~70° channel, spherical |
| Mesh nodes | 8 578 |
| dt | 1920 s (45 steps/day) |
| Run length | 5 days |
| MPI ranks | 2 |
| Vertical coord | linfs |
| EOS | linear (temperature only) |
| Mixing | TOY scheme |
| Ice | off |

---

## Files

```
toy_neverworld2/
├── mesh/
│   ├── nod2d.out            node coordinates
│   ├── elem2d.out           triangular connectivity
│   ├── aux3d.out            level depths + bathymetry
│   ├── windstress.out       wind stress profile (read from MeshPath)
│   ├── edges.out            }
│   ├── edge_tri.out         } derived geometry (pre-computed)
│   ├── edgenum.out          }
│   ├── elvls.out            }
│   ├── nlvls.out            }
│   ├── dist_2/              METIS partition for 2 ranks
│   ├── dist_8/              METIS partition for 8 ranks
│   └── create_neverworld2_mesh.py
├── input/
│   ├── namelist.config      run length, time step, paths (patched at runtime)
│   ├── namelist.oce         ocean dynamics, linear EOS, TOY mixing
│   ├── namelist.tra         tracers (analytically initialised)
│   ├── namelist.dyn         momentum viscosity
│   ├── namelist.cvmix       CVMix (not active)
│   ├── namelist.ice         sea ice (not active)
│   ├── namelist.io          daily output: SST, SSH, T, S, u, v, w
│   └── namelist.forcing     bulk forcing (not active)
├── output/                  gitignored — created at runtime
├── run.sh                   docker run command
├── plot.py                  SST + SSH visualisation
├── neverworld2.png          reference figure
└── README.md
```

The Docker entrypoint patches `MeshPath → /mesh/`, `ResultPath → /output/`,
and `ClimateDataPath → /dev/null/` at container start. All other parameters
are set in `input/` and committed as the experiment definition.

---

## How to run

```bash
# Build the image once
pixi run build-fesom2-image

# Run the experiment
pixi run run-fesom2-toy-neverworld2

# Visualise
pixi run plot-fesom2-toy-neverworld2
```

Wall time on a MacBook Pro (M-series, 2 MPI ranks via Rosetta): ~20 s.
