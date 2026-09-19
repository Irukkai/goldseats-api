"""Configuration constants for GoldSeats synthetic dataset generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Tuple


IMAGE_WIDTH = 800
IMAGE_HEIGHT = 600
BACKGROUND_COLOR = "#1a1a2e"

SCREEN_Y = 50
SEAT_WIDTH = 20
SEAT_HEIGHT = 18
SEAT_GAP_X = 4
SEAT_GAP_Y = 6

THEATRE_DISTRIBUTION = {
    "standard": 0.40,
    "large": 0.20,
    "small": 0.15,
    "imax": 0.15,
    "recliners": 0.10,
}

BOOKING_DISTRIBUTION = {
    "empty": 0.10,
    "light": 0.20,
    "medium": 0.30,
    "busy": 0.25,
    "almost_full": 0.15,
}

# Included for flexibility; the default sampling distribution excludes it.
BOOKING_OCCUPANCY_RANGES = {
    "empty": (0.05, 0.15),
    "light": (0.15, 0.35),
    "medium": (0.35, 0.60),
    "busy": (0.60, 0.80),
    "almost_full": (0.80, 0.95),
    "sold_out_edges": (0.95, 0.99),
}

SCENARIO_DISTRIBUTION = {
    "solo": 0.30,
    "pair": 0.30,
    "small_group": 0.20,
    "large_group": 0.10,
    "family": 0.10,
}

GROUP_SIZE_BY_SCENARIO = {
    "solo": (1, 1),
    "pair": (2, 2),
    "small_group": (3, 4),
    "large_group": (5, 6),
    "family": (3, 5),
}

THEATRE_LAYOUT_RANGES: Dict[str, Dict[str, Tuple[int, int] | float | int | str]] = {
    "standard": {
        "rows": (15, 20),
        "seats_per_row": (16, 24),
        "aisle_mode": "center",
        "screen_width_factor": 0.58,
        "curve_strength": 0.20,
        "row_spacing_mult": 1.0,
        "seat_spacing_mult": 1.0,
        "stadium": 0,
        "default_seat_type": "regular",
    },
    "large": {
        "rows": (20, 25),
        "seats_per_row": (24, 32),
        "aisle_mode": "two_side",
        "screen_width_factor": 0.74,
        "curve_strength": 0.10,
        "row_spacing_mult": 1.08,
        "seat_spacing_mult": 1.0,
        "stadium": 1,
        "default_seat_type": "regular",
    },
    "small": {
        "rows": (8, 12),
        "seats_per_row": (10, 16),
        "aisle_mode": "none",
        "screen_width_factor": 0.52,
        "curve_strength": 0.08,
        "row_spacing_mult": 1.0,
        "seat_spacing_mult": 1.0,
        "stadium": 0,
        "default_seat_type": "regular",
    },
    "imax": {
        "rows": (20, 28),
        "seats_per_row": (20, 28),
        "aisle_mode": "center",
        "screen_width_factor": 0.82,
        "curve_strength": 0.12,
        "row_spacing_mult": 1.06,
        "seat_spacing_mult": 1.0,
        "stadium": 1,
        "default_seat_type": "regular",
    },
    "recliners": {
        "rows": (10, 14),
        "seats_per_row": (8, 14),
        "aisle_mode": "none",
        "screen_width_factor": 0.56,
        "curve_strength": 0.03,
        "row_spacing_mult": 1.35,
        "seat_spacing_mult": 1.38,
        "stadium": 0,
        "default_seat_type": "recliner",
    },
}

SCORE_WEIGHTS = {
    "horizontal_center": 0.25,
    "vertical_position": 0.25,
    "view_angle": 0.20,
    "neighbor": 0.15,
    "row_quality": 0.15,
}

SEAT_COLORS = {
    "available_regular": "#4a4a6a",
    "available_recliner": "#2a5a8a",
    "available_wheelchair": "#6a2a8a",
    "available_companion": "#9b7bd3",
    "booked": "#8a2a2a",
    "recommended": "#FFD700",
}


@dataclass(frozen=True)
class GenerationConfigSnapshot:
    count: int
    output_dir: str
    preview: bool
    seed: int | None


def validate_distributions() -> None:
    for dist_name, dist in (
        ("theatre", THEATRE_DISTRIBUTION),
        ("booking", BOOKING_DISTRIBUTION),
        ("scenario", SCENARIO_DISTRIBUTION),
    ):
        total = round(sum(dist.values()), 8)
        if total != 1.0:
            raise ValueError(f"{dist_name} distribution must sum to 1.0, got {total}")


def snapshot_to_dict(snapshot: GenerationConfigSnapshot) -> dict:
    payload = asdict(snapshot)
    payload["theatre_distribution"] = THEATRE_DISTRIBUTION
    payload["booking_distribution"] = BOOKING_DISTRIBUTION
    payload["scenario_distribution"] = SCENARIO_DISTRIBUTION
    payload["booking_ranges"] = BOOKING_OCCUPANCY_RANGES
    payload["score_weights"] = SCORE_WEIGHTS
    return payload
