# unscheduler/visualizer.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as mticker
import textwrap
from datetime import datetime
from .constants import BLOCK_BORDER_WIDTH

# UFL periods for calendar labeling
UFL_PERIODS_DISPLAY = {
    'P1': (7.416667, 8.25),      # 7:25 to 8:15
    'P2': (8.5, 9.333333),       # 8:30 to 9:20
    'P3': (9.583333, 10.416667),  # 9:35 to 10:25
    'P4': (10.666667, 11.5),     # 10:40 to 11:30
    'P5': (11.75, 12.583333),    # 11:45 to 12:35
    'P6': (12.833333, 13.666667),  # 12:50 to 1:40
    'P7': (13.916667, 14.75),    # 1:55 to 2:45
    'P8': (15.0, 15.833333),     # 3:00 to 3:50
    'P9': (16.083333, 16.916667),  # 4:05 to 4:55
    'P10': (17.166667, 18.0),    # 5:10 to 6:00
    'P11': (18.25, 19.083333),   # 6:15 to 7:05
    'PE1': (19.333333, 20.166667),  # 7:20 to 8:10
    'PE2': (20.333333, 21.166667),  # 8:20 to 9:10
    'PE3': (21.333333, 22.166667),  # 9:20 to 10:10
}

# UFL period mapping (string format for accurate times)
UFL_PERIODS = {
    'P1': ('07:25', '08:15'),
    'P2': ('08:30', '09:20'),
    'P3': ('09:35', '10:25'),
    'P4': ('10:40', '11:30'),
    'P5': ('11:45', '12:35'),
    'P6': ('12:50', '13:40'),
    'P7': ('13:55', '14:45'),
    'P8': ('15:00', '15:50'),
    'P9': ('16:05', '16:55'),
    'P10': ('17:10', '18:00'),
    'P11': ('18:15', '19:05'),
    'PE1': ('19:20', '20:10'),
    'PE2': ('20:20', '21:10'),
    'PE3': ('21:20', '22:10'),
}

# Render-time mode for labels: "24h" or "12h"
TIME_FORMAT_MODE = "24h"


def time_to_float(time_str: str) -> float:
    h, m = map(int, time_str.split(":"))
    return h + m / 60.0


def get_text_color_for_bg(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "black" if luminance > 0.5 else "white"


def _format_time_12h(time_str: str) -> str:
    # Linux-friendly 12h formatting; on macOS/Linux %-I avoids leading zero
    return datetime.strptime(time_str, "%H:%M").strftime("%-I:%M %p")


def format_time_ampm(time_str: str) -> str:
    """
    Return a label for HH:MM based on TIME_FORMAT_MODE.
    In 24h mode, returns 'HH:MM'; in 12h mode, returns 'H:MM AM/PM'.
    """
    if TIME_FORMAT_MODE == "24h":
        return time_str
    return _format_time_12h(time_str)


def _format_hour_tick(v: float) -> str:
    # Only label integer hours
    if abs(v - round(v)) > 1e-6:
        return ""
    h = int(round(v)) % 24
    if TIME_FORMAT_MODE == "24h":
        return f"{h:02d}:00"
    h12 = h % 12 or 12
    suffix = "AM" if h < 12 else "PM"
    return f"{h12} {suffix}"


def draw_events_on_grid(ax, events: list, start_h: int, end_h: int, num_days: int):
    """Draws events, clipping them to the visible time window and day range."""
    day_map = {code: i for i, code in enumerate("MTWRFSU")}
    for event in events:
        day_index = day_map.get(event["day_code"])
        if day_index is None or day_index >= num_days:
            continue

        if event["type"] == "block":
            s, e, color = (
                time_to_float(event["start"]),
                time_to_float(event["end"]),
                event["color"],
            )
            if event.get("spans_midnight", False):
                text_color = get_text_color_for_bg(color)
                # Evening part on the original day
                if max(s, start_h) < min(24.0, end_h) and day_index < num_days:
                    rect_start = max(s, start_h)
                    rect_end = min(24.0, end_h)

                    ax.add_patch(
                        patches.Rectangle(
                            (day_index, rect_start),
                            1,
                            rect_end - rect_start,
                            facecolor=color,
                            edgecolor="black",
                            linewidth=BLOCK_BORDER_WIDTH,
                            alpha=0.7,
                            zorder=3,
                        )
                    )

                    # Fix: Position text within visible rectangle
                    text_y = rect_start + 0.1
                    ax.text(
                        day_index + 0.5,
                        text_y,
                        event["event"],
                        ha="center",
                        va="top",
                        color=text_color,
                        fontsize=8,
                        weight="normal",
                        zorder=5,
                    )

                # Morning part on the next day
                next_day_index = (day_index + 1) % 7
                if max(0.0, start_h) < min(e, end_h) and next_day_index < num_days:
                    rect_start = max(0.0, start_h)
                    rect_end = min(e, end_h)

                    ax.add_patch(
                        patches.Rectangle(
                            (next_day_index, rect_start),
                            1,
                            rect_end - rect_start,
                            facecolor=color,
                            edgecolor="black",
                            linewidth=BLOCK_BORDER_WIDTH,
                            alpha=0.7,
                            zorder=3,
                        )
                    )

                    # Fix: Position text within visible rectangle
                    text_y = rect_start + 0.1
                    ax.text(
                        next_day_index + 0.5,
                        text_y,
                        event["event"],
                        ha="center",
                        va="top",
                        color=text_color,
                        fontsize=8,
                        weight="normal",
                        zorder=5,
                    )
            else:
                # Regular event (doesn't span midnight)
                if max(s, start_h) < min(e, end_h):
                    text_color = get_text_color_for_bg(color)
                    rect_start = max(s, start_h)
                    rect_end = min(e, end_h)

                    ax.add_patch(
                        patches.Rectangle(
                            (day_index, rect_start),
                            1,
                            rect_end - rect_start,
                            facecolor=color,
                            edgecolor="black",
                            linewidth=BLOCK_BORDER_WIDTH,
                            alpha=0.7,
                            zorder=5,
                        )
                    )

                    # Fix: Position text within visible rectangle
                    text_y = rect_start + 0.1
                    ax.text(
                        day_index + 0.5,
                        text_y,
                        event["event"],
                        ha="center",
                        va="top",
                        color=text_color,
                        fontsize=8,
                        weight="normal",
                        zorder=5,
                    )

        elif event["type"] == "trigger":
            t = time_to_float(event["time"])
            if start_h <= t <= end_h:
                trigger_text = f"{format_time_ampm(event['time'])} → {event['event']}"
                ax.text(
                    day_index + 0.5,
                    t,
                    trigger_text,
                    ha="center",
                    va="bottom",
                    color=event["color"],
                    fontsize=6,
                    weight="regular",
                    zorder=5,
                )


def create_calendar_pdf(
    events: list,
    title: str,
    start_h: int,
    end_h: int,
    time_format: str,
    figsize: tuple,
    show_weekends: bool = True,
):
    """Creates and saves a single week's calendar PDF."""
    global TIME_FORMAT_MODE
    TIME_FORMAT_MODE = time_format

    fig, ax = plt.subplots(figsize=figsize)
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    
    if not show_weekends:
        days = days[:5]  # Only weekdays
    
    num_days = len(days)

    ax.set_xlim(0, num_days)
    ax.set_xticks([i + 0.5 for i in range(num_days)])
    ax.set_xticklabels(days, fontsize=9)
    ax.set_xlabel("")
    ax.set_ylim(end_h, start_h)

    # Day columns as minor gridlines
    ax.set_xticks(range(0, num_days + 1), minor=True)
    ax.grid(True, which="minor", axis="x",
            linestyle="-", linewidth=0.9, zorder=1)

    # Weekend divider between Friday (index 4) and Saturday (index 5)
    # Only draw if weekends are shown
    if show_weekends:
        ax.axvline(x=5, color="green", linestyle="-",
                   linewidth=1.5, alpha=0.8, zorder=1)

    # Left axis (main) - UFL Periods with time annotations
    period_positions = []
    for period, (start_time, end_time) in UFL_PERIODS_DISPLAY.items():
        if start_h <= start_time <= end_h:
            label_y = (start_time + end_time) / 2
            period_positions.append(label_y)

            # Get original time strings from UFL_PERIODS (avoid floating point errors)
            start_orig, end_orig = UFL_PERIODS[period]

            # Format using the 12h/24h toggle
            time_str = f"{format_time_ampm(start_orig)}-{format_time_ampm(end_orig)}"

            # Draw period label and time annotation
            ax.text(-0.02, label_y - 0.005, period, fontsize=8, weight='normal',
                    va='bottom', ha='right', color='black', transform=ax.get_yaxis_transform())
            ax.text(-0.02, label_y + 0.005, time_str, fontsize=6,
                    va='top', ha='right', color='gray', style='italic', transform=ax.get_yaxis_transform())

    # Hide left axis ticks since we're drawing custom labels
    ax.set_yticks([])

    # Right axis (twinx) - Time with dashed grid lines
    ax2 = ax.twinx()
    ax2.set_ylim(end_h, start_h)
    ax2.set_yticks(range(start_h, end_h + 1))
    ax2.yaxis.set_minor_locator(mticker.AutoMinorLocator(2))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, pos: _format_hour_tick(v)))
    ax2.grid(True, which="major", axis="y",
             linestyle="--", linewidth=0.7, zorder=1)
    ax2.grid(True, which="minor", axis="y",
             linestyle=":", linewidth=0.5, zorder=1)

    draw_events_on_grid(ax, events, start_h, end_h, num_days)
    ax.set_title(title, fontsize=16, pad=30)

    # Tight layout with margins for labels
    fig_width, fig_height = fig.get_size_inches()
    margin = 0.5
    fig.tight_layout(
        rect=[
            margin / fig_width,
            margin / fig_height,
            1 - (margin / fig_width),
            1 - (margin / fig_height),
        ],
        pad=1.0,
    )

    filename = f"{title.lower().replace(' ', '_')}.pdf"
    plt.savefig(filename)
    print(f"✓ Generated {filename}")
    plt.close(fig)