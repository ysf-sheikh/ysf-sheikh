import json
from datetime import date, timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "contributions.json"
OUTPUT_FILE = ROOT / "contrib-streak.gif"

WIDTH = 1000
HEIGHT = 380

# Clean aesthetic theme matching target
BACKGROUND = "#ffffff"
TEXT_PRIMARY = "#111111"
TEXT_MUTED = "#666666"
RED = "#d1242f"

GRID_EMPTY = "#ebedf0"
GRID_FADED = "#f4f5f6"

GRID_ACTIVE = [
    "#9be9a8",
    "#40c463",
    "#30a14e",
    "#216e39",
]

CELL_SIZE = 13
CELL_GAP = 4
CELL_STEP = CELL_SIZE + CELL_GAP

FPS_DELAY = 50
INTRO_FRAMES = 10
FRAMES_PER_DAY = 1
FINALE_FRAMES = 40


# ============================================================
# FONTS
# ============================================================

def load_font(size, bold=False, serif=False):
    candidates = []
    if serif:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        ])
    else:
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


FONT_HUGE = load_font(56, bold=True, serif=True)
FONT_SUB = load_font(10)
FONT_RED_LABEL = load_font(10, bold=True)


# ============================================================
# LOAD DATA & STREAK LOGIC
# ============================================================

def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Contribution data not found: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_streak(data):
    days = {
        date.fromisoformat(item["date"]): int(item["level"])
        for item in data["days"]
    }

    today = date.today()
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

def get_calendar_layout(streak_start, last_date):
    start = streak_start - timedelta(days=(streak_start.weekday() + 1) % 7)
    end = last_date + timedelta(days=(5 - last_date.weekday()) % 7 + 1)

    cells = []
    current = start
    while current <= end:
        column = (current - start).days // 7
        row = (current.weekday() + 1) % 7
        cells.append({
            "date": current,
            "column": column,
            "row": row,
        })
        current += timedelta(days=1)

    return cells


# ============================================================
# FRAME RENDERING
# ============================================================

def render_frame(
    calendar,
    streak,
    days_map,
    progress,
    start_date,
    last_day_off,
    final=False,
):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    current_day_count = max(0, min(progress, len(streak)))

    # HEADER: Day Counter
    draw.text(
        (40, 25),
        f"Day {current_day_count}",
        font=FONT_HUGE,
        fill=TEXT_PRIMARY,
    )

    draw.text(
        (40, 92),
        f"SINCE {start_date.strftime('%d %b %Y').upper()}",
        font=FONT_SUB,
        fill=TEXT_MUTED,
    )

    if last_day_off:
        draw.text(
            (WIDTH - 40, 92),
            f"LAST DAY OFF: {last_day_off.strftime('%d %b %Y').upper()}",
            font=FONT_RED_LABEL,
            fill=RED,
            anchor="ra",
        )

    calendar_x = 40
    calendar_y = 150

    completed_streak_dates = {item["date"] for item in streak[:current_day_count]}
    active_streak_dates = {item["date"] for item in streak}
    cell_lookup = {c["date"]: c for c in calendar}

    # DRAW CELLS
    for cell in calendar:
        x = calendar_x + cell["column"] * CELL_STEP
        y = calendar_y + cell["row"] * CELL_STEP
        current_date = cell["date"]

        color = GRID_EMPTY
        level = days_map.get(current_date, 0)

        if current_date in active_streak_dates:
            if current_date in completed_streak_dates:
                color = GRID_ACTIVE[min(max(0, level - 1), 3)]
            else:
                color = GRID_FADED
        else:
            color = GRID_FADED

        draw.rounded_rectangle(
            (x, y, x + CELL_SIZE, y + CELL_SIZE),
            radius=3,
            fill=color,
        )

    # LAST DAY OFF RED CROSS
    if last_day_off:
        cross_cell = cell_lookup.get(last_day_off)
        if cross_cell:
            cx = calendar_x + cross_cell["column"] * CELL_STEP
            cy = calendar_y + cross_cell["row"] * CELL_STEP
            draw.text(
                (cx + 2, cy - 2),
                "×",
                font=load_font(14, bold=True),
                fill=RED,
            )

    # CONNECTING LINE THROUGH STREAK DAYS IN CHRONOLOGICAL ORDER + LEADING DOT
    if current_day_count > 0:
        points = []
        for i in range(current_day_count):
            item = streak[i]
            c = cell_lookup.get(item["date"])
            if c:
                px = calendar_x + c["column"] * CELL_STEP + CELL_SIZE // 2
                py = calendar_y + c["row"] * CELL_STEP + CELL_SIZE // 2
                points.append((px, py))

        # Draw connecting line through all passed days
        if len(points) >= 2:
            draw.line(points, fill="#555555", width=2)

        # Draw leading dot at the current day tip
        if points and not final:
            last_pt = points[-1]
            draw.ellipse(
                (last_pt[0] - 5, last_pt[1] - 5, last_pt[0] + 5, last_pt[1] + 5),
                fill="#30a14e",
                outline="#ffffff",
                width=1,
            )

    return image.convert("RGB")


# ============================================================
# CREATE ANIMATION
# ============================================================

def create_animation():
    data = load_data()
    streak, days_map = get_streak(data)

    if not streak:
        raise ValueError("No active contribution streak found.")

    start_date = streak[0]["date"]
    last_date = max(days_map.keys())
    last_day_off = start_date - timedelta(days=1)

    calendar = get_calendar_layout(start_date, last_date)
    frames = []

    for _ in range(INTRO_FRAMES):
        frames.append(render_frame(calendar, streak, days_map, 0, start_date, last_day_off))

    for day_index in range(1, len(streak) + 1):
        for _ in range(FRAMES_PER_DAY):
            frames.append(render_frame(calendar, streak, days_map, day_index, start_date, last_day_off))

    final_frame = render_frame(calendar, streak, days_map, len(streak), start_date, last_day_off, final=True)
    for _ in range(FINALE_FRAMES):
        frames.append(final_frame)

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


if __name__ == "__main__":
    create_animation()
