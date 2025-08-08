Of course. A good `README.md` is essential. It should not only explain how to use the tool but also capture the philosophy behind it. Here is a comprehensive README file that explains the purpose, usage, and, most importantly, the detailed syntax for creating your schedule file.

You can save this directly as `README.md` in your project's root directory.

---

# Unschedule Analyzer

This tool generates printable, bi-weekly "unschedule" calendars and provides a detailed time-allocation analysis. It is designed for academics, researchers, and anyone with a complex, recurring schedule who wants to reclaim time for focused, deep work.

The core philosophy is based on Cal Newport's "unschedule" concept: instead of trying to schedule every moment of deep work (which is brittle), you schedule all of your fixed commitments (classes, meetings, family time, etc.). The empty space that remains is your deep work time. This tool helps you visualize that empty space.

## Features

*   **Generates Bi-Weekly Calendars**: Creates two separate, high-quality PDF calendars for a "Week A" / "Week B" schedule.
*   **Interactive Configuration**: Prompts you for the desired time range and page orientation (Portrait/Landscape) each time you run it.
*   **Simple Input File**: All schedule information is defined in a single, human-readable `.txt` file.
*   **Powerful Time Parsing**: Understands flexible time formats like `9a`, `5pm`, `14:30`, and `5:15p`.
*   **Handles Complex Schedules**: Natively understands overnight events (like sleep) and recurring appointments.
*   **Detailed Analytics**: After generating the PDFs, it prints a full statistical report of how your time is allocated, including the average number of unscheduled hours available per week.

## Requirements

*   Python 3.x
*   The following Python packages:
    *   `matplotlib`
    *   `python-dateutil`

You can install these using `pip`:
```sh
pip install matplotlib python-dateutil
```
Or if you are using `poetry`:
```sh
poetry add matplotlib python-dateutil
```

## Usage

Run the script from your terminal, providing the path to your schedule file as a command-line argument.

```sh
python unschedule_analyzer.py schedule.txt
```

The script will then prompt you to enter the time range and page orientation for the calendars you want to generate.

## The `schedule.txt` File Format

This is the heart of the tool. All your recurring commitments are defined here. The file is read line by line. Lines starting with `#` are comments and are ignored.

### 1. Defining Categories and Colors (Optional)

You can define categories and assign them a specific color using the `@` symbol at the start of a line. This is useful for creating a consistent color scheme.

**Format:** `@CategoryName: color`

*   `color` can be a named color (`blue`, `green`) or a hex code (`#4682B4`).
*   Any category used later without being defined this way will be assigned a color automatically from a default palette.

**Example:**
```text
@Teaching: #4682B4
@Lab: #2E8B57
@Family: purple
```

### 2. Setting the Current Category Context

To avoid re-typing categories for every event, you can set an "active" category. All subsequent events will be assigned to this category until a new one is set.

**Format:** `@CategoryName`

**Example:**
```text
@Teaching
# All events below this line will be in the "Teaching" category
Weekly MWF 9a 10:30a PHY7001 Lecture
Weekly TR 11a 12:30p Office Hours
```

### 3. Defining Events

There are two types of events: **Blocks** (with a duration) and **Triggers** (instantaneous).

#### Event Blocks

These represent a block of scheduled time.

**Format:** `Recurrence DayString StartTime EndTime Description`

*   **`Recurrence`**: Can be one of three values:
    *   `Weekly`: The event occurs every week.
    *   `WeekA`: The event occurs only in "Week A".
    *   `WeekB`: The event occurs only in "Week B".
*   **`DayString`**: A string of single characters representing the days of the week. No spaces.
    *   `M` - Monday, `T` - Tuesday, `W` - Wednesday, `R` - Thursday, `F` - Friday, `S` - Saturday, `U` - Sunday.
    *   Example: `MWF` for an event on Monday, Wednesday, and Friday.
*   **`StartTime` / `EndTime`**: The start and end times. Flexible formats like `9a`, `5pm`, `14:30`, `4:30p` are all valid.
*   **`Description`**: The rest of the line is the event's title.

#### Event Triggers

These represent an instantaneous prompt for an action. They have no end time.

**Format:** `Recurrence DayString Time Description`

**Example:** `Weekly MTWRF 5p Check Cryostat`

### 4. Inline Category Overrides

If you want to assign a category to a single event without changing the active context, you can add an inline tag at the end of the line.

**Format:** `... @CategoryName`

This is useful for one-off events or for listing items chronologically.

**Example:**
```text
# This event gets the "Admin" category, regardless of the current context.
Weekly F 1p 2p Dept. Faculty Mtg @Admin
```

### Full Example `schedule.txt`

```text
# =============================================================
# Unschedule Configuration for an Experimental Physics Prof
# =============================================================

@Teaching: #4682B4
@Lab: #2E8B57
@Family: #8A2BE2
@Writing: #D2691E
@Sleep: #696969

# --- Teaching ---
@Teaching
Weekly MWF 9a 10:30a PHY7001 Lecture
Weekly TR 11a 12:30p Office Hours

# --- Lab & Research ---
@Lab
WeekA T 2p 4p Lab Group Mtg
WeekB T 2p 4p Student Mtgs
# This is a trigger and will be black by default
Weekly MTWRF 5p Check Cryostat

# --- Deep Work ---
@Writing
Weekly MWF 6a 8a Paper/Proposal

# --- Admin ---
# These use inline tags and will get auto-generated colors.
Weekly F 1p 2p Dept. Faculty Mtg @Admin
WeekA M 1p 2p Grant Budget Review @Admin

# --- Family & Commute ---
@Family
Weekly MTWRFSU 6p 7p Family Dinner
Weekly W 7p 8p Kids' Soccer

# Commute gets its own auto-color and overrides the "Family" context
Weekly MTWRF 8:30a To Campus @Commute
Weekly MTWRF 5:15p To Home @Commute
Weekly F 4:30p School Pickup @Commute

# --- Personal & Sleep ---
@Sleep
# This trigger is under the Sleep context, but as a trigger, it remains black.
Weekly MTWRFSU 9:45p Prep for tomorrow

# This tests the overnight event logic
Weekly MTWRFSU 10p 4a Sleep
```

## Output

Running the script will produce two files in the same directory:
1.  `week_a.pdf`
2.  `week_b.pdf`

It will also print a detailed time allocation analysis to your console.