"""Plot SST and SSH from the toy_neverworld2 FESOM2 experiment.

Usage:
    python experiments/fesom2/toy_neverworld2/plot.py

Reads mesh from mesh/ and output from output/ (both relative to this
script), and writes neverworld2.png next to this script.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import netCDF4 as nc
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_mesh(mesh_dir):
    """Return (lon, lat, triangles) from nod2d.out and elem2d.out."""
    mesh_dir = Path(mesh_dir)
    nod = np.loadtxt(mesh_dir / "nod2d.out", skiprows=1)
    lon, lat = nod[:, 1], nod[:, 2]
    tri = np.loadtxt(mesh_dir / "elem2d.out", dtype=int, skiprows=1) - 1
    return lon, lat, tri


def read_last(nc_path, varname):
    """Read the last time slice of varname from a FESOM2 output file."""
    with nc.Dataset(nc_path) as ds:
        return ds[varname][-1, :]


output_dir = HERE / "output"
mesh_dir   = HERE / "mesh"

sst_file = sorted(output_dir.glob("sst.fesom.*.nc"))[0]
ssh_file = sorted(output_dir.glob("ssh.fesom.*.nc"))[0]

lon, lat, tri = read_mesh(mesh_dir)
triang = mtri.Triangulation(lon, lat, tri)

sst = read_last(sst_file, "sst")
ssh = read_last(ssh_file, "ssh")

fig, (ax_sst, ax_ssh) = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("toy_neverworld2 — last time step", fontsize=13)

for ax, data, title, cmap in [
    (ax_sst, sst, "SST (°C)", "RdYlBu_r"),
    (ax_ssh, ssh, "SSH (m)",  "RdBu_r"),
]:
    vmax = np.percentile(np.abs(data), 99)
    vmin = np.percentile(data, 1) if "SST" in title else -vmax
    tcf = ax.tripcolor(triang, data, cmap=cmap, vmin=vmin, vmax=vmax,
                       shading="gouraud")
    plt.colorbar(tcf, ax=ax, shrink=0.85)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("longitude (°)")
    ax.set_ylabel("latitude (°)")

plt.tight_layout()
out = HERE / "neverworld2.png"
plt.savefig(out, dpi=150)
print(f"Saved {out}")
