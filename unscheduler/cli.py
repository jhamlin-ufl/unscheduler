# unscheduler/cli.py
import os
import sys
import subprocess
import argparse
from pathlib import Path

from .tui import UnscheduleApp, SettingsManager


def main():
    """CLI entry point for the unscheduler application."""
    parser = argparse.ArgumentParser(description="Unscheduler - Schedule visualization and analysis")
    parser.add_argument('schedule_file', nargs='?', help='Path to schedule file')
    parser.add_argument('--no-editor', action='store_true', help='Do not open editor automatically')
    parser.add_argument('--no-pdf', action='store_true', help='Do not open PDF files automatically')
    
    args = parser.parse_args()
    
    # Load settings to get last file
    settings_mgr = SettingsManager()
    settings = settings_mgr.load_settings()
    
    # Determine which file to use
    if args.schedule_file:
        schedule_file = os.path.abspath(args.schedule_file)
    elif 'last_schedule_file' in settings and settings['last_schedule_file']:
        schedule_file = settings['last_schedule_file']
        print(f"Using last schedule file: {schedule_file}")
    else:
        print("Error: No schedule file specified and no previous file found.")
        print(f"Usage: unscheduler <schedule_filename>")
        sys.exit(1)
    
    # Check if file exists
    if not os.path.exists(schedule_file):
        print(f"Error: File '{schedule_file}' not found.")
        sys.exit(1)
    
    # Save as last used file
    settings['last_schedule_file'] = schedule_file
    settings_mgr.save_settings(settings)
    
    # Open editor in background if not disabled
    if not args.no_editor:
        try:
            terminal = os.environ.get('TERMINAL', 'x-terminal-emulator')
            subprocess.Popen([terminal, '-e', 'nvim', schedule_file])
        except FileNotFoundError:
            print("Warning: Could not launch terminal, skipping editor")
    
    # Callback to open PDF after first generation
    def open_pdf():
        if not args.no_pdf and os.path.exists('weeks.pdf'):
            try:
                subprocess.Popen(['okular', 'weeks.pdf'])
            except FileNotFoundError:
                print("Warning: okular not found")
    
    # Create the app with callback and run it
    app = UnscheduleApp(schedule_file=schedule_file, on_first_render_callback=open_pdf)
    app.run()


if __name__ == "__main__":
    main()