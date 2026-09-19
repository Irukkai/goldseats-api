"""Seat map renderer using Pillow."""

from __future__ import annotations

from typing import Dict, Iterable, Set

from PIL import Image, ImageDraw, ImageFont

from config import (
    BACKGROUND_COLOR,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    SCREEN_Y,
    SEAT_COLORS,
    SEAT_HEIGHT,
    SEAT_WIDTH,
)


def _color_for_seat(status: str, seat_type: str, is_recommended: bool) -> str:
    if is_recommended:
        return SEAT_COLORS["recommended"]
    if status == "booked":
        return SEAT_COLORS["booked"]
    return SEAT_COLORS[f"available_{seat_type}"]


def render_seat_map(
    layout: Dict,
    seat_state: Dict[str, Dict],
    recommended_seats: Iterable[str],
    theatre_type: str,
    scenario: str,
    occupancy_rate: float,
    output_path: str,
) -> None:
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")
    font_sm = ImageFont.load_default()

    # Screen glow + screen bar.
    screen_w = int(IMAGE_WIDTH * layout["screen_width_factor"])
    screen_h = 24
    sx0 = (IMAGE_WIDTH - screen_w) // 2
    sy0 = SCREEN_Y
    for i, alpha in enumerate((30, 22, 14, 8)):
        draw.rounded_rectangle(
            [sx0 - 8 - i * 4, sy0 - 8 - i * 2, sx0 + screen_w + 8 + i * 4, sy0 + screen_h + 8 + i * 2],
            radius=12 + i * 2,
            fill=(240, 240, 255, alpha),
        )
    draw.rounded_rectangle([sx0, sy0, sx0 + screen_w, sy0 + screen_h], radius=10, fill=(220, 226, 240, 255))
    draw.text((IMAGE_WIDTH // 2 - 20, sy0 + 6), "SCREEN", fill=(255, 255, 255, 255), font=font_sm)

    rec_set: Set[str] = set(recommended_seats)

    # Seat numbers (top from first row by col order).
    first_row = [s for s in layout["seats"] if s["row_index"] == 0]
    for seat in first_row:
        tx = int(seat["x"] + SEAT_WIDTH / 2 - 4)
        draw.text((tx, int(seat["y"] - 13)), str(seat["number"]), fill=(220, 220, 235, 220), font=font_sm)

    prev_row = None
    for seat in layout["seats"]:
        sid = seat["seat_id"]
        x0 = int(seat["x"])
        y0 = int(seat["y"])
        x1 = x0 + SEAT_WIDTH
        y1 = y0 + SEAT_HEIGHT
        state = seat_state[sid]
        color = _color_for_seat(state["status"], state["seat_type"], sid in rec_set)

        # subtle shadow
        draw.rounded_rectangle([x0 + 1, y0 + 2, x1 + 1, y1 + 2], radius=4, fill=(0, 0, 0, 60))

        if sid in rec_set:
            draw.rounded_rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], radius=5, outline=(255, 215, 0, 180), width=2)
            draw.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=7, outline=(255, 215, 0, 80), width=1)

        draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=color)

        # row labels on left
        if prev_row != seat["row_index"] and seat["number"] == 1:
            text_color = (255, 255, 255, 255)
            if seat["row_index"] % 5 == 0:
                draw.text((x0 - 22, y0 + 2), seat["row_label"], fill=text_color, font=font_sm)
            else:
                draw.text((x0 - 18, y0 + 3), seat["row_label"], fill=(225, 225, 240, 230), font=font_sm)
            prev_row = seat["row_index"]

    # Bottom legend.
    legend_y = IMAGE_HEIGHT - 80
    legend_items = [
        ("Regular", SEAT_COLORS["available_regular"]),
        ("Recliner", SEAT_COLORS["available_recliner"]),
        ("Wheelchair", SEAT_COLORS["available_wheelchair"]),
        ("Booked", SEAT_COLORS["booked"]),
        ("Recommended", SEAT_COLORS["recommended"]),
    ]
    lx = 28
    for label, color in legend_items:
        draw.rounded_rectangle([lx, legend_y, lx + 16, legend_y + 12], radius=3, fill=color)
        draw.text((lx + 22, legend_y - 1), label, fill=(230, 230, 240, 230), font=font_sm)
        lx += 128

    meta = f"{theatre_type.upper()} | {scenario} | Occupancy: {occupancy_rate * 100:.1f}%"
    draw.text((28, IMAGE_HEIGHT - 52), meta, fill=(235, 235, 245, 245), font=font_sm)

    img.save(output_path, format="PNG", optimize=True)
