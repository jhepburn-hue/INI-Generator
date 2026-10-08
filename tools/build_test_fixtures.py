"""Builds the test fixtures from the config workbooks and the reference INIs.

Usage:
    python tools/build_test_fixtures.py <workbook_dir> <reference_ini_dir>

Each "<anything> - NAME.xlsx" workbook becomes tests/fixtures/forms/NAME.csv. The Apex tab is
exported when its Config Name matches NAME, otherwise the Options tab (some Apex tabs are stale
copies of another config). Reference INIs with a matching form are copied to
tests/fixtures/reference_ini/NAME.ini.
"""
import csv
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config_ids import normalize_config_name  # noqa: E402

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
FIXTURES = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")


def column_index(cell_ref):
    letters = re.match(r"[A-Z]+", cell_ref).group()
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_workbook(path):
    # Returns {sheet name: [[cell, ...], ...]} using only the standard library
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))

        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.get("Id"): rel.get("Target") for rel in rels}

        sheets = {}
        for sheet in workbook.find("m:sheets", NS):
            target = targets[sheet.get(f"{{{NS['r']}}}id")].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target

            rows = []
            for row in ET.fromstring(z.read(target)).iter(f"{{{NS['m']}}}row"):
                cells = {}
                for c in row.findall("m:c", NS):
                    v = c.find("m:v", NS)
                    kind = c.get("t")
                    if kind == "s" and v is not None:
                        value = shared[int(v.text)]
                    elif kind == "inlineStr":
                        value = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
                    else:
                        value = v.text if v is not None else ""
                    cells[column_index(c.get("r"))] = (value or "").strip()
                if any(cells.values()):
                    rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
            sheets[sheet.get("name").strip()] = rows
        return sheets


def config_name_in_sheet(rows):
    for row in rows:
        if row and row[0].strip().lower() == "config name":
            return next((c for c in row[1:5] if c), "")
    return ""


def pick_sheet(sheets, name):
    apex = next((rows for sheet_name, rows in sheets.items() if sheet_name.lower() == "apex"), None)
    if apex and normalize_config_name(config_name_in_sheet(apex)) == normalize_config_name(name):
        return apex
    # Fall back to the Apex tab only when there is no Options tab (its Config Name may have a typo)
    return sheets.get("Options") or apex


def main(workbook_dir, reference_dir):
    forms_dir = os.path.join(FIXTURES, "forms")
    reference_out = os.path.join(FIXTURES, "reference_ini")
    os.makedirs(forms_dir, exist_ok=True)
    os.makedirs(reference_out, exist_ok=True)

    forms = references = 0
    seen = set()
    for filename in sorted(os.listdir(workbook_dir)):
        if not filename.endswith(".xlsx"):
            continue
        name = filename[:-5].split(" - ")[-1].strip()
        if name in seen:
            # e.g. "CXY6 - CXY3.xlsx" can be a copy of the CXY3 form
            print(f"skip {filename}: another workbook already exported {name}")
            continue
        seen.add(name)
        rows = pick_sheet(read_workbook(os.path.join(workbook_dir, filename)), name)
        if not rows:
            print(f"skip {filename}: no Options or matching Apex tab")
            continue

        with open(os.path.join(forms_dir, f"{name}.csv"), "w", newline="") as f:
            csv.writer(f).writerows(rows)
        forms += 1

        reference = os.path.join(reference_dir, f"{name}.ini")
        if os.path.exists(reference):
            shutil.copyfile(reference, os.path.join(reference_out, f"{name}.ini"))
            references += 1

    print(f"Wrote {forms} forms and {references} reference INIs to {os.path.normpath(FIXTURES)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
