#!/usr/bin/env python3
"""Render GitHub contribution counts as a looping isometric city GIF."""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "contributions.json"
OUTPUT_PATH = ROOT / "contribution-city.gif"

WIDTH, HEIGHT = 900, 390
TILE_W, TILE_H = 12, 6
ORIGIN_X, ORIGIN_Y = 312, 48
FRAMES = 34
FRAME_DURATION_MS = 75
BACKGROUND = "#0d1117"
GRID_EMPTY = "#202a35"
TEXT = "#c9d1d9"
MUTED = "#8b949e"

# GitHub's dark contribution palette, indexed by data-level (0 through 4).
PALETTE = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}


def font(size: int, bold: bool = False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def shade(hex_color: str, factor: float) -> str:
    value = hex_color.lstrip("#")
    rgb = [int(value[i:i + 2], 16) for i in (0, 2, 4)]
    rgb = [max(0, min(255, int(channel * factor))) for channel in rgb]
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def load_data():
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    days = payload.get("days", [])
    if not days:
        raise RuntimeError("contributions.json contains no daily records.")

    parsed = []
    for item in days:
        parsed.append({
            "date": date.fromisoformat(item["date"]),
            "count": max(0, int(item.get("count", 0))),
            "level": max(0, min(4, int(item.get("level", 0)))),
        })

    parsed.sort(key=lambda item: item["date"])
    return payload, parsed


def draw_diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float,
                 color: str, outline: str | None = None):
    points = [
        (cx, cy),
        (cx + TILE_W / 2, cy + TILE_H / 2),
        (cx, cy + TILE_H),
        (cx - TILE_W / 2, cy + TILE_H / 2),
    ]
    draw.polygon(points, fill=color, outline=outline)


def draw_building(draw: ImageDraw.ImageDraw, cx: float, base_y: float,
                  height: float, level: int):
    color = PALETTE[level]
    left = (cx - TILE_W / 2, base_y - height + TILE_H / 2)
    top = (cx, base_y - height)
    right = (cx + TILE_W / 2, base_y - height + TILE_H / 2)
    front = (cx, base_y - height + TILE_H)
    base_left = (cx - TILE_W / 2, base_y + TILE_H / 2)
    base_mid = (cx, base_y + TILE_H)
    base_right = (cx + TILE_W / 2, base_y + TILE_H / 2)

    # Two visible building faces and the roof.
    draw.polygon([left, top, front, base_mid, base_left],
                 fill=shade(color, 0.62))
    draw.polygon([top, right, base_right, base_mid, front],
                 fill=shade(color, 0.82))
    draw.polygon([left, top, right, front],
                 fill=color, outline=shade(color, 1.15))


def build_frame(payload, days, progress: float) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    # Header
    draw.text((34, 24), "CONTRIBUTION CITY", font=font(15, True), fill=TEXT)
    draw.text((34, 47), f"@{payload.get('username', 'github user')}",
              font=font(11), fill=MUTED)

    max_count = max((item["count"] for item in days), default=0)
    grid_start = days[0]["date"] - timedelta(
        days=(days[0]["date"].weekday() + 1) % 7
    )
    grid_end = days[-1]["date"]
    total_days = max(1, (grid_end - grid_start).days + 1)
    week_count = ((total_days - 1) // 7) + 1

    # Use a stable ordering so the animation grows across the calendar.
    indexed = []
    for item in days:
        weekday = (item["date"].weekday() + 1) % 7  # Sunday = row zero
        week = (item["date"] - grid_start).days // 7
        rank = (item["date"] - days[0]["date"]).days
        indexed.append((week, weekday, rank, item))

    # Draw the empty calendar plots first, from back to front.
    for week, weekday, _, item in sorted(indexed, key=lambda x: x[0] + x[1]):
        cx = ORIGIN_X + (week - weekday) * TILE_W / 2
        base_y = ORIGIN_Y + (week + weekday) * TILE_H / 2 + 75
        draw_diamond(draw, cx, base_y, GRID_EMPTY)

    # Animation wave: each date rises as the reveal moves through the year.
    for week, weekday, rank, item in sorted(indexed, key=lambda x: x[0] + x[1]):
        if item["count"] <= 0:
            continue

        normalized_rank = rank / max(1, len(days) - 1)
        local_progress = (progress - normalized_rank * 0.78) / 0.22
        reveal = max(0.0, min(1.0, local_progress))
        if reveal <= 0:
            continue

        # Square-root scaling keeps unusually busy days from dominating.
        scaled_height = 7 + 39 * math.sqrt(item["count"] / max_count)
        height = scaled_height * reveal
        cx = ORIGIN_X + (week - weekday) * TILE_W / 2
        base_y = ORIGIN_Y + (week + weekday) * TILE_H / 2 + 75
        draw_building(draw, cx, base_y, height, item["level"])

    # Small labels and summary stats.
    draw.text((34, 344), f"{payload.get('total_contributions', 0):,}",
              font=font(21, True), fill=TEXT)
    draw.text((34, 369), "CONTRIBUTIONS", font=font(9, True), fill=MUTED)

    draw.text((205, 344), f"{payload.get('active_days', 0):,}",
              font=font(21, True), fill=TEXT)
    draw.text((205, 369), "ACTIVE DAYS", font=font(9, True), fill=MUTED)

    draw.text((365, 344), f"{payload.get('current_streak', 0):,}",
              font=font(21, True), fill=TEXT)
    draw.text((365, 369), "CURRENT STREAK", font=font(9, True), fill=MUTED)

    # Contribution-level legend.
    legend_x, legend_y = 660, 354
    draw.text((legend_x, 335), "LESS", font=font(9, True), fill=MUTED)
    for level in range(5):
        x = legend_x + 34 + level * 22
        draw.rounded_rectangle(
            (x, legend_y, x + 14, legend_y + 14),
            radius=2,
            fill=PALETTE[level],
        )
    draw.text((legend_x + 150, 335), "MORE", font=font(9, True), fill=MUTED)

    # A subtle baseline keeps the isometric footprint grounded.
    draw.text((WIDTH - 34, 24), f"{week_count} WEEKS",
              font=font(9, True), fill=MUTED, anchor="ra")

    return image


def main():
    payload, days = load_data()
    frames = []
    for index in range(FRAMES):
        progress = index / (FRAMES - 1)
        frames.append(build_frame(payload, days, progress))

    # Hold the fully-built city briefly before the loop restarts.
    frames.extend([frames[-1].copy(), frames[-1].copy(), frames[-1].copy()])
    frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Rendered {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
