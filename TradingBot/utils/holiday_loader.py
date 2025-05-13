import datetime
import os

def load_holidays(file_path='config/holidays.txt'):
    holidays = set()
    
    if not os.path.exists(file_path):
        print(f"Holiday file not found at {file_path}")
        return holidays

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                try:
                    holiday_date = datetime.datetime.strptime(line, "%Y-%m-%d").date()
                    holidays.add(holiday_date)
                except ValueError:
                    print(f"Invalid date format in holidays.txt: '{line}' (expected YYYY-MM-DD)")

    return holidays
