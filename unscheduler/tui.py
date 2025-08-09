# unscheduler/tui.py
import os
import io
import re
import json
from pathlib import Path
import contextlib
import humanize
from datetime import datetime
from typing import Optional, Tuple

from dateutil.parser import parse as parse_dt

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label, Input
from textual.reactive import reactive

from .parser import parse_schedule_file, get_events_for_week
from .stats import check_for_overlaps, calculate_and_print_stats
from .visualizer import create_calendar_pdf


# Minimal prompt screen for entering a time string (e.g., "5pm", "17:00", "5", "24:00")
class TimePrompt(Screen):
    def __init__(self, title: str):
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.title, id="prompt_title"),
            Input(placeholder="e.g., 5pm, 17:00, 5, 24:00", id="entry"),
        )

    def on_mount(self) -> None:
        self.query_one("#entry", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        # Allow Enter to submit; handled by on_input_submitted
        pass


# Helpers to parse start/end times per policy:
# Start-hour: floor minutes (7:30 -> 7), min=0, must be < end
# End-hour: ceil minutes (7:30 -> 8), max=24, must be > start
_H24_RE = re.compile(r"^\s*24(?::?0{2})?\s*$")
_H_RE = re.compile(r"^\s*(\d{1,2})\s*$")


def parse_start_hour(s: str) -> int:
    s = s.strip()
    if _H24_RE.match(s):
        raise ValueError("24:00 invalid for start")
    m = _H_RE.match(s)
    if m:
        h = int(m.group(1))
        if not (0 <= h <= 23):
            raise ValueError("hour out of range for start")
        return h
    dt = parse_dt(s)
    return dt.hour  # floor minutes by taking the hour


def parse_end_hour(s: str) -> int:
    s = s.strip()
    if _H24_RE.match(s):
        return 24
    m = _H_RE.match(s)
    if m:
        h = int(m.group(1))
        if h == 24:
            return 24
        if not (0 <= h <= 23):
            raise ValueError("hour out of range for end")
        return h
    dt = parse_dt(s)
    return dt.hour if dt.minute == 0 else min(dt.hour + 1, 24)  # ceil minutes


class SettingsManager:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'unscheduler'
        self.config_file = self.config_dir / 'settings.json'
        self.default_settings = {
            'orientation': 'Landscape',
            'time_format': '24h',
            'start_hour': 3,
            'end_hour': 22
        }

    def load_settings(self):
        """Load settings from file, return defaults if file doesn't exist."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return self.default_settings.copy()
        except Exception:
            return self.default_settings.copy()

    def save_settings(self, settings):
        """Save settings to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception:
            return False


class UnscheduleApp(App):
    TITLE = "Unschedule Analyzer [LIVE MODE]"
    BINDINGS = [
        ("o", "toggle_orientation", "Orientation"),
        ("s", "set_start_hour", "Set Start Hour"),
        ("e", "set_end_hour", "Set End Hour"),
        ("h", "toggle_time_format", "Time Format"),
        ("r", "force_refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    # State
    orientation = reactive("Landscape")
    time_format = reactive("24h")  # "24h" or "12h"
    start_hour = reactive(3)
    end_hour = reactive(22)
    last_file_mod_time = reactive(datetime.now())
    last_pdf_gen_time = reactive(datetime.now())

    def __init__(self, schedule_file: str):
        super().__init__()
        self.schedule_file_path = schedule_file
        self.all_commitments, self.all_categories, self.non_work_cats = [], set(), []
        self._reload_timer = None

        # Load persistent settings
        self.settings_manager = SettingsManager()
        saved_settings = self.settings_manager.load_settings()

        # Apply loaded settings to reactive properties
        self.orientation = saved_settings['orientation']
        self.time_format = saved_settings['time_format']
        self.start_hour = saved_settings['start_hour']
        self.end_hour = saved_settings['end_hour']

    def _save_settings(self):
        """Save current settings to disk."""
        current_settings = {
            'orientation': self.orientation,
            'time_format': self.time_format,
            'start_hour': self.start_hour,
            'end_hour': self.end_hour
        }
        self.settings_manager.save_settings(current_settings)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="root"):
            # Single combined status line to avoid spacing issues
            yield Label("", id="status_label")
            yield Static("Ready.", id="report_panel")
            with Vertical(id="footer_status"):
                yield Label("", id="file_mod_label")
                yield Label("", id="pdf_gen_label")
        yield Footer()

    def on_mount(self) -> None:
        self.update_status_line()
        self.run_analysis()
        self._reload_timer = self.set_interval(1.0, self._maybe_reload_on_save)

    def _maybe_reload_on_save(self) -> None:
        try:
            current_mod = datetime.fromtimestamp(
                os.path.getmtime(self.schedule_file_path))
            if current_mod > self.last_file_mod_time:
                self.run_analysis()
        except FileNotFoundError:
            self._safe_update(
                "#report_panel", "[bold red]Error: schedule file not found.[/]")

    def _safe_update(self, selector: str, text: str) -> None:
        try:
            node = self.query_one(selector)
            node.update(text)
        except Exception:
            pass

    def update_status_line(self) -> None:
        status = f"Orientation: {self.orientation} | Time Range: {self.start_hour:02d}:00 to {self.end_hour:02d}:00 | Time Format: {self.time_format}"
        self._safe_update("#status_label", status)

    def run_analysis(self) -> None:
        try:
            # Capture analysis output
            self.last_file_mod_time = datetime.fromtimestamp(
                os.path.getmtime(self.schedule_file_path))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.all_commitments, self.all_categories, self.non_work_cats, errors = parse_schedule_file(
                    self.schedule_file_path)
                if errors:
                    self._safe_update(
                        "#report_panel", "[bold red]Parsing errors detected.[/]")
                    return
                check_for_overlaps(self.all_commitments)
                calculate_and_print_stats(
                    self.all_commitments, self.all_categories, self.non_work_cats)
            self._safe_update("#report_panel", out.getvalue())

            # Generate calendars
            figsize = (8.5, 11) if self.orientation == "Portrait" else (11, 8.5)
            week_a_events = get_events_for_week(self.all_commitments, "A")
            create_calendar_pdf(week_a_events, "Week A", self.start_hour,
                                self.end_hour, self.time_format, figsize)
            week_b_events = get_events_for_week(self.all_commitments, "B")
            create_calendar_pdf(week_b_events, "Week B", self.start_hour,
                                self.end_hour, self.time_format, figsize)
            self.last_pdf_gen_time = datetime.now()
            self._safe_update(
                "#pdf_gen_label",
                f"Calendars Generated:  {self.last_pdf_gen_time.strftime('%Y-%m-%d %H:%M:%S')} ({humanize.naturaltime(self.last_pdf_gen_time)})",
            )
            self._safe_update(
                "#file_mod_label",
                f"Source File Modified:  {self.last_file_mod_time.strftime('%Y-%m-%d %H:%M:%S')} ({humanize.naturaltime(self.last_file_mod_time)})",
            )
        except Exception as e:
            self._safe_update(
                "#report_panel", f"[bold red]An error occurred during analysis:\n{e}[/]")

    # Watchers keep the single status line current
    def watch_orientation(self, old_value: str, new_value: str) -> None:
        self._save_settings()

    def watch_time_format(self, old_value: str, new_value: str) -> None:
        self._save_settings()

    def watch_start_hour(self, old_value: int, new_value: int) -> None:
        self._save_settings()

    def watch_end_hour(self, old_value: int, new_value: int) -> None:
        self._save_settings()

    # Actions
    def action_force_refresh(self) -> None:
        self.run_analysis()

    def action_toggle_orientation(self) -> None:
        self.orientation = "Portrait" if self.orientation == "Landscape" else "Landscape"
        self.run_analysis()

    def action_toggle_time_format(self) -> None:
        self.time_format = "12h" if self.time_format == "24h" else "24h"
        self.run_analysis()

    def action_set_start_hour(self) -> None:
        def _apply(result: Optional[str]) -> None:
            if not result:
                return
            try:
                new_start = parse_start_hour(result)
                if not (0 <= new_start < self.end_hour):
                    raise ValueError("start must be < end")
                self.start_hour = new_start
                self.run_analysis()
            except Exception as ex:
                self._safe_update(
                    "#report_panel", f"[bold yellow]Invalid start time ({result}): {ex}[/]")

        self.push_screen(TimePrompt("Enter Start Time:"), _apply)

    def action_set_end_hour(self) -> None:
        def _apply(result: Optional[str]) -> None:
            if not result:
                return
            try:
                new_end = parse_end_hour(result)
                if not (self.start_hour < new_end <= 24):
                    raise ValueError("end must be > start and <= 24")
                self.end_hour = new_end
                self.run_analysis()
            except Exception as ex:
                self._safe_update(
                    "#report_panel", f"[bold yellow]Invalid end time ({result}): {ex}[/]")

        self.push_screen(TimePrompt("Enter End Time:"), _apply)
