import json
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


USERNAME = "ysf-sheikh"

URL = f"https://github.com/users/{USERNAME}/contributions"

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch_contributions():
    print(f"Fetching contributions for @{USERNAME}...")
    print(URL)

    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    days = soup.select("td.ContributionCalendar-day")

    if not days:
        raise RuntimeError(
            "Could not find GitHub contribution cells. "
            "GitHub may have changed its page structure."
        )

    contributions = []

    for day in days:
        date = day.get("data-date")
        level = day.get("data-level")

        if not date or level is None:
            continue

        try:
            level = int(level)
        except ValueError:
            level = 0

        contributions.append(
            {
                "date": date,
                "level": level,
            }
        )

    if not contributions:
        raise RuntimeError("No contribution data was found.")

    contributions.sort(key=lambda x: x["date"])

    total = sum(
        1
        for day in contributions
        if day["level"] > 0
    )

    # Calculate total contribution count from the accessible
    # aria-label/title text when available.
    total_contributions = 0

    for day in days:
        text = day.get("aria-label", "")

        match = re.search(
            r"(\d[\d,]*)\s+contribution",
            text
        )

        if match:
            total_contributions += int(
                match.group(1).replace(",", "")
            )

    # Fallback if GitHub's accessibility text isn't available.
    if total_contributions == 0:
        total_contributions = total

    # Current streak
    contribution_dates = {
        day["date"]
        for day in contributions
        if day["level"] > 0
    }

    longest_streak = 0
    current_streak = 0

    sorted_dates = sorted(contribution_dates)

    previous_date = None
    streak = 0

    for date_string in sorted_dates:
        date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

        if previous_date is not None:
            difference = (date - previous_date).days

            if difference == 1:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1

        longest_streak = max(
            longest_streak,
            streak
        )

        previous_date = date

    # Calculate current streak from today backwards.
    from datetime import date, timedelta

    today = date.today()

    # If today has no contribution, allow yesterday to be
    # the beginning of the current streak.
    if today.isoformat() in contribution_dates:
        current_day = today
    else:
        current_day = today - timedelta(days=1)

    while current_day.isoformat() in contribution_dates:
        current_streak += 1
        current_day -= timedelta(days=1)

    data = {
        "username": USERNAME,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_contributions": total_contributions,
        "active_days": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "days": contributions,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2
        )

    print()
    print("Contribution data saved successfully.")
    print(f"Days found: {len(contributions)}")
    print(f"Contributions: {total_contributions}")
    print(f"Current streak: {current_streak}")
    print(f"Longest streak: {longest_streak}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    fetch_contributions()