#!/usr/bin/env python3
"""Plot temperature cross-sections from a completed rotating_convection run.

Reads the final time step from MNC output (mnc_out_0001/ and mnc_out_0002/,
split in X by the 2-process MPI decomposition) and produces two panels:

  Left:  meridional cross-section T(y, z) at x ≈ 0 (tank centre)
  Right: azimuthal mean T(r, z) where r is radius from tank centre

Output: T_section.png in the same directory as this script.

Usage:
    python experiments/rotating_convection/plot.py
or from the repo root:
    pixi run python experiments/rotating_convection/plot.py
"""
import pathlib
import glob
import numpy as np
import netCDF4
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

EXPERIMENT_DIR = pathlib.Path(__file__).resolve().parent
RUN_DIR = EXPERIMENT_DIR / "run"
OUTPUT_PNG = EXPERIMENT_DIR / "T_section.png"

NX, NY, NZ = 60, 60, 40
DZ = 0.003   # m per layer
R_TANK = 0.5  # m


def load_final_temperature():
    """Read the last time step from both MNC tiles, assemble full (NZ, NY, NX) field."""
    tiles = []
    xs = []
    for tile in sorted(RUN_DIR.glob("mnc_out_*/T.*.nc")):
        ds = netCDF4.Dataset(tile)
        T = ds.variables["THETA"][:]   # (time, NZ, NY, NX_tile)
        x = ds.variables["X"][:]       # [0, 0.5) or [0.5, 1)
        ds.close()
        tiles.append(T[-1])            # last time step, shape (NZ, NY, NX_tile)
        xs.append(x)

    T_full = np.concatenate(tiles, axis=-1)   # (NZ, NY, NX)
    x_full = np.concatenate(xs) - 0.5        # centre on tank: [-0.5, 0.5)
    return T_full, x_full


def main():
    T, x = load_final_temperature()

    # Grid coordinates centred on tank
    dy = 1.0 / NY
    y = np.arange(NY) * dy + dy / 2 - 0.5   # [-0.5, 0.5)
    z = -(np.arange(NZ) + 0.5) * DZ          # depth [m], negative downward

    # Left panel: meridional section at x ≈ 0
    ix_centre = np.argmin(np.abs(x))
    T_section = T[:, :, ix_centre]           # (NZ, NY)

    # Right panel: azimuthal mean on radius bins
    xx, yy = np.meshgrid(x, y)              # (NY, NX)
    r = np.sqrt(xx**2 + yy**2)
    r_bins = np.linspace(0, R_TANK, 31)
    r_mid = 0.5 * (r_bins[:-1] + r_bins[1:])
    T_radial = np.full((NZ, len(r_mid)), np.nan)
    for k in range(NZ):
        for b in range(len(r_mid)):
            mask = (r >= r_bins[b]) & (r < r_bins[b + 1])
            if mask.any():
                T_radial[k, b] = T[k][mask].mean()

    # Colour scale: symmetric around a midpoint that shows the gradient clearly
    vmin, vmax = np.nanmin(T), np.nanmax(T)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)

    # --- Left: y-z section ---
    ax = axes[0]
    cf = ax.pcolormesh(y * 100, z * 100, T_section,
                       cmap="RdBu_r", vmin=vmin, vmax=vmax)
    ax.set_xlabel("y  [cm]")
    ax.set_ylabel("z  [cm]")
    ax.set_title("Temperature — meridional section at x ≈ 0")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    # --- Right: radial mean ---
    ax = axes[1]
    cf = ax.pcolormesh(r_mid * 100, z * 100, T_radial,
                       cmap="RdBu_r", vmin=vmin, vmax=vmax)
    ax.set_xlabel("r  [cm]")
    ax.set_ylabel("z  [cm]")
    ax.set_title("Temperature — azimuthal mean")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"Saved {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
