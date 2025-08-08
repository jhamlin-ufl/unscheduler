# unschedule_analyzer.py
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as mticker
import textwrap
import re
import os
import sys
from dateutil.parser import parse
from datetime import datetime

# ==============================================================================
# SECTION 1: DATA PARSING & FILTERING
# (No changes in this section)
# ==============================================================================

DAY_CODES = "MTWRFSU"
COLOR_PALETTE = ["#AEC7E8", "#FFBB78", "#98DF8A", "#FF9896", "#C5B0D5", "#C49C94", "#F7B6D2", "#DBDB8D", "#9EDAE5", "#AD494A"]
DEFAULT_TRIGGER_COLOR = "black"

class ColorAssigner:
    def __init__(self, palette):
        self.palette = palette
        self.manual_color_map = {}
        self.auto_color_map = {}
        self.next_color_index = 0
        self.palette_cycled = False

    def define_color(self, category, color):
        self.manual_color_map[category] = color

    def get_color(self, category):
        if category in self.manual_color_map:
            return self.manual_color_map[category]
        if category not in self.auto_color_map:
            if not self.palette_cycled and self.next_color_index >= len(self.palette):
                print(f"Warning: Reached end of {len(self.palette)}-color palette. Colors will be reused.")
                self.palette_cycled = True
            color = self.palette[self.next_color_index % len(self.palette)]
            self.auto_color_map[category] = color
            self.next_color_index += 1
        return self.auto_color_map[category]

def parse_schedule_file(filename: str) -> (list, set, bool):
    commitments, categories_found, parsing_errors_found = [], set(), False
    color_assigner = ColorAssigner(COLOR_PALETTE)
    current_category = None
    with open(filename, 'r') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'): continue

            if line.startswith('@'):
                parts = line[1:].split(':', 1)
                category_name = parts[0].strip()
                current_category = category_name
                categories_found.add(category_name)
                if len(parts) > 1:
                    color_assigner.define_color(category_name, parts[1].strip())
                continue
            
            try:
                inline_match = re.search(r'\s@(\S+)$', line)
                inline_category = None
                if inline_match:
                    inline_category = inline_match.group(1)
                    categories_found.add(inline_category)
                    line = line[:inline_match.start()].strip()
                
                words = line.split()
                if len(words) < 3: continue

                is_trigger = True
                try:
                    parse(words[3])
                    is_trigger = False
                except (ValueError, IndexError):
                    is_trigger = True

                recurrence, day_str = words[0], words[1].upper()
                for day_char in day_str:
                    if day_char not in DAY_CODES: continue
                    
                    event_base = {"recurrence": recurrence, "day_code": day_char}
                    if is_trigger:
                        event = {**event_base, "type": "trigger", "time": parse(words[2]).strftime('%H:%M'), "event": ' '.join(words[3:])}
                        if inline_category:
                            event["category"], event["color"] = inline_category, color_assigner.get_color(inline_category)
                        else:
                            event["category"], event["color"] = None, DEFAULT_TRIGGER_COLOR
                    else:
                        start_time, end_time = parse(words[2]).time(), parse(words[3]).time()
                        event_category = inline_category or current_category
                        if event_category: categories_found.add(event_category)
                        event = {**event_base, "type": "block", "start": start_time.strftime('%H:%M'), "end": end_time.strftime('%H:%M'), "event": ' '.join(words[4:]), "category": event_category, "color": color_assigner.get_color(event_category) if event_category else 'gray', "spans_midnight": end_time < start_time}
                    commitments.append(event)
            except Exception as e:
                print(f"Error on line {i}: '{line}' -> {e}")
                parsing_errors_found = True
    return commitments, categories_found, parsing_errors_found

def get_events_for_week(all_commitments: list, week_type: str) -> list:
    return [c for c in all_commitments if c["recurrence"] == "Weekly" or (c["recurrence"] == f"Week{week_type}")]

# ==============================================================================
# SECTION 2: VISUALIZATION LOGIC
# ==============================================================================
def time_to_float(time_str: str) -> float:
    h, m = map(int, time_str.split(':'))
    return h + m / 60.0

def get_text_color_for_bg(hex_color: str) -> str:
    h = hex_color.lstrip('#')
    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return 'black' if luminance > 0.5 else 'white'

def format_time_ampm(time_str: str) -> str:
    return datetime.strptime(time_str, '%H:%M').strftime('%-I:%M %p')

def draw_events_on_grid(ax, events: list, start_h: int, end_h: int):
    day_map = {code: i for i, code in enumerate('MTWRFSU')}
    for event in events:
        day_index = day_map.get(event['day_code'])
        if day_index is None: continue

        if event['type'] == 'block':
            s, e, color = time_to_float(event['start']), time_to_float(event['end']), event['color']
            if event.get('spans_midnight', False):
                text_color = get_text_color_for_bg(color)
                # Evening part
                draw_s_eve, draw_e_eve = max(s, start_h), min(24.0, end_h)
                if draw_e_eve > draw_s_eve:
                    ax.add_patch(patches.Rectangle((day_index, draw_s_eve), 1, draw_e_eve-draw_s_eve, facecolor=color, edgecolor='darkgray', linewidth=0.5, alpha=0.7))
                    ax.text(day_index+0.5, s+0.1, event['event'], ha='center', va='top', color=text_color, fontsize=8, weight='semibold')
                # Morning part
                next_day_index = (day_index + 1) % 7
                draw_s_morn, draw_e_morn = max(0.0, start_h), min(e, end_h)
                if draw_e_morn > draw_s_morn:
                    ax.add_patch(patches.Rectangle((next_day_index, draw_s_morn), 1, draw_e_morn-draw_s_morn, facecolor=color, edgecolor='darkgray', linewidth=0.5, alpha=0.7))
                    ax.text(next_day_index+0.5, e-0.1, event['event'], ha='center', va='bottom', color=text_color, fontsize=8, weight='semibold')
            else:
                draw_s, draw_e = max(s, start_h), min(e, end_h)
                if draw_e > draw_s:
                    ax.add_patch(patches.Rectangle((day_index, draw_s), 1, draw_e-draw_s, facecolor=color, edgecolor='darkgray', linewidth=0.5, alpha=0.7))
                    ax.text(day_index+0.5, s+(e-s)/2, textwrap.fill(event['event'], 15), ha='center', va='center', color=get_text_color_for_bg(color), fontsize=8)
        
        elif event['type'] == 'trigger':
            t = time_to_float(event['time'])
            if start_h <= t <= end_h:
                trigger_text = f"{format_time_ampm(event['time'])} → {event['event']}"
                ax.text(day_index+0.5, t, trigger_text, ha='center', va='bottom', color=event['color'], fontsize=6, weight='regular')

def create_calendar_pdf(events: list, title: str, start_h: int, end_h: int, figsize: tuple):
    fig, ax = plt.subplots(figsize=figsize)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    ax.set_xlim(0, 7)
    ax.set_xticks([i + 0.5 for i in range(len(days))])
    ax.set_xticklabels(days, fontsize=9)
    ax.tick_params(axis='x', which='both', bottom=True, top=True, labelbottom=True, labeltop=True, length=0)
    ax.set_xticks(range(8), minor=True)
    ax.grid(True, which='minor', axis='x', linestyle='-', linewidth=0.9)
    ax.axvline(x=5, color='green', linestyle='-', linewidth=1.5, alpha=0.8)
    
    ax.set_ylim(end_h, start_h)
    ax.set_yticks(range(start_h, end_h + 1))
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(2))
    ax.grid(True, which='major', axis='y', linestyle='--', linewidth=0.7)
    ax.grid(True, which='minor', axis='y', linestyle=':', linewidth=0.5)
    
    draw_events_on_grid(ax, events, start_h, end_h)
    ax.set_title(title, fontsize=16, pad=20)
    
    # --- CORRECTED MARGIN LOGIC ---
    # Use fig.tight_layout with a rect argument to enforce margins
    fig_width, fig_height = fig.get_size_inches()
    margin = 0.5
    rect = [
        margin / fig_width,         # left
        margin / fig_height,        # bottom
        1 - (margin / fig_width),   # right
        1 - (margin / fig_height)   # top
    ]
    fig.tight_layout(rect=rect, pad=1.0)
    
    filename = f"{title.lower().replace(' ', '_')}.pdf"
    plt.savefig(filename)
    print(f"✓ Generated {filename}")
    plt.close(fig)

# ==============================================================================
# SECTION 3: STATISTICS & MAIN EXECUTION
# (No changes in this section)
# ==============================================================================

def calculate_and_print_stats(all_commitments: list):
    category_hours = {}
    FMT = '%H:%M'
    for event in all_commitments:
        if event['type'] == 'block':
            start = datetime.strptime(event['start'], FMT)
            end = datetime.strptime(event['end'], FMT)
            duration = (end - start).total_seconds() / 3600
            if duration < 0:
                duration += 24
            
            multiplier = 2 if event['recurrence'] == 'Weekly' else 1
            biweekly_duration = duration * multiplier
            
            category = event.get('category')
            if category:
                category_hours[category] = category_hours.get(category, 0) + biweekly_duration

    print("\n--- Weekly Time Allocation Analysis ---")
    if not category_hours:
        print("No scheduled blocks found to analyze.")
        return
        
    total_scheduled_hours = sum(category_hours.values())
    total_hours_in_two_weeks = 2 * 7 * 24
    
    unscheduled_hours = total_hours_in_two_weeks - total_scheduled_hours
    category_hours['Unscheduled'] = unscheduled_hours
    
    print(f"{'Category':<15} | {'Avg. Hours/Wk':<15} | {'Avg. Hours/Day':<15}")
    print("-" * 52)
    
    sorted_categories = sorted(category_hours.items(), key=lambda item: item[1], reverse=True)
    
    for cat, total_hrs in sorted_categories:
        avg_hrs_wk = total_hrs / 2
        avg_hrs_day = total_hrs / 14
        print(f"{cat:<15} | {avg_hrs_wk:<15.1f} | {avg_hrs_day:<15.1f}")
        
def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(__file__)} <schedule_filename>")
        return
        
    schedule_filename = sys.argv[1]
    if not os.path.exists(schedule_filename):
        print(f"Error: File '{schedule_filename}' not found.")
        return

    print(f"--- Reading '{schedule_filename}' ---")
    all_commitments, categories, errors = parse_schedule_file(schedule_filename)
    if errors:
        print("\nParsing errors detected. Please fix your schedule file. Exiting.")
        return
    print(f"✓ Parsed {len(all_commitments)} event entries across {len(categories)} categories.")
    
    try:
        print("\n--- Configure Your Calendar ---")
        start_h_str = input(f"Enter start hour (e.g., 3) [3]: ") or "3"
        end_h_str = input(f"Enter end hour (e.g., 22) [22]: ") or "22"
        orient = input("Orientation (P/L) [L]: ").upper() or "L"
        start_hour, end_hour = int(start_h_str), int(end_h_str)
        figsize = (8.5, 11) if orient == 'P' else (11, 8.5)
    except ValueError:
        print("Invalid input. Please enter whole numbers for hours. Exiting.")
        return

    print("\n--- Generating Calendars ---")
    create_calendar_pdf(get_events_for_week(all_commitments, 'A'), "Week A", start_hour, end_hour, figsize)
    create_calendar_pdf(get_events_for_week(all_commitments, 'B'), "Week B", start_hour, end_hour, figsize)
    
    calculate_and_print_stats(all_commitments)
    print("\n--- All done. ---")

if __name__ == "__main__":
    main()