# main.py
import os
import sys

# Import the main application class from our new tui module
from unscheduler.tui import UnscheduleApp

def main():
    """The main entry point for the application."""
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(__file__)} <schedule_filename>")
        return
        
    schedule_file = sys.argv[1]
    if not os.path.exists(schedule_file):
        print(f"Error: File '{schedule_file}' not found.")
        return

    # Create an instance of our Textual app and run it
    app = UnscheduleApp(schedule_file=schedule_file)
    app.run()

if __name__ == "__main__":
    main()