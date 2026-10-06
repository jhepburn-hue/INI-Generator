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