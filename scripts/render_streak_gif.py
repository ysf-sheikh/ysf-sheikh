import json
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "contributions.json"
OUTPUT_FILE = ROOT / "contrib-streak.gif"

WIDTH = 1000
HEIGHT = 340

BACKGROUND = "#0d1117"
PANEL = "#161b22"
GRID_EMPTY = "#21262d"

GRID_ACTIVE = [
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
]

TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED = "#8b949e"
ACCENT = "#39d353"
ACCENT_GLOW = "#69f0a0"
RED = "#f85149"

CELL_SIZE = 13
CELL_GAP = 4
CELL_STEP = CELL_SIZE + CELL_GAP

FPS_DELAY = 65
INTRO_FRAMES = 12
FRAMES_PER_DAY = 2
FINALE_FRAMES = 35

MAX_ANIMATION_DAYS = 200


# ============================================================
# FONTS
# ============================================================

def load_font(size, bold=False):

    candidates = []

    if bold:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ])
    else:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ])

    for font_path in candidates:

        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


FONT_TITLE = load_font(21, True)
FONT_SMALL = load_font(10)
FONT_DAY = load_font(17, True)
FONT_COUNTER = load_font(43, True)
FONT_LABEL = load_font(11)


# ============================================================
# LOAD CONTRIBUTION DATA
# ============================================================

def load_data():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Contribution data not found: {DATA_FILE}"
        )

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_streak(data):

    days = {
        date.fromisoformat(item["date"]): int(item["level"])
        for item in data["days"]
    }

    today = date.today()

    # If today has no contributions, check yesterday.
    if days.get(today, 0) == 0:
        today -= timedelta(days=1)

    streak = []

    current = today

    while days.get(current, 0) > 0:

        streak.append({
            "date": current,
            "level": days[current],
        })

        current -= timedelta(days=1)

    streak.reverse()

    return streak, days


# ============================================================
# CALENDAR LAYOUT
# ============================================================

def get_calendar_layout(days):

    first_date = min(days)
    last_date = max(days)

    # Sunday-first calendar.
    start = first_date - timedelta(
        days=(first_date.weekday() + 1) % 7
    )

    # Complete the final calendar week.
    end = last_date + timedelta(
        days=(5 - last_date.weekday()) % 7 + 1
    )

    cells = []

    current = start

    while current < end:

        column = (current - start).days // 7
        row = (current.weekday() + 1) % 7

        cells.append({
            "date": current,
            "column": column,
            "row": row,
            "level": days.get(current, 0),
        })

        current += timedelta(days=1)

    return cells


# ============================================================
# DRAWING HELPERS
# ============================================================

def rounded_rectangle(draw, box, radius, fill, outline=None):

    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
    )


def draw_glow(image, x, y):

    glow = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(glow)

    draw.ellipse(
        (
            x - 15,
            y - 15,
            x + 15,
            y + 15,
        ),
        fill=(57, 211, 83, 100),
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(radius=8)
    )

    image.alpha_composite(glow)


# ============================================================
# FRAME RENDERING
# ============================================================

def render_frame(
    calendar,
    streak,
    progress,
    start_date,
    missing_date,
    final=False,
):

    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(image)

    # HEADER
    draw.text(
        (42, 27),
        "CONTRIBUTION STREAK",
        font=FONT_LABEL,
        fill=ACCENT,
    )

    draw.text(
        (42, 48),
        "Consistency compounds.",
        font=FONT_TITLE,
        fill=TEXT_PRIMARY,
    )

    draw.text(
        (42, 79),
        "ONE DAY AT A TIME / EVERY DAY COUNTS",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
    )

    # CALENDAR PANEL
    rounded_rectangle(
        draw,
        (35, 110, 965, 294),
        12,
        PANEL,
        "#30363d",
    )

    calendar_x = 75
    calendar_y = 151

    # Progress tracking.
    completed = max(
        0,
        min(progress, len(streak))
    )

    completed_dates = {
        item["date"]: item["level"]
        for item in streak[:completed]
    }

    current_item = (
        streak[completed]
        if completed < len(streak)
        else None
    )

    current_date = (
        current_item["date"]
        if current_item
        else None
    )

    # CALENDAR CELLS
    for cell in calendar:

        x = calendar_x + cell["column"] * CELL_STEP
        y = calendar_y + cell["row"] * CELL_STEP

        current = cell["date"]

        color = GRID_EMPTY

        if current in completed_dates:

            level = completed_dates[current]

            color = GRID_ACTIVE[
                max(0, min(level - 1, 3))
            ]

        elif current == current_date:

            color = "#1c4428"

        elif current == missing_date:

            color = "#2d2225"

        rounded_rectangle(
            draw,
            (
                x,
                y,
                x + CELL_SIZE,
                y + CELL_SIZE,
            ),
            3,
            color,
        )

    # MISSING DAY MARKER
    missing_cell = next(
        (
            cell for cell in calendar
            if cell["date"] == missing_date
        ),
        None,
    )

    if missing_cell:

        x = calendar_x + missing_cell["column"] * CELL_STEP
        y = calendar_y + missing_cell["row"] * CELL_STEP

        draw.line(
            (x + 3, y + 3, x + 10, y + 10),
            fill=RED,
            width=2,
        )

        draw.line(
            (x + 10, y + 3, x + 3, y + 10),
            fill=RED,
            width=2,
        )

    # MOVING DOT
    if current_item and not final:

        current_cell = next(
            (
                cell for cell in calendar
                if cell["date"] == current_item["date"]
            ),
            None,
        )

        if current_cell:

            x = calendar_x + current_cell["column"] * CELL_STEP
            y = calendar_y + current_cell["row"] * CELL_STEP

            center_x = x + CELL_SIZE // 2
            center_y = y + CELL_SIZE // 2

            draw_glow(
                image,
                center_x,
                center_y,
            )

            draw = ImageDraw.Draw(image)

            draw.ellipse(
                (
                    center_x - 5,
                    center_y - 5,
                    center_x + 5,
                    center_y + 5,
                ),
                fill=ACCENT_GLOW,
                outline="#ffffff",
                width=1,
            )

    # COUNTER
    counter_x = 730

    draw.text(
        (counter_x, 145),
        "CURRENT STREAK",
        font=FONT_LABEL,
        fill=TEXT_MUTED,
    )

    draw.text(
        (counter_x, 164),
        f"{completed:03d}",
        font=FONT_COUNTER,
        fill=ACCENT,
    )

    draw.text(
        (counter_x + 105, 189),
        "DAYS",
        font=FONT_LABEL,
        fill=TEXT_PRIMARY,
    )

    if final:
        status = "STREAK COMPLETE"
    elif completed == 0:
        status = "READY TO BEGIN"
    else:
        status = "KEEP GOING"

    draw.text(
        (counter_x, 224),
        status,
        font=FONT_SMALL,
        fill=ACCENT if final else TEXT_MUTED,
    )

    # FOOTER
    draw.text(
        (42, 311),
        f"STARTED {start_date.strftime('%b %d, %Y').upper()}",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
    )

    draw.text(
        (WIDTH - 42, 311),
        "PERSONAL PROGRESS",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
        anchor="ra",
    )

    return image.convert("RGB")


# ============================================================
# CREATE ANIMATION
# ============================================================

def create_animation():

    data = load_data()

    streak, days = get_streak(data)

    if not streak:

        raise ValueError(
            "No active contribution streak was found."
        )

    if len(streak) > MAX_ANIMATION_DAYS:

        streak = streak[-MAX_ANIMATION_DAYS:]

    calendar = get_calendar_layout(days)

    start_date = streak[0]["date"]

    missing_date = start_date - timedelta(days=1)

    frames = []

    # INTRO
    for _ in range(INTRO_FRAMES):

        frames.append(
            render_frame(
                calendar,
                streak,
                0,
                start_date,
                missing_date,
            )
        )

    # DAY-BY-DAY PROGRESSION
    for day_index in range(len(streak)):

        for _ in range(FRAMES_PER_DAY):

            frames.append(
                render_frame(
                    calendar,
                    streak,
                    day_index,
                    start_date,
                    missing_date,
                )
            )

    # FINAL FRAME
    final_frame = render_frame(
        calendar,
        streak,
        len(streak),
        start_date,
        missing_date,
        final=True,
    )

    for _ in range(FINALE_FRAMES):

        frames.append(final_frame)

    # EXPORT
    frames[0].save(
        OUTPUT_FILE,
        save_all=True,
        append_images=frames[1:],
        duration=FPS_DELAY,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print("--------------------------------")
    print("STREAK ANIMATION GENERATED")
    print("--------------------------------")
    print(f"Streak length: {len(streak)} days")
    print(f"Started: {start_date}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Frames: {len(frames)}")
    print("--------------------------------")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    create_animation()
