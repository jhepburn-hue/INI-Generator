import csv
import io

def parse_csv_file(file_contents):
    """
    Parses uploaded CSV bytes/string into a list of cleaned row tuples.
    """
    if isinstance(file_contents, bytes):
        file_contents = file_contents.decode('utf-8', errors='ignore')
    
    reader = csv.reader(io.StringIO(file_contents))
    cleaned_rows = []
    
    for row in reader:
        cleaned_row = [cell.strip() for cell in row]
        if any(cleaned_row):
            cleaned_rows.append(cleaned_row)
            
    return cleaned_rows

def get_setting_value(rows, setting_label):
    """
    Searches rows for a target setting label and returns its associated value.
    Handles non-standard column layouts across different CSV formats.
    """
    target = setting_label.strip().lower()
    
    for row in rows:
        for idx, cell in enumerate(row):
            if cell.lower() == target:
                for next_cell in row[idx + 1:]:
                    if next_cell != "":
                        return next_cell
    return None

def get_av_section(rows):
    """
    Parses CSV rows and constructs the formatted [av] INI section string.
    """
    idle_led_raw = get_setting_value(rows, "Idle LED")
    beeper_raw = get_setting_value(rows, "Beeper")
    
    # Map Idle LED color to lowercased string (default "white")
    idle_color = idle_led_raw.lower() if idle_led_raw else "white"
    
    # Map Beeper: 'On' -> silence_beeper = false, 'Off' -> silence_beeper = true
    silence_beeper = "false"
    if beeper_raw and beeper_raw.lower() == "off":
        silence_beeper = "true"

    lines = [
        "[av]",
        f"silence_beeper = {silence_beeper}",
        "host_control_enabled = true",
        "host_control_exclusive = false",
        f'idle_color = "{idle_color}"',
        "red_intensity = 6",
        "green_intensity = 5",
        "blue_intensity = 5"
    ]
    
    return "\n".join(lines)


def generate_ini(rows):
    """
    Master function that calls each section function and joins them together.
    """
    sections = [
        get_av_section(rows),
    ]
    
    return "\n\n".join(sections)