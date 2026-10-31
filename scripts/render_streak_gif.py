import json
import math
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

# Limit the animation's frame count to keep the GIF manageable.
MAX_ANIMATION_DAYS = 200


# ============================================================
# FONT HELPERS
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
FONT_SUBTITLE = load_font(12)
FONT_DAY = load_font(17, True)
FONT_SMALL = load_font(10)
FONT_COUNTER = load_font(43, True)
FONT_LABEL = load_font(11, True)


# ============================================================
# DATA
# ============================================================

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_streak(data):
    days = {
        item["date"]: int(item["level"])
        for item in data["days"]
    }

    today = date.today()

    if days.get(today.isoformat(), 0) == 0:
        today -= timedelta(days=1)

    streak = []
    current = today

    while True:
        key = current.isoformat()

        if days.get(key, 0) == 0:
            break

        streak.append({
            "date": current,
            "level": days[key],
        })

        current -= timedelta(days=1)

    streak.reverse()

    return streak, days


# ============================================================
# CALENDAR LAYOUT
# ============================================================

def get_calendar_layout(days):
    """
    Arrange contribution days into a Sunday-first calendar.
    Each column represents one week.
    """

    first_date = min(days)
    last_date = max(days)

    # Move backward to the Sunday starting the first week.
    start = first_date - timedelta(days=(first_date.weekday() + 1) % 7)

    # Move forward to the Saturday ending the last week.
    end = last_date + timedelta(days=(5 - last_date.weekday()) % 7 + 1)

    cells = []
    current = start

    while current < end:
        column = (current - start).days // 7
        row = (current.weekday() + 1) % 7

        cells.append({
            "date": current,
            "column": column,
            "row": row,
            "level": days.get(current.isoformat(), 0),
        })

        current += timedelta(days=1)

    return cells


# ============================================================
# DRAWING HELPERS
# ============================================================

def rounded_rectangle(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def centered_text(draw, center_x, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]

    draw.text(
        (center_x - text_width / 2, y),
        text,
        font=font,
        fill=fill,
    )


def draw_glow(image, x, y, radius=15):
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)

    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=(57, 211, 83, 100),
    )

    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))

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

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

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
        "ONE DAY AT A TIME  /  EVERY DAY COUNTS",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
    )

    # --------------------------------------------------------
    # CALENDAR PANEL
    # --------------------------------------------------------

    rounded_rectangle(
        draw,
        (35, 110, 965, 294),
        12,
        PANEL,
        outline="#30363d",
    )

    calendar_x = 75
    calendar_y = 151

    # Calculate calendar width and horizontal spacing.
    max_column = max(cell["column"] for cell in calendar)

    # --------------------------------------------------------
    # CALENDAR CELLS
    # --------------------------------------------------------

    active_dates = {
        item["date"]: item["level"]
        for item in streak
    }

    completed = max(0, min(progress, len(streak)))

    completed_dates = {
        item["date"].isoformat(): item["level"]
        for item in streak[:completed]
    }

    current_item = (
        streak[completed]
        if completed < len(streak)
        else None
    )

    current_date = (
        current_item["date"].isoformat()
        if current_item
        else None
    )

    # Background cells.
    for cell in calendar:
        x = calendar_x + cell["column"] * CELL_STEP
        y = calendar_y + cell["row"] * CELL_STEP

        key = cell["date"].isoformat()

        color = GRID_EMPTY

        if key in completed_dates:
            level = completed_dates[key]
            color = GRID_ACTIVE[max(0, min(level - 1, 3))]

        elif key == current_date:
            color = "#1c4428"

        elif cell["date"] == missing_date:
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

    # --------------------------------------------------------
    # MISSING DAY MARKER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # MOVING DOT
    # --------------------------------------------------------

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

            draw_glow(image, center_x, center_y)

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

    # --------------------------------------------------------
    # COUNTER
    # --------------------------------------------------------

    counter_x = 730

    draw.text(
        (counter_x, 145),
        "CURRENT STREAK",
        font=FONT_LABEL,
        fill=TEXT_MUTED,
    )

    day_number = completed

    draw.text(
        (counter_x, 164),
        f"{day_number:03d}",
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

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    start_label = start_date.strftime("%b %d, %Y").upper()

    draw.text(
        (42, 311),
        f"STARTED {start_label}",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
    )

    draw.text(
        (WIDTH - 42, 311),
        "AUREL / PERSONAL PROGRESS",
        font=FONT_SMALL,
        fill=TEXT_MUTED,
        anchor="ra",
    )

    return image.convert("RGB")


# ============================================================
# ANIMATION
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

    # --------------------------------------------------------
    # INTRO
    # --------------------------------------------------------

    for _ in range(INTRO_FRAMES):
        frames.append(
            render_frame(
                calendar,
                streak,
                progress=0,
                start_date=start_date,
                missing_date=missing_date,
            )
        )

    # --------------------------------------------------------
    # DAY-BY-DAY PROGRESSION
    # --------------------------------------------------------

    for day_index in range(len(streak)):
        for _ in range(FRAMES_PER_DAY):
            frames.append(
                render_frame(
                    calendar,
                    streak,
                    progress=day_index,
                    start_date=start_date,
                    missing_date=missing_date,
                )
            )

    # --------------------------------------------------------
    # FINAL FRAME
    # --------------------------------------------------------

    final_frame = render_frame(
        calendar,
        streak,
        progress=len(streak),
        start_date=start_date,
        missing_date=missing_date,
        final=True,
    )

    for _ in range(FINALE_FRAMES):
        frames.append(final_frame)

    # --------------------------------------------------------
    # EXPORT GIF
    # --------------------------------------------------------

    frames[0].save(
        OUTPUT_FILE,
        save_all=True,
        append_images=frames[1:],
        duration=FPS_DELAY,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"Animation generated: {OUTPUT_FILE}")
    print(f"Streak length: {len(streak)} days")
    print(f"Streak started: {start_date}")
    print(f"Frames generated: {len(frames)}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    create_animation()
