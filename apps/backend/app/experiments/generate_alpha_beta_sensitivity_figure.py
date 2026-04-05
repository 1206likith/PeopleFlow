"""Generate alpha/beta routing-weight sensitivity heatmap for manuscript use."""

from __future__ import annotations

from pathlib import Path
import csv

import matplotlib.pyplot as plt  # type: ignore
import numpy as np  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
PAPER_DIR = ROOT_DIR / "Research_Paper_IEEE"
CSV_PATH = PAPER_DIR / "alpha_beta_sensitivity.csv"
OUT_PATH = PAPER_DIR / "fig_alpha_beta_sensitivity.png"


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {CSV_PATH}")

    rows = []
    with CSV_PATH.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for r in reader:
            rows.append(
                {
                    "alpha": float(r["alpha"]),
                    "beta": float(r["beta"]),
                    "evac_time": float(r["evac_time_mean_s"]),
                }
            )

    alphas = sorted({r["alpha"] for r in rows})
    betas = sorted({r["beta"] for r in rows})

    mat = np.zeros((len(alphas), len(betas)), dtype=float)
    for r in rows:
        i = alphas.index(r["alpha"])
        j = betas.index(r["beta"])
        mat[i, j] = r["evac_time"]

    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    im = ax.imshow(mat, cmap="viridis", aspect="auto")

    ax.set_xticks(np.arange(len(betas)), labels=[f"{b:.1f}" for b in betas])
    ax.set_yticks(np.arange(len(alphas)), labels=[f"{a:.1f}" for a in alphas])
    ax.set_xlabel(r"Congestion weight $\beta$")
    ax.set_ylabel(r"Distance weight $\alpha$")
    ax.set_title("Routing Cost Sensitivity: Mean Evacuation Time (s)")

    for i in range(len(alphas)):
        for j in range(len(betas)):
            value = mat[i, j]
            txt_color = "white" if value > np.median(mat) else "black"
            ax.text(j, i, f"{value:.1f}", ha="center", va="center", color=txt_color, fontsize=8)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Mean evacuation time (s)")

    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote: {OUT_PATH}")


if __name__ == "__main__":
    main()
