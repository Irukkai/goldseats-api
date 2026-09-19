"""Visualize a random generated sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize generated GoldSeats sample")
    parser.add_argument("--output", type=str, default="./output", help="Dataset output directory")
    parser.add_argument("--seed", type=int, default=None, help="Seed for random sample selection")
    parser.add_argument("--image-id", type=str, default=None, help="Optional image id to preview")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output)
    dataset_csv = output_dir / "dataset.csv"
    if not dataset_csv.exists():
        raise FileNotFoundError(f"Missing dataset CSV at {dataset_csv}")

    df = pd.read_csv(dataset_csv)
    if df.empty:
        raise ValueError("dataset.csv is empty")

    if args.image_id:
        sample = df[df["image_id"] == args.image_id]
        if sample.empty:
            raise ValueError(f"Image id not found: {args.image_id}")
        row = sample.iloc[0]
    else:
        rng = np.random.default_rng(args.seed)
        row = df.iloc[int(rng.integers(0, len(df)))]

    image_path = output_dir / row["image_path"]
    label_path = output_dir / row["label_path"]
    if not image_path.exists() or not label_path.exists():
        raise FileNotFoundError(f"Missing image or label for {row['image_id']}")

    with label_path.open("r", encoding="utf-8") as f:
        label = json.load(f)

    print(f"Image ID: {label['image_id']}")
    print(f"Theatre type: {label['theatre_type']}")
    print(f"Scenario: {label['scenario']}")
    print(f"Group size: {label['group_size']}")
    print(f"Booking pattern: {label['booking_pattern']}")
    print(f"Occupancy: {label['occupancy_rate'] * 100:.1f}%")
    print(f"Recommended seats: {', '.join(label['recommended_seats'])}")
    print(f"Recommended score: {label['recommended_score']}")

    image = plt.imread(image_path)
    plt.figure(figsize=(10, 7))
    plt.imshow(image)
    plt.axis("off")
    plt.title(
        f"{label['image_id']} | {label['theatre_type']} | {label['scenario']} | "
        f"Rec: {', '.join(label['recommended_seats'])}"
    )
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
