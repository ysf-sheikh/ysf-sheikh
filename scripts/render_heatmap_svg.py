import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "contributions.json"
OUTPUT_FILE = ROOT / "contrib-heatmap.svg"


PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",
]


def load_data():
    with DATA_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def create_svg(data):
    days = data["days"]

    total = data["total_contributions"]
    current_streak = data["current_streak"]
    longest_streak = data["longest_streak"]

    # Convert dates into lookup dictionary.
    contribution_map = {
        day["date"]: day["level"]
        for day in days
    }

    dates = sorted(contribution_map.keys())

    if not dates:
        raise RuntimeError(
            "No contribution data available."
        )

    first_date = datetime.strptime(
        dates[0],
        "%Y-%m-%d"
    ).date()

    # Move backward to Sunday so the first column
    # begins at the start of a week.
    from datetime import timedelta

    first_date -= timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    last_date = datetime.strptime(
        dates[-1],
        "%Y-%m-%d"
    ).date()

    # Move forward to Saturday.
    last_date += timedelta(
        days=(6 - ((last_date.weekday() + 1) % 7))
    )

    total_days = (
        last_date - first_date
    ).days + 1

    weeks = (total_days + 6) // 7

    cell = 13
    gap = 4

    step = cell + gap

    left = 40
    top = 45

    width = left + weeks * step + 10
    height = top + 7 * step + 95

    svg_parts = []

    svg_parts.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}">
        
        <style>
            .cell {{
                opacity: 0;
                animation: reveal 0.45s ease-out forwards;
            }}

            @keyframes reveal {{
                from {{
                    opacity: 0;
                    transform: translateY(-8px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            .title {{
                font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
                font-size: 15px;
                font-weight: 600;
                fill: #f0f6fc;
            }}

            .text {{
                font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
                font-size: 11px;
                fill: #8b949e;
            }}

            .stat {{
                font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
                font-size: 12px;
                fill: #c9d1d9;
            }}
        </style>

        <rect width="100%" height="100%"
              rx="12"
              fill="#0d1117"
              stroke="#30363d"/>

        <text
            x="{left}"
            y="24"
            class="title">
            github.com/{data["username"]}
        </text>
        '''
    )

    # Render the contribution cells.
    for index in range(total_days):
        current = first_date + timedelta(days=index)

        week = index // 7
        weekday = index % 7

        date_string = current.isoformat()

        level = contribution_map.get(
            date_string,
            0
        )

        color = PALETTE[
            min(level, len(PALETTE) - 1)
        ]

        x = left + week * step
        y = top + weekday * step

        delay = (
            week * 0.025 +
            weekday * 0.02
        )

        svg_parts.append(
            f'''
            <rect
                class="cell"
                x="{x}"
                y="{y}"
                width="{cell}"
                height="{cell}"
                rx="3"
                fill="{color}"
                style="animation-delay: {delay:.3f}s">
                <title>
                    {date_string}: contribution level {level}
                </title>
            </rect>
            '''
        )

    footer_y = top + 7 * step + 30

    svg_parts.append(
        f'''
        <text
            x="{left}"
            y="{footer_y}"
            class="stat">
            {total:,} contributions
        </text>

        <text
            x="{left + 160}"
            y="{footer_y}"
            class="text">
            Current streak: {current_streak} days
        </text>

        <text
            x="{left + 330}"
            y="{footer_y}"
            class="text">
            Longest streak: {longest_streak} days
        </text>

        <text
            x="{width - 150}"
            y="{footer_y + 30}"
            class="text">
            Less
        </text>
        '''
    )

    legend_x = width - 110
    legend_y = footer_y + 18

    for index, color in enumerate(PALETTE):
        svg_parts.append(
            f'''
            <rect
                x="{legend_x + index * 17}"
                y="{legend_y}"
                width="12"
                height="12"
                rx="3"
                fill="{color}"/>
            '''
        )

    svg_parts.append(
        f'''
        <text
            x="{width - 8}"
            y="{footer_y + 30}"
            text-anchor="end"
            class="text">
            More
        </text>

        </svg>
        '''
    )

    return "".join(svg_parts)


def main():
    data = load_data()

    svg = create_svg(data)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print(
        f"Heatmap written to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()