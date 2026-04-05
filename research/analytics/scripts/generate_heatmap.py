import argparse
import csv
import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


def load_points(csv_path):
    xs, ys = [], []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row.get("x", 0)))
            ys.append(float(row.get("y", 0)))
    return np.array(xs), np.array(ys)


def save_heatmap(xs, ys, out_path, bins=100):
    H, xedges, yedges = np.histogram2d(xs, ys, bins=bins)
    plt.figure(figsize=(6, 5))
    plt.imshow(H.T, origin="lower", cmap="hot")
    plt.colorbar(label="density")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generate heatmap from CSV with x,y columns")
    parser.add_argument("csv", help="Input CSV path with x,y columns")
    parser.add_argument("--out", default=os.path.join("..", "output", "heatmap", "heatmap.png"))
    parser.add_argument("--bins", type=int, default=100)
    args = parser.parse_args()

    xs, ys = load_points(args.csv)
    save_heatmap(xs, ys, args.out, bins=args.bins)
    print(f"Saved heatmap to {args.out}")


if __name__ == "__main__":
    main()
