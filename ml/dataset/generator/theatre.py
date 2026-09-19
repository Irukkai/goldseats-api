"""Theatre layout generation."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from config import (
    IMAGE_WIDTH,
    SCREEN_Y,
    SEAT_GAP_X,
    SEAT_GAP_Y,
    SEAT_HEIGHT,
    SEAT_WIDTH,
    THEATRE_LAYOUT_RANGES,
)


def _row_label(index: int) -> str:
    label = ""
    value = index
    while True:
        value, rem = divmod(value, 26)
        label = chr(65 + rem) + label
        if value == 0:
            break
        value -= 1
    return label


def _build_aisles(mode: str, seats_per_row: int) -> List[int]:
    if mode == "none":
        return []
    if mode == "center":
        return [seats_per_row // 2]
    # two_side
    return [seats_per_row // 3, (2 * seats_per_row) // 3]


def _x_with_aisles(col: int, aisles: List[int], pitch_x: float) -> float:
    extra = 0.0
    for aisle_after_col in aisles:
        if col >= aisle_after_col:
            extra += pitch_x * 1.8
    return col * pitch_x + extra


def generate_layout(theatre_type: str, rng: np.random.Generator) -> Dict:
    spec = THEATRE_LAYOUT_RANGES[theatre_type]
    row_min, row_max = spec["rows"]
    seat_min, seat_max = spec["seats_per_row"]
    rows = int(rng.integers(row_min, row_max + 1))
    seats_per_row = int(rng.integers(seat_min, seat_max + 1))
    aisles = _build_aisles(str(spec["aisle_mode"]), seats_per_row)

    pitch_x = (SEAT_WIDTH + SEAT_GAP_X) * float(spec["seat_spacing_mult"])
    pitch_y = (SEAT_HEIGHT + SEAT_GAP_Y) * float(spec["row_spacing_mult"])

    total_width = _x_with_aisles(seats_per_row - 1, aisles, pitch_x) + SEAT_WIDTH
    offset_x = (IMAGE_WIDTH - total_width) / 2.0
    first_row_y = SCREEN_Y + 62

    curve_strength = float(spec["curve_strength"])
    center_col = (seats_per_row - 1) / 2.0
    max_curve_shift = 12.0 + 0.6 * seats_per_row

    seats = []
    for row_idx in range(rows):
        row_label = _row_label(row_idx)
        stadium = 1.8 * row_idx if int(spec["stadium"]) else 0.0
        y = first_row_y + row_idx * pitch_y + stadium
        row_curve = curve_strength * ((row_idx / max(rows - 1, 1)) - 0.5)

        for col_idx in range(seats_per_row):
            rel = (col_idx - center_col) / max(center_col, 1.0)
            curve_shift = (rel * rel) * np.sign(rel) * max_curve_shift * row_curve
            x = offset_x + _x_with_aisles(col_idx, aisles, pitch_x) + curve_shift
            seat_id = f"{row_label}{col_idx + 1}"
            seats.append(
                {
                    "seat_id": seat_id,
                    "row_label": row_label,
                    "row_index": row_idx,
                    "number": col_idx + 1,
                    "col_index": col_idx,
                    "x": float(x),
                    "y": float(y),
                    "is_premium_center": False,
                }
            )

    # Mark IMAX premium center section.
    if theatre_type == "imax":
        left = int(round(seats_per_row * 0.32))
        right = int(round(seats_per_row * 0.68))
        top = int(round(rows * 0.33))
        bottom = int(round(rows * 0.75))
        for seat in seats:
            if top <= seat["row_index"] <= bottom and left <= seat["col_index"] <= right:
                seat["is_premium_center"] = True

    layout = {
        "theatre_type": theatre_type,
        "rows": rows,
        "seats_per_row": seats_per_row,
        "aisles": aisles,
        "seat_pitch_x": pitch_x,
        "seat_pitch_y": pitch_y,
        "screen_position": "top",
        "screen_width_factor": float(spec["screen_width_factor"]),
        "default_seat_type": str(spec["default_seat_type"]),
        "seats": seats,
    }
    return layout
