# unscheduler/parser.py
import re
from dateutil.parser import parse
from .constants import DAY_CODES, COLOR_PALETTE, DEFAULT_TRIGGER_COLOR

# --- ColorAssigner class is unchanged ---
class ColorAssigner:
    """Manages color assignments for categories."""
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

def _parse_content(file_stream) -> (list, set, list, bool):
    """Internal parsing function that works on any file-like object."""
    commitments, categories_found, parsing_errors_found = [], set(), False
    non_work_categories = []
    color_assigner = ColorAssigner(COLOR_PALETTE)
    current_category = None
    in_non_work_section = False

    for i, line in enumerate(file_stream, 1):
        line = line.strip()
        if not line or line.startswith('#'): continue

        if line.strip().lower() == '[non-work-definition]':
            in_non_work_section = True
            continue

        if line.startswith('@'):
            in_non_work_section = False
            parts = line[1:].split(':', 1)
            category_name = parts[0].strip()
            current_category = category_name
            categories_found.add(category_name)
            if len(parts) > 1:
                color_assigner.define_color(category_name, parts[1].strip())
            continue

        if in_non_work_section:
            key, value = line.split('=', 1)
            if key.strip() == 'non_work_categories':
                non_work_categories = [cat.strip() for cat in value.split(',')]
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
            try: parse(words[3]); is_trigger = False
            except (ValueError, IndexError): is_trigger = True

            recurrence, day_str = words[0], words[1].upper()
            for day_char in day_str:
                if day_char not in DAY_CODES: continue
                
                event_base = {"recurrence": recurrence, "day_code": day_char}
                if is_trigger:
                    event = {**event_base, "type": "trigger", "time": parse(words[2]).strftime('%H:%M'), "event": ' '.join(words[3:])}
                    if inline_category: event["category"], event["color"] = inline_category, color_assigner.get_color(inline_category)
                    else: event["category"], event["color"] = None, DEFAULT_TRIGGER_COLOR
                else:
                    start_time, end_time = parse(words[2]).time(), parse(words[3]).time()
                    event_category = inline_category or current_category
                    if event_category: categories_found.add(event_category)
                    event = {**event_base, "type": "block", "start": start_time.strftime('%H:%M'), "end": end_time.strftime('%H:%M'), "event": ' '.join(words[4:]), "category": event_category, "color": color_assigner.get_color(event_category) if event_category else 'gray', "spans_midnight": end_time < start_time}
                commitments.append(event)
        except Exception as e:
            print(f"Error on line {i}: '{line}' -> {e}")
            parsing_errors_found = True
    return commitments, categories_found, non_work_categories, parsing_errors_found

def parse_schedule_file(filename: str):
    """Public function to parse a schedule from a file on disk."""
    with open(filename, 'r') as f:
        return _parse_content(f)

def get_events_for_week(all_commitments: list, week_type: str) -> list:
    """Filters the master commitment list for a specific week type ('A' or 'B')."""
    return [c for c in all_commitments if c["recurrence"] == "Weekly" or (c["recurrence"] == f"Week{week_type}")]