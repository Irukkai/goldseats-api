"""Ground-truth seat recommendation scoring."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np

from config import GROUP_SIZE_BY_SCENARIO, SCORE_WEIGHTS


def _build_row_map(layout: Dict) -> Dict[int, List[Dict]]:
    rows = defaultdict(list)
    for seat in layout["seats"]:
        rows[seat["row_index"]].append(seat)
    for row in rows.values():
        row.sort(key=lambda s: s["col_index"])
    return rows


def _seat_lookup(layout: Dict) -> Dict[str, Dict]:
    return {seat["seat_id"]: seat for seat in layout["seats"]}


def _horizontal_center_score(seat: Dict, layout: Dict) -> float:
    center_col = (layout["seats_per_row"] - 1) / 2.0
    distance = abs(seat["col_index"] - center_col) / max(center_col, 1)
    return max(0.0, 1.0 - distance)


def _vertical_position_score(seat: Dict, layout: Dict) -> float:
    """Peaks at ~50% depth, matching requested 40-60% optimal region."""
    row_ratio = seat["row_index"] / max(layout["rows"] - 1, 1)
    sigma = 0.18
    return float(math.exp(-0.5 * ((row_ratio - 0.5) / sigma) ** 2))


def _view_angle_score(seat: Dict, layout: Dict) -> float:
    """
    THX-inspired score targeting ~36 degree field of view.

    angle = 2*atan((screen_width/2)/distance_to_screen_plane)
    """
    xs = np.array([s["x"] for s in layout["seats"]], dtype=float)
    screen_width = (xs.max() - xs.min()) * layout["screen_width_factor"]
    screen_y = min(s["y"] for s in layout["seats"]) - 45.0
    dist = max(30.0, seat["y"] - screen_y)
    angle = math.degrees(2.0 * math.atan((screen_width / 2.0) / dist))
    return float(math.exp(-abs(angle - 36.0) / 18.0))


def _neighbor_score(seat: Dict, seat_state: Dict[str, Dict], layout: Dict) -> float:
    row = seat["row_index"]
    col = seat["col_index"]
    row_label = seat["row_label"]
    checks = [
        (row, col - 1, row_label),
        (row, col + 1, row_label),
        (row - 1, col, None),
        (row + 1, col, None),
    ]
    total = 0
    open_neighbors = 0
    for nrow, ncol, same_row_label in checks:
        if ncol < 0 or ncol >= layout["seats_per_row"] or nrow < 0 or nrow >= layout["rows"]:
            continue
        if same_row_label is not None:
            nid = f"{same_row_label}{ncol + 1}"
        else:
            nlabel = layout["seats"][nrow * layout["seats_per_row"]]["row_label"]
            nid = f"{nlabel}{ncol + 1}"
        total += 1
        if nid in seat_state and seat_state[nid]["status"] == "available":
            open_neighbors += 1
    if total == 0:
        return 0.5
    return open_neighbors / total


def _row_quality_score(seat: Dict, layout: Dict) -> float:
    row_ratio = seat["row_index"] / max(layout["rows"] - 1, 1)
    if row_ratio < 0.12:
        return 0.15
    if row_ratio > 0.90:
        return 0.55
    return float(max(0.0, 1.0 - abs(row_ratio - 0.52) / 0.52))


def _compute_individual_scores(layout: Dict, seat_state: Dict[str, Dict]) -> Dict[str, float]:
    scores = {}
    for seat in layout["seats"]:
        sid = seat["seat_id"]
        if seat_state[sid]["status"] != "available":
            scores[sid] = 0.0
            continue
        s_center = _horizontal_center_score(seat, layout)
        s_vertical = _vertical_position_score(seat, layout)
        s_angle = _view_angle_score(seat, layout)
        s_neighbor = _neighbor_score(seat, seat_state, layout)
        s_row = _row_quality_score(seat, layout)
        final = (
            SCORE_WEIGHTS["horizontal_center"] * s_center
            + SCORE_WEIGHTS["vertical_position"] * s_vertical
            + SCORE_WEIGHTS["view_angle"] * s_angle
            + SCORE_WEIGHTS["neighbor"] * s_neighbor
            + SCORE_WEIGHTS["row_quality"] * s_row
        )
        if seat.get("is_premium_center", False):
            final += 0.03
        scores[sid] = float(min(1.0, max(0.0, final)))
    return scores


def _resolve_group_size(scenario: str, rng: np.random.Generator) -> int:
    lo, hi = GROUP_SIZE_BY_SCENARIO[scenario]
    return int(rng.integers(lo, hi + 1))


def _contiguous_blocks(row_seats: List[Dict], n: int, seat_state: Dict[str, Dict]) -> List[List[str]]:
    blocks: List[List[str]] = []
    for i in range(0, len(row_seats) - n + 1):
        block = row_seats[i : i + n]
        ids = [seat["seat_id"] for seat in block]
        cols = [seat["col_index"] for seat in block]
        if not all(cols[j + 1] == cols[j] + 1 for j in range(n - 1)):
            continue
        if all(seat_state[sid]["status"] == "available" for sid in ids):
            blocks.append(ids)
    return blocks


def _pick_best_group(
    candidates: List[List[str]],
    scores: Dict[str, float],
    seat_lookup: Dict[str, Dict],
    seats_per_row: int,
) -> Tuple[List[str], float]:
    if not candidates:
        return [], 0.0
    best = ([], -1.0)
    center_col = (seats_per_row - 1) / 2.0
    for block in candidates:
        mean_score = float(np.mean([scores[sid] for sid in block]))
        cols = np.array([seat_lookup[sid]["col_index"] for sid in block], dtype=float)
        block_center = float(cols.mean())
        center_bonus = 1.0 - abs(block_center - center_col) / max(center_col, 1.0)
        final = mean_score + 0.08 * center_bonus
        if final > best[1]:
            best = (block, final)
    return best


def _family_candidates(rows: Dict[int, List[Dict]], seat_state: Dict[str, Dict], group_size: int) -> List[List[str]]:
    candidates = []
    for row in rows.values():
        blocks = _contiguous_blocks(row, group_size, seat_state)
        for block in blocks:
            types = [seat_state[sid]["seat_type"] for sid in block]
            if "wheelchair" in types and "companion" in types:
                candidates.append(block)
    return candidates


def recommend_seats(
    layout: Dict,
    seat_state: Dict[str, Dict],
    scenario: str,
    rng: np.random.Generator,
) -> Dict:
    rows = _build_row_map(layout)
    lookup = _seat_lookup(layout)
    scores = _compute_individual_scores(layout, seat_state)
    group_size = _resolve_group_size(scenario, rng)

    recommended: List[str] = []
    rec_score = 0.0

    if scenario == "solo":
        available = [sid for sid, s in seat_state.items() if s["status"] == "available"]
        if available:
            best_sid = max(available, key=lambda sid: scores[sid])
            recommended = [best_sid]
            rec_score = scores[best_sid]
    else:
        candidates = []
        if scenario == "family":
            # Keep family recommendations accessible. If the requested group size
            # is impossible, step down size while preserving wheelchair+companion.
            for n in range(group_size, 1, -1):
                candidates = _family_candidates(rows, seat_state, n)
                if candidates:
                    group_size = n
                    break
            if not candidates:
                # final family fallback: the best wheelchair+companion pair
                for row in rows.values():
                    for sid_pair in _contiguous_blocks(row, 2, seat_state):
                        types = [seat_state[sid]["seat_type"] for sid in sid_pair]
                        if "wheelchair" in types and "companion" in types:
                            candidates.append(sid_pair)
                if candidates:
                    group_size = 2
        else:
            # Group scenarios must stay contiguous. If N is unavailable,
            # progressively relax N to keep labels valid and realistic.
            for n in range(group_size, 0, -1):
                candidates = []
                for row in rows.values():
                    candidates.extend(_contiguous_blocks(row, n, seat_state))
                if candidates:
                    group_size = n
                    break

        recommended, rec_score = _pick_best_group(candidates, scores, lookup, layout["seats_per_row"])

    # Final fallback if still no candidate (extreme sold-out map): best single.
    if not recommended:
        avail = sorted(
            [sid for sid, s in seat_state.items() if s["status"] == "available"],
            key=lambda sid: scores[sid],
            reverse=True,
        )
        group_size = 1 if avail else 0
        recommended = avail[:1]
        rec_score = float(np.mean([scores[sid] for sid in recommended])) if recommended else 0.0

    all_scores = {}
    for seat in layout["seats"]:
        sid = seat["seat_id"]
        all_scores[sid] = {
            "status": seat_state[sid]["status"],
            "score": round(scores[sid], 3) if seat_state[sid]["status"] == "available" else 0.0,
            "row": seat["row_label"],
            "number": seat["number"],
        }

    return {
        "group_size": group_size,
        "recommended_seats": recommended,
        "recommended_score": round(float(rec_score), 3),
        "all_seat_scores": all_scores,
    }
