# unscheduler/visualizer.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as mticker
import textwrap
from datetime import datetime
from .constants import BLOCK_BORDER_WIDTH

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


def draw_events_on_grid(ax, events: list, start_h: int, end_h: int):
    """Draws events, clipping them to the visible time window."""
    day_map = {code: i for i, code in enumerate("MTWRFSU")}
    for event in events:
        day_index = day_map.get(event["day_code"])
        if day_index is None:
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
                if max(s, start_h) < min(24.0, end_h):
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
                if max(0.0, start_h) < min(e, end_h):
                    next_day_index = (day_index + 1) % 7
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

    ax.set_xlim(0, 7)
    ax.set_xticks([i + 0.5 for i in range(len(days))])
    ax.set_xticklabels(days, fontsize=9)
    ax.set_xlabel("")
    ax.set_ylim(end_h, start_h)

    # Day columns as minor gridlines
    ax.set_xticks(range(0, 8), minor=True)
    ax.grid(True, which="minor", axis="x",
            linestyle="-", linewidth=0.9, zorder=1)

    # Weekend divider between Friday (index 4) and Saturday (index 5)
    ax.axvline(x=5, color="green", linestyle="-",
               linewidth=1.5, alpha=0.8, zorder=1)

    # Hour ticks and formatting
    ax.set_yticks(range(start_h, end_h + 1))
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(2))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, pos: _format_hour_tick(v)))
    ax.grid(True, which="major", axis="y",
            linestyle="--", linewidth=0.7, zorder=1)
    ax.grid(True, which="minor", axis="y",
            linestyle=":", linewidth=0.5, zorder=1)

    draw_events_on_grid(ax, events, start_h, end_h)
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
