import csv
import os
import re
import sys

# Company data that is never committed (see .gitignore)
PRIVATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private")
CONFIG_IDS_PATH = os.path.join(PRIVATE_DIR, "config_ids.csv")


def normalize_config_name(name):
    # "CXY4-Lk5XXXX" -> "CXY4", "cxy1 (note)" -> "CXY1"
    match = re.match(r"\s*([A-Za-z0-9_]+)", name or "")
    return match.group(1).upper() if match else ""


def load_config_ids(path=CONFIG_IDS_PATH):
    config_ids = {}
    if not os.path.exists(path):
        return config_ids

    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            config_ids[normalize_config_name(row["config_name"])] = int(row["config_id"])

    return config_ids


def lookup_config_id(config_name, config_ids=None):
    if config_ids is None:
        config_ids = load_config_ids()
    return config_ids.get(normalize_config_name(config_name))


def import_report(report_path, csv_path=CONFIG_IDS_PATH):
    # Converts a "CONFIGURATIONS REPORT" text export into config_ids.csv.
    # Names like "CXY1/CXY3" or "CXY2 OR CXZ1 for demo kits" become one row per name.
    rows = []
    with open(report_path) as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3 or not parts[1].isdigit():
                continue

            raw_name, dec_id = parts[0], int(parts[1])
            raw_name = re.sub(r"\(.*?\)", "", raw_name)
            for name in re.split(r"/|\bOR\b", raw_name):
                name = normalize_config_name(name)
                if name:
                    rows.append((name, dec_id))

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["config_name", "config_id"])
        writer.writerows(sorted(set(rows)))

    return len(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python config_ids.py <config_ids_report.txt>")
        sys.exit(1)
    print(f"Imported {import_report(sys.argv[1])} config names into {CONFIG_IDS_PATH}")
