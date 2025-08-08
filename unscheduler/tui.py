# unscheduler/tui.py
import os
import io
import contextlib
import humanize
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Label, Button, Input
from textual.reactive import reactive
from textual.validation import Integer

# Import our existing project modules
from .parser import parse_schedule_file, get_events_for_week
from .stats import check_for_overlaps, calculate_and_print_stats
from .visualizer import create_calendar_pdf


class TimeRangeScreen(Screen):
    """A modal screen for setting the calendar's time range."""

    def __init__(self, start_hour: int, end_hour: int):
        super().__init__()
        self.start_hour = start_hour
        self.end_hour = end_hour

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        with Vertical(id="dialog"):
            yield Label("Set Time Range", id="dialog_title")
            
            yield Label("Start Hour (0-23):")
            self.start_input = Input(
                str(self.start_hour),
                id="start_hour_input",
                validators=[Integer(minimum=0, maximum=23)]
            )
            yield self.start_input
            
            # --- NEW: Add a blank Static widget for spacing ---
            yield Static() 
            
            yield Label("End Hour (1-24):")
            self.end_input = Input(
                str(self.end_hour),
                id="end_hour_input",
                validators=[Integer(minimum=1, maximum=24)]
            )
            yield self.end_input
            
            with Horizontal(id="dialog_buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.submit_and_dismiss()
        else:
            self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_and_dismiss()

    def submit_and_dismiss(self) -> None:
        try:
            if self.start_input.is_valid and self.end_input.is_valid:
                new_start = int(self.start_input.value)
                new_end = int(self.end_input.value)
                
                if new_end > new_start:
                    self.dismiss((new_start, new_end))
                else:
                    self.app.notify("Start hour must be less than end hour.", title="Invalid Range", severity="error")
            else:
                self.app.notify("Please enter valid hours (0-23 for start, 1-24 for end).", title="Invalid Input", severity="error")
        except ValueError:
            self.app.notify("Invalid number format.", title="Error", severity="error")


class UnscheduleApp(App):
    """The main application class."""

    CSS_PATH = "tui.css"
    TITLE = "Unschedule Analyzer [LIVE MODE]"
    BINDINGS = [
        ("o", "toggle_orientation", "Orientation"),
        ("t", "set_time_range", "Time Range"),
        ("r", "force_refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    orientation = reactive("Landscape")
    start_hour = reactive(3)
    end_hour = reactive(22)
    last_file_mod_time = reactive(datetime.now())
    last_pdf_gen_time = reactive(datetime.now())

    def __init__(self, schedule_file: str):
        super().__init__()
        self.schedule_file_path = schedule_file
        self.all_commitments, self.all_categories, self.non_work_cats = [], set(), []
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main_container"):
            yield Label(f"Watching: {self.schedule_file_path}")
            yield Label("", id="orientation_label")
            yield Label("", id="time_range_label")
            yield Static(id="divider1", markup="[b]---[/b]")
            yield Label("", id="file_mod_label")
            yield Label("", id="pdf_gen_label")
            yield Static(id="divider2", markup="[b]---[/b]")
            yield Static("Awaiting first analysis...", id="report_panel", expand=True)
        yield Footer()

    def watch_orientation(self, new_orientation: str): self.query_one("#orientation_label").update(f"Orientation: {new_orientation}")
    def watch_start_hour(self): self.update_time_range_label()
    def watch_end_hour(self): self.update_time_range_label()
    def update_time_range_label(self): self.query_one("#time_range_label").update(f"Time Range: {self.start_hour}:00 to {self.end_hour}:00")
    def watch_last_file_mod_time(self, mod_time: datetime): self.query_one("#file_mod_label").update(f"Source File Modified:  {mod_time.strftime('%Y-%m-%d %H:%M:%S')} ({humanize.naturaltime(mod_time)})")
    def watch_last_pdf_gen_time(self, gen_time: datetime): self.query_one("#pdf_gen_label").update(f"Calendars Generated:  {gen_time.strftime('%Y-%m-%d %H:%M:%S')} ({humanize.naturaltime(gen_time)})")

    def on_mount(self):
        self.watch_orientation(self.orientation)
        self.update_time_range_label()
        self.run_analysis()
        self.set_interval(1.0, self.check_file_modification)
        
    def check_file_modification(self):
        try:
            current_mod_time = datetime.fromtimestamp(os.path.getmtime(self.schedule_file_path))
            if current_mod_time > self.last_file_mod_time:
                if self._refresh_timer is not None: self._refresh_timer.stop()
                self._refresh_timer = self.set_timer(0.5, self.run_analysis)
        except FileNotFoundError:
            self.query_one("#report_panel").update("[bold red]Error: schedule file not found.[/]")

    def run_analysis(self):
        try:
            self.last_file_mod_time = datetime.fromtimestamp(os.path.getmtime(self.schedule_file_path))
            output_stream = io.StringIO()
            with contextlib.redirect_stdout(output_stream):
                self.all_commitments, self.all_categories, self.non_work_cats, errors = parse_schedule_file(self.schedule_file_path)
                if errors: self.query_one("#report_panel").update("[bold red]Parsing errors detected.[/]"); return
                check_for_overlaps(self.all_commitments)
                calculate_and_print_stats(self.all_commitments, self.all_categories, self.non_work_cats)
            report = output_stream.getvalue()
            self.query_one("#report_panel").update(report)
            figsize = (8.5, 11) if self.orientation == "Portrait" else (11, 8.5)
            week_a_events = get_events_for_week(self.all_commitments, 'A')
            create_calendar_pdf(week_a_events, "Week A", self.start_hour, self.end_hour, figsize)
            week_b_events = get_events_for_week(self.all_commitments, 'B')
            create_calendar_pdf(week_b_events, "Week B", self.start_hour, self.end_hour, figsize)
            self.last_pdf_gen_time = datetime.now()
        except Exception as e:
            self.query_one("#report_panel").update(f"[bold red]An error occurred during analysis:\n{e}[/]")

    def action_force_refresh(self): self.run_analysis()
    def action_toggle_orientation(self): self.orientation = "Portrait" if self.orientation == "Landscape" else "Landscape"; self.run_analysis()
    def action_set_time_range(self) -> None:
        self.app.push_screen(TimeRangeScreen(self.start_hour, self.end_hour), self.update_time_range_from_dialog)

    def update_time_range_from_dialog(self, result: tuple | None) -> None:
        if result is not None:
            new_start, new_end = result
            self.start_hour, self.end_hour = new_start, new_end
            self.run_analysis()