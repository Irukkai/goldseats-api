"""Generate synthetic theatre seat-map dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import (
    BOOKING_DISTRIBUTION,
    GenerationConfigSnapshot,
    SCENARIO_DISTRIBUTION,
    THEATRE_DISTRIBUTION,
    snapshot_to_dict,
    validate_distributions,
)
from generator.recommender import recommend_seats
from generator.renderer import render_seat_map
from generator.seats import apply_booking_pattern
from generator.theatre import generate_layout


def _sample_category(rng: np.random.Generator, distribution: dict[str, float]) -> str:
    keys = list(distribution.keys())
    probs = np.array([distribution[k] for k in keys], dtype=float)
    return str(rng.choice(np.array(keys), p=probs))


def _validate_record(label: dict) -> None:
    if label["booked_seats"] + label["available_seats"] != label["total_seats"]:
        raise ValueError(f"Inconsistent seat counts for {label['image_id']}")
    if not (0.0 <= label["occupancy_rate"] <= 1.0):
        raise ValueError(f"Invalid occupancy rate for {label['image_id']}")
    if not label["recommended_seats"]:
        raise ValueError(f"No recommendation for {label['image_id']}")
    for sid in label["recommended_seats"]:
        seat = label["all_seat_scores"].get(sid)
        if seat is None:
            raise ValueError(f"Recommended seat missing score entry: {sid}")
        if seat["status"] != "available":
            raise ValueError(f"Recommended seat is not available: {sid}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GoldSeats synthetic dataset generator")
    parser.add_argument("--count", type=int, default=10000, help="Number of images to generate")
    parser.add_argument("--output", type=str, default="./output", help="Output directory")
    parser.add_argument("--preview", action="store_true", help="Generate only 10 images")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_distributions()

    count = 10 if args.preview else args.count
    output_dir = Path(args.output)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    rows = []
    occupancy_values = []
    scenario_counts = Counter()
    theatre_counts = Counter()
    booking_counts = Counter()

    for idx in tqdm(range(count), desc="Generating seat maps", unit="img"):
        image_id = f"theatre_{idx + 1:06d}"
        theatre_type = _sample_category(rng, THEATRE_DISTRIBUTION)
        booking_pattern = _sample_category(rng, BOOKING_DISTRIBUTION)
        scenario = _sample_category(rng, SCENARIO_DISTRIBUTION)

        layout = generate_layout(theatre_type, rng)
        booking = apply_booking_pattern(layout, booking_pattern, rng)
        rec = recommend_seats(layout, booking["seat_state"], scenario, rng)

        image_rel = Path("images") / f"{image_id}.png"
        label_rel = Path("labels") / f"{image_id}.json"
        image_abs = output_dir / image_rel
        label_abs = output_dir / label_rel

        render_seat_map(
            layout=layout,
            seat_state=booking["seat_state"],
            recommended_seats=rec["recommended_seats"],
            theatre_type=theatre_type,
            scenario=scenario,
            occupancy_rate=booking["occupancy_rate"],
            output_path=str(image_abs),
        )

        label = {
            "image_id": image_id,
            "theatre_type": theatre_type,
            "scenario": scenario,
            "group_size": rec["group_size"],
            "booking_pattern": booking_pattern,
            "total_seats": booking["total_seats"],
            "available_seats": booking["available_seats"],
            "booked_seats": booking["booked_seats"],
            "occupancy_rate": booking["occupancy_rate"],
            "recommended_seats": rec["recommended_seats"],
            "recommended_score": rec["recommended_score"],
            "all_seat_scores": rec["all_seat_scores"],
            "screen_position": layout["screen_position"],
            "image_path": str(image_rel).replace("\\", "/"),
        }
        _validate_record(label)

        with label_abs.open("w", encoding="utf-8") as f:
            json.dump(label, f, indent=2)

        rows.append(
            {
                "image_id": image_id,
                "image_path": str(image_rel).replace("\\", "/"),
                "label_path": str(label_rel).replace("\\", "/"),
                "theatre_type": theatre_type,
                "scenario": scenario,
                "group_size": rec["group_size"],
                "booking_pattern": booking_pattern,
                "occupancy_rate": booking["occupancy_rate"],
                "total_seats": booking["total_seats"],
                "available_seats": booking["available_seats"],
                "recommended_seats": ",".join(rec["recommended_seats"]),
                "recommended_score": rec["recommended_score"],
            }
        )

        occupancy_values.append(booking["occupancy_rate"])
        scenario_counts[scenario] += 1
        theatre_counts[theatre_type] += 1
        booking_counts[booking_pattern] += 1

    csv_path = output_dir / "dataset.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    config_snapshot = GenerationConfigSnapshot(
        count=count,
        output_dir=str(output_dir),
        preview=bool(args.preview),
        seed=args.seed,
    )
    with (output_dir / "config_used.json").open("w", encoding="utf-8") as f:
        json.dump(snapshot_to_dict(config_snapshot), f, indent=2)

    avg_occupancy = (100.0 * float(np.mean(occupancy_values))) if occupancy_values else 0.0
    print(f"Generated {count:,} images")
    print(f"Average occupancy: {avg_occupancy:.1f}%")
    for key in ("solo", "pair", "small_group", "large_group", "family"):
        print(f"{key.replace('_', ' ').title()} scenarios: {scenario_counts.get(key, 0):,}")
    print("Theatre mix:", dict(theatre_counts))
    print("Booking mix:", dict(booking_counts))
    print(f"Dataset CSV: {csv_path}")


if __name__ == "__main__":
    main()
