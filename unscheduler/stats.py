# unscheduler/stats.py
from datetime import datetime
from .constants import DAY_CODES, DAY_NAME_MAP

def check_for_overlaps(all_commitments: list):
    """Checks for and prints informational warnings about overlapping time blocks."""
    print("\n--- Checking for overlaps ---")
    found_overlap = False
    for day_code in DAY_CODES:
        daily_blocks = sorted([e for e in all_commitments if e['type'] == 'block' and e['day_code'] == day_code], key=lambda x: x['start'])
        if len(daily_blocks) < 2:
            continue
        for i in range(1, len(daily_blocks)):
            prev_event = daily_blocks[i-1]
            curr_event = daily_blocks[i]
            if curr_event['start'] < prev_event['end']:
                found_overlap = True
                day_name = DAY_NAME_MAP.get(day_code, 'Unknown Day')
                print(f"  Warning: Overlap on {day_name} -> '{prev_event['event']}' ({prev_event['start']}-{prev_event['end']}) and '{curr_event['event']}' ({curr_event['start']}-{curr_event['end']})")
    if not found_overlap:
        print("  No overlaps found.")

def calculate_and_print_stats(all_commitments: list, all_categories: set, non_work_categories: list):
    """Calculates and prints the final, unified time allocation report."""
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
    work_categories = sorted(list(all_categories - set(non_work_categories)))
    print(f"NON-WORK Categories: {', '.join(non_work_categories) if non_work_categories else 'None defined'}")
    print(f"WORK Categories:     {', '.join(work_categories) if work_categories else 'None defined'}")
    print("-" * 52)
    
    total_scheduled = sum(category_hours.values())
    total_hours = 2 * 7 * 24
    category_hours['Unscheduled'] = total_hours - total_scheduled
    
    print(f"{'Category':<15} | {'Avg. Hours/Wk':<15} | {'Avg. Hours/Day':<15}")
    print("-" * 52)
    
    sorted_categories = sorted(category_hours.items(), key=lambda item: item[1], reverse=True)
    
    for cat, total_hrs in sorted_categories:
        print(f"{cat:<15} | {(total_hrs / 2):<15.1f} | {(total_hrs / 14):<15.1f}")

    total_work_hours = sum(category_hours.get(cat, 0) for cat in work_categories)
    total_available_hours = total_work_hours + category_hours.get('Unscheduled', 0)
    avg_available_wk = total_available_hours / 2
    avg_available_day = total_available_hours / 14
    
    print("-" * 52)
    print(f"{'Work+Unscheduled':<15} | {avg_available_wk:<15.1f} | {avg_available_day:<15.1f}")