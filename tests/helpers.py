import os
import re

from csv_parser import DEFAULT_INI_PATH, generate_ini, load_defaults, parse_csv_file

# Fixtures hold customer data and are not committed. Build them with tools/build_test_fixtures.py,
# or point INI_FIXTURES_DIR at a folder that has forms/ and reference_ini/.
FIXTURES = os.environ.get("INI_FIXTURES_DIR", os.path.join(os.path.dirname(__file__), "fixtures"))
FORMS_DIR = os.path.join(FIXTURES, "forms")
REFERENCE_DIR = os.path.join(FIXTURES, "reference_ini")

DEFAULTS = load_defaults() if os.path.exists(DEFAULT_INI_PATH) else {}


def fixtures_available():
    return bool(DEFAULTS) and os.path.isdir(FORMS_DIR) and os.path.isdir(REFERENCE_DIR)


def form_names():
    if not os.path.isdir(FORMS_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(FORMS_DIR) if f.endswith(".csv"))


def reference_names():
    if not os.path.isdir(REFERENCE_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(REFERENCE_DIR) if f.endswith(".ini"))


def read_form(name):
    with open(os.path.join(FORMS_DIR, f"{name}.csv"), "rb") as f:
        return parse_csv_file(f.read())


def parse_ini(text):
    # {(section, key): value} with comments stripped
    values = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        header = re.match(r"\[(.+)\]$", line)
        if header:
            section = header.group(1)
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            value = value[:value.find('"', 1) + 1] if value.startswith('"') else value.split(";")[0].strip()
            values[(section, key.strip())] = value
    return values


def effective(values):
    # settings_default.ini with the INI's values applied
    merged = {(section, key): value for section, keys in DEFAULTS.items() for key, value in keys.items()}
    merged.update(values)
    return merged


def normalize(value):
    # "04" and "4" are the same number. Hex strings compare case-insensitively.
    if value and re.fullmatch(r"\d+", value):
        return str(int(value))
    return value.upper() if value else value


def is_noop(key, values):
    # True when the key has no effect, because the feature it belongs to is off
    section, name = key
    enabled = values.get((section, "enabled"))

    if name != "enabled" and enabled == "false":
        return True
    if section == "rfid/lf" and name.startswith("filter_") and name != "filter_enabled":
        return values.get(("rfid/lf", "filter_enabled")) == "false"
    if section == "rfid/hf/app/wallet":
        # Wallet apps are the sections with wallet SE keys (privacy key, or the MIFARE 2GO app)
        wallet_apps = {s for (s, k) in values if k == "privacy_se_key_nb" or s == "rfid/hf/app/mifare_2go/generic"}
        return all(values.get((app, "enabled")) == "false" for app in wallet_apps)
    if section == "mypass" and name.endswith("_se_slot_nb"):
        return values.get(("mypass", "allow_credentials")) == "false"
    return False


def compare_with_reference(name):
    # Returns ({(section, key): (generated, reference)}, warnings) for keys that differ in a way the
    # reader would notice
    generated_text, warnings = generate_ini(read_form(name))
    with open(os.path.join(REFERENCE_DIR, f"{name}.ini")) as f:
        reference_text = f.read()

    generated = effective(parse_ini(generated_text))
    reference = effective(parse_ini(reference_text))

    differences = {}
    for key in set(generated) | set(reference):
        if normalize(generated.get(key)) == normalize(reference.get(key)):
            continue
        if is_noop(key, generated) and is_noop(key, reference):
            continue
        differences[key] = (generated.get(key), reference.get(key))
    return differences, warnings
