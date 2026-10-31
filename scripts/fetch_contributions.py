#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar and save daily counts + levels."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "ysf-sheikh"
PROFILE_URL = f"https://github.com/users/{USERNAME}/contributions"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "contributions.json"
COUNT_RE = re.compile(r"(\d[\d,]*)\s+contributions?", re.IGNORECASE)


def parse_count(element) -> int:
    """Read the actual contribution count from GitHub's accessible label/title."""
    for attribute in ("aria-label", "title"):
        value = element.get(attribute, "") or ""
        match = COUNT_RE.search(value)
        if match:
            return int(match.group(1).replace(",", ""))
        if "no contributions" in value.lower():
            return 0

    # Some GitHub markup versions place the label on a child element.
    for child in element.select("[aria-label], [title]"):
        for attribute in ("aria-label", "title"):
            value = child.get(attribute, "") or ""
            match = COUNT_RE.search(value)
            if match:
                return int(match.group(1).replace(",", ""))
            if "no contributions" in value.lower():
                return 0
    return 0


def calculate_streaks(days: list[dict]) -> tuple[int, int]:
    active_dates = {
        date.fromisoformat(item["date"])
        for item in days
        if item["count"] > 0
    }
    if not active_dates:
        return 0, 0

    latest = max(date.fromisoformat(item["date"]) for item in days)
    # If the newest calendar cell is today and has no activity yet, count from
    # yesterday. Otherwise, count from the latest calendar date.
    anchor = latest
    if anchor not in active_dates:
        anchor -= timedelta(days=1)

    current = 0
    cursor = anchor
    while cursor in active_dates:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    running = 0
    previous = None
    for day in sorted(active_dates):
        if previous is not None and day == previous + timedelta(days=1):
            running += 1
        else:
            running = 1
        longest = max(longest, running)
        previous = day

    return current, longest


def main() -> None:
    response = requests.get(
        PROFILE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; contribution-city/1.0)",
            "Accept": "text/html",
        },
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cells = soup.select("[data-date][data-level]")
    if not cells:
        raise RuntimeError(
            "Could not find GitHub contribution cells. GitHub may have changed "
            "its page markup; no data file was overwritten."
        )

    days = []
    for cell in cells:
        raw_date = cell.get("data-date")
        raw_level = cell.get("data-level")
        try:
            day = date.fromisoformat(raw_date)
            level = max(0, min(4, int(raw_level)))
        except (TypeError, ValueError):
            continue

        count = parse_count(cell)
        if level > 0 and count == 0:
            # Avoid silently generating a misleading skyline if GitHub's
            # accessible count label is missing or its markup has changed.
            raise RuntimeError(
                f"Contribution count could not be read for {raw_date}. "
                "The existing contributions.json has been left untouched."
            )

        days.append({
            "date": day.isoformat(),
            "count": count,
            "level": level,
        })

    days.sort(key=lambda item: item["date"])
    if not days:
        raise RuntimeError("GitHub returned no parseable contribution dates.")

    current_streak, longest_streak = calculate_streaks(days)
    payload = {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": sum(item["count"] for item in days),
        "active_days": sum(item["count"] > 0 for item in days),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "days": days,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Saved {len(days)} days | {payload['total_contributions']} "
        f"contributions | {payload['active_days']} active days"
    )


if __name__ == "__main__":
    main()
