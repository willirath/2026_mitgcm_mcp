#!/usr/bin/env python3
"""Plot temperature cross-sections and top views from a completed rotating_convection run.

Reads all time steps from MNC output (mnc_out_0001/ and mnc_out_0002/,
split in X by the 2-process MPI decomposition) and produces a 2×2 figure:

  Row 1 left:  meridional cross-section T(y, z) at x ≈ 0 (final time step)
  Row 1 right: azimuthal mean T(r, z) (final time step)
  Row 2 left:  time-mean, depth-mean T(x, y) — top view
  Row 2 right: T(x, y) at layer k=1 (second from surface) — final snapshot

Output: T_section.png in the same directory as this script.

Usage:
    python experiments/rotating_convection/plot.py
or from the repo root:
    pixi run python experiments/rotating_convection/plot.py
"""
import pathlib
import numpy as np
import netCDF4
import matplotlib.pyplot as plt

EXPERIMENT_DIR = pathlib.Path(__file__).resolve().parent
RUN_DIR = EXPERIMENT_DIR / "run"
OUTPUT_PNG = EXPERIMENT_DIR / "T_section.png"

NX, NY, NZ = 60, 60, 40
DZ = 0.003   # m per layer
R_TANK = 0.5  # m


def load_temperature():
    """Read all time steps from both MNC tiles.

    Returns T_full (time, NZ, NY, NX) and x_full (NX,) centred on tank.
    """
    tiles, xs = [], []
    for tile in sorted(RUN_DIR.glob("mnc_out_*/T.*.nc")):
        ds = netCDF4.Dataset(tile)
        T = ds.variables["THETA"][:]   # (time, NZ, NY, NX_tile)
        x = ds.variables["X"][:]
        ds.close()
        tiles.append(T)
        xs.append(x)

    T_full = np.concatenate(tiles, axis=-1)        # (time, NZ, NY, NX)
    x_full = np.concatenate(xs) - 0.5             # centre: [-0.5, 0.5)
    return T_full, x_full


def land_mask(xx, yy):
    """Boolean mask: True where outside the tank (land)."""
    return np.sqrt(xx**2 + yy**2) > R_TANK


def main():
    T_all, x = load_temperature()

    dy = 1.0 / NY
    y = np.arange(NY) * dy + dy / 2 - 0.5   # [-0.5, 0.5)
    z = -(np.arange(NZ) + 0.5) * DZ          # depth [m], negative downward

    xx, yy = np.meshgrid(x, y)               # (NY, NX)
    r = np.sqrt(xx**2 + yy**2)
    mask_land = land_mask(xx, yy)            # (NY, NX)

    T_final = T_all[-1]                      # (NZ, NY, NX) — last snapshot

    # --- Row 1: cross-sections (final time step) ---
    ix_centre = np.argmin(np.abs(x))
    T_section = T_final[:, :, ix_centre]     # (NZ, NY)

    r_bins = np.linspace(0, R_TANK, 31)
    r_mid = 0.5 * (r_bins[:-1] + r_bins[1:])
    T_radial = np.full((NZ, len(r_mid)), np.nan)
    for k in range(NZ):
        for b in range(len(r_mid)):
            m = (r >= r_bins[b]) & (r < r_bins[b + 1])
            if m.any():
                T_radial[k, b] = T_final[k][m].mean()

    # --- Row 2: top views ---
    # Time-mean then depth-mean; mask land
    T_tmean = T_all.mean(axis=0)             # (NZ, NY, NX)
    T_depthmean = T_tmean.mean(axis=0)       # (NY, NX)
    T_depthmean = np.where(mask_land, np.nan, T_depthmean)

    # Snapshot at layer k=1 (second from surface); mask land
    T_layer1 = T_final[1].copy()             # (NY, NX)
    T_layer1 = np.where(mask_land, np.nan, T_layer1)

    # Shared colour scale across all panels
    vmin = min(np.nanmin(T_section), np.nanmin(T_radial),
               np.nanmin(T_depthmean), np.nanmin(T_layer1))
    vmax = max(np.nanmax(T_section), np.nanmax(T_radial),
               np.nanmax(T_depthmean), np.nanmax(T_layer1))

    fig, axes = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)
    kw = dict(cmap="RdBu_r", vmin=vmin, vmax=vmax)

    # Row 1 left: meridional section
    ax = axes[0, 0]
    cf = ax.pcolormesh(y * 100, z * 100, T_section, **kw)
    ax.set_xlabel("y  [cm]")
    ax.set_ylabel("z  [cm]")
    ax.set_title("Meridional section at x ≈ 0  (final)")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    # Row 1 right: azimuthal mean
    ax = axes[0, 1]
    cf = ax.pcolormesh(r_mid * 100, z * 100, T_radial, **kw)
    ax.set_xlabel("r  [cm]")
    ax.set_ylabel("z  [cm]")
    ax.set_title("Azimuthal mean  (final)")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    # Row 2 left: time-mean depth-mean top view
    ax = axes[1, 0]
    cf = ax.pcolormesh(x * 100, y * 100, T_depthmean, **kw)
    ax.set_aspect("equal")
    ax.set_xlabel("x  [cm]")
    ax.set_ylabel("y  [cm]")
    ax.set_title("Top view — time-mean, depth-mean T")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    # Row 2 right: layer k=1 snapshot
    ax = axes[1, 1]
    cf = ax.pcolormesh(x * 100, y * 100, T_layer1, **kw)
    ax.set_aspect("equal")
    ax.set_xlabel("x  [cm]")
    ax.set_ylabel("y  [cm]")
    ax.set_title(f"Top view — layer k=1 (z ≈ {z[1]*100:.1f} cm), final snapshot")
    fig.colorbar(cf, ax=ax, label="T  [°C]")

    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"Saved {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
