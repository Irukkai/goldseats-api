"""Seat type assignment and booking pattern simulation."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np

from config import BOOKING_OCCUPANCY_RANGES


def _seat_groups_by_row(seats: List[Dict]) -> Dict[int, List[Dict]]:
    rows = defaultdict(list)
    for seat in seats:
        rows[seat["row_index"]].append(seat)
    for row in rows.values():
        row.sort(key=lambda s: s["col_index"])
    return rows


def _assign_base_types(layout: Dict, rng: np.random.Generator) -> Dict[str, str]:
    seats = layout["seats"]
    rows = _seat_groups_by_row(seats)
    types = {seat["seat_id"]: layout["default_seat_type"] for seat in seats}

    wheelchair_rows = sorted(rows.keys())
    wheelchair_rows = [r for r in wheelchair_rows if (r % 3 == 0 or r == wheelchair_rows[-1])]

    for row_idx in wheelchair_rows:
        row = rows[row_idx]
        if len(row) < 4:
            continue
        left_wc = row[0]["seat_id"]
        left_comp = row[1]["seat_id"]
        right_wc = row[-1]["seat_id"]
        right_comp = row[-2]["seat_id"]
        types[left_wc] = "wheelchair"
        types[left_comp] = "companion"
        types[right_wc] = "wheelchair"
        types[right_comp] = "companion"

    # Add a few recliners in non-recliner theatres to improve variety.
    if layout["theatre_type"] != "recliners":
        all_regular = [sid for sid, stype in types.items() if stype == "regular"]
        if all_regular:
            sample_size = max(1, int(0.04 * len(all_regular)))
            chosen = rng.choice(all_regular, size=min(sample_size, len(all_regular)), replace=False)
            for sid in np.atleast_1d(chosen):
                types[str(sid)] = "recliner"
    return types


def _booking_preference(seat: Dict, layout: Dict) -> float:
    rows = layout["rows"]
    cols = layout["seats_per_row"]
    center_col = (cols - 1) / 2.0
    row_ratio = seat["row_index"] / max(rows - 1, 1)
    col_ratio = abs(seat["col_index"] - center_col) / max(center_col, 1)

    center_pref = 1.0 - col_ratio
    # Back rows book first, then middle, front last.
    back_pref = row_ratio
    mid_bonus = 1.0 - abs(row_ratio - 0.58) / 0.58
    front_penalty = 0.25 if row_ratio < 0.18 else 0.0

    aisle_pref = 0.0
    for aisle in layout["aisles"]:
        if abs(seat["col_index"] - aisle) <= 1:
            aisle_pref = max(aisle_pref, 1.0 - 0.45 * abs(seat["col_index"] - aisle))
    return 0.40 * center_pref + 0.30 * back_pref + 0.20 * max(mid_bonus, 0.0) + 0.15 * aisle_pref - front_penalty


def _neighbor_booked_bonus(candidate_ids: List[str], booked: set, seat_index: Dict[str, Dict]) -> float:
    # Encourages natural clusters/islands by preferring adjacent placements once booking starts.
    if not booked:
        return 0.0
    bonus = 0.0
    for sid in candidate_ids:
        seat = seat_index[sid]
        row = seat["row_index"]
        col = seat["col_index"]
        neighbors = [
            (row, col - 1),
            (row, col + 1),
            (row - 1, col),
            (row + 1, col),
        ]
        for nrow, ncol in neighbors:
            nid = f"{seat['row_label']}{ncol + 1}" if nrow == row else None
            if nid and nid in booked:
                bonus += 0.12
    return bonus


def _sample_target_occupancy(pattern: str, rng: np.random.Generator) -> float:
    lo, hi = BOOKING_OCCUPANCY_RANGES[pattern]
    return float(rng.uniform(lo, hi))


def _available_blocks_in_row(row_seats: List[Dict], free_ids: set, block_size: int) -> List[List[str]]:
    blocks = []
    for i in range(0, len(row_seats) - block_size + 1):
        block = row_seats[i : i + block_size]
        ids = [seat["seat_id"] for seat in block]
        cols = [seat["col_index"] for seat in block]
        contiguous = all(cols[j + 1] == cols[j] + 1 for j in range(len(cols) - 1))
        if contiguous and all(sid in free_ids for sid in ids):
            blocks.append(ids)
    return blocks


def apply_booking_pattern(layout: Dict, pattern: str, rng: np.random.Generator) -> Dict:
    seats = layout["seats"]
    seat_types = _assign_base_types(layout, rng)
    rows = _seat_groups_by_row(seats)
    seat_index = {seat["seat_id"]: seat for seat in seats}

    total_seats = len(seats)
    target_occ = _sample_target_occupancy(pattern, rng)
    target_booked = int(round(total_seats * target_occ))

    free_ids = {seat["seat_id"] for seat in seats}
    booked_ids = set()
    base_pref = {seat["seat_id"]: _booking_preference(seat, layout) for seat in seats}

    # Book groups first for realism (2-4) plus singles.
    group_size_choices = np.array([1, 2, 3, 4])
    group_probs = np.array([0.26, 0.32, 0.24, 0.18])

    while len(booked_ids) < target_booked and free_ids:
        remaining = target_booked - len(booked_ids)
        size = int(rng.choice(group_size_choices, p=group_probs))
        size = min(size, remaining)
        size = max(size, 1)

        candidate_blocks: List[Tuple[List[str], float]] = []
        if size == 1:
            # sample from top weighted free seats
            candidates = list(free_ids)
            scores = np.array([base_pref[sid] for sid in candidates], dtype=float)
            scores -= scores.min()
            scores += 1e-6
            probs = scores / scores.sum()
            chosen = str(rng.choice(np.array(candidates), p=probs))
            candidate_blocks.append(([chosen], 1.0))
        else:
            for row in rows.values():
                blocks = _available_blocks_in_row(row, free_ids, size)
                for block in blocks:
                    pref = float(np.mean([base_pref[sid] for sid in block]))
                    pref += _neighbor_booked_bonus(block, booked_ids, seat_index)
                    candidate_blocks.append((block, pref))

        if not candidate_blocks:
            break

        prefs = np.array([max(0.001, cand[1]) for cand in candidate_blocks], dtype=float)
        prefs = prefs / prefs.sum()
        selected_block = candidate_blocks[int(rng.choice(np.arange(len(candidate_blocks)), p=prefs))][0]
        for sid in selected_block:
            if sid in free_ids:
                free_ids.remove(sid)
                booked_ids.add(sid)

    # Fill exact target if needed.
    if len(booked_ids) < target_booked:
        remaining_ids = list(free_ids)
        if remaining_ids:
            scores = np.array([base_pref[sid] for sid in remaining_ids], dtype=float)
            scores -= scores.min()
            scores += 1e-6
            probs = scores / scores.sum()
            n = min(target_booked - len(booked_ids), len(remaining_ids))
            extras = rng.choice(np.array(remaining_ids), size=n, replace=False, p=probs)
            for sid in np.atleast_1d(extras):
                sid = str(sid)
                free_ids.discard(sid)
                booked_ids.add(sid)

    seat_state = {}
    for seat in seats:
        sid = seat["seat_id"]
        seat_state[sid] = {
            "status": "booked" if sid in booked_ids else "available",
            "seat_type": seat_types[sid],
        }

    return {
        "seat_state": seat_state,
        "total_seats": total_seats,
        "booked_seats": len(booked_ids),
        "available_seats": total_seats - len(booked_ids),
        "occupancy_rate": round(len(booked_ids) / max(total_seats, 1), 4),
    }
