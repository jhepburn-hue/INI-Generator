import os
import re

DEFAULT_INI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private", "settings_default.ini")

# Options listed in settings_default.ini comments apply to the next key only. These keys share
# the list of the key above them.
SHARED_OPTIONS = {
    ("wiegand", "green_ctrl_mode"): ("wiegand", "red_ctrl_mode"),
    ("wiegand", "buzzer_ctrl_mode"): ("wiegand", "red_ctrl_mode"),
}

# Integer ranges taken from the settings_default.ini comments
RANGES = {
    ("av", "red_intensity"): (0, 6),
    ("av", "green_intensity"): (0, 5),
    ("av", "blue_intensity"): (0, 5),
    ("card_tracker", "max_cards"): (1, 15),
    ("rfid/lf", "filter_bit_len"): (1, 50),
    ("rfid/hf/app/leaf/desfire/1", "card_key_nb"): (0, 13),
    ("rfid/hf/app/leaf/desfire/2", "card_key_nb"): (0, 13),
    ("rfid/hf/app/leaf/desfire/3", "card_key_nb"): (0, 13),
    ("rfid/hf/app/leaf/desfire/4", "card_key_nb"): (0, 13),
    ("rfid/hf/app/meridian", "bit_nb"): (1, 128),
    ("rfid/hf/app/pkoc", "transaction_id_len"): (16, 65),
    ("wiegand", "default_facility_code"): (0, 255),
}


def load_allowed_values(path=DEFAULT_INI_PATH):
    # Reads the "; - "value"" option lists that settings_default.ini puts above a key.
    allowed = {}
    section = None
    options = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            header = re.match(r"\[(.+)\]$", line)
            if header:
                section = header.group(1)
                options = []
                continue

            option = re.match(r'^; - ("[^"]*"|\d+)\s*$', line)
            if option:
                options.append(option.group(1))
                continue

            if "=" in line and not line.startswith(";"):
                key = line.split("=", 1)[0].strip()
                if options:
                    allowed[(section, key)] = options
                options = []

    for key, source in SHARED_OPTIONS.items():
        if source in allowed:
            allowed[key] = allowed[source]
    return allowed


def effective_values(defaults, overrides):
    values = {section: dict(keys) for section, keys in defaults.items()}
    for section, keys in overrides.items():
        values.setdefault(section, {}).update(keys)
    return values


def check_value(section, key, value, default, allowed):
    where = f"[{section}] {key} = {value}"

    if section == "keys":
        if value != '"N/A"' and not re.fullmatch(r"[\w.-]+:[\w.-]+", value):
            return f"{where}: key slots must be \"N/A\" or KEYSET:KEY"
        return None

    if default in ("true", "false") and value not in ("true", "false"):
        return f"{where}: must be true or false"
    if default.startswith('"') and not (value.startswith('"') and value.endswith('"') and len(value) >= 2):
        return f"{where}: must be a quoted string"
    if default.lower().startswith("0x") and not re.fullmatch(r"0x[0-9A-Fa-f]+", value):
        return f"{where}: must be a hex number like 0x2001"
    if re.fullmatch(r"-?\d+", default) and not re.fullmatch(r"-?\d+", value):
        return f"{where}: must be a whole number"

    if (section, key) in allowed and value not in allowed[(section, key)]:
        return f"{where}: must be one of {', '.join(allowed[(section, key)])}"

    # A quoted hex default ("000000", "0000000000") fixes the length of its hex value
    if re.fullmatch(r'"[0-9A-Fa-f]{4,}"', default):
        length = len(default) - 2
        if not re.fullmatch(rf'"[0-9A-Fa-f]{{{length}}}"', value):
            return f"{where}: must be {length} hex characters"

    if (section, key) in RANGES:
        low, high = RANGES[(section, key)]
        if not low <= int(value) <= high:
            return f"{where}: must be between {low} and {high}"

    if (section, key) == ("rfid/hf/nfc", "enabled_protocols"):
        letters = value.strip('"')
        if not letters or set(letters) - set("ABFV"):
            return f"{where}: must use only the letters A, B, F and V"

    if (section, key) == ("ble/adv_data", "name_complete") and len(value.strip('"')) > 5:
        return f"{where}: BLE name is limited to 5 characters"

    return None


def is_active(section, values):
    # mypass has no "enabled" key. Its SE key slots matter when MyPass credentials are allowed.
    if section == "mypass":
        return values[section].get("allow_credentials") == "true"
    return values[section].get("enabled", "true") == "true"


def check_key_slots(values):
    # Every SE key number of an enabled application is a keys slot. That slot must hold a key.
    problems = []
    for section, keys in values.items():
        if section == "keys" or not is_active(section, values):
            continue
        for key, value in keys.items():
            if not re.search(r"se_(key|slot)_nb$", key) or not re.fullmatch(r"\d+", value):
                continue
            # MyPass keyset 2 (km2/kc2) is only used when all_keys is on
            if section == "mypass" and key[:2] in ("km", "kc") and key[2] == "2" and keys.get("all_keys") != "true":
                continue
            slot = f"slot{int(value):02d}"
            slot_value = values["keys"].get(slot)
            if slot_value is None:
                problems.append(f"[{section}] {key} = {value}: there is no keys {slot}")
            elif slot_value == '"N/A"':
                problems.append(f"[{section}] {key} = {value}: keys {slot} is empty (\"N/A\")")
    return problems


def check_leaf_card_keys(values):
    # A LEAF app reads the card key whose number matches card_key_nb: Kc8 -> 8, Kc1 -> 1, Kv2 -> 2
    problems = []
    for section, keys in values.items():
        if not re.fullmatch(r"rfid/hf/app/leaf/desfire/\d", section) or keys.get("enabled") != "true":
            continue
        slot_value = values["keys"].get(f"slot{int(keys['se_key_nb']):02d}", "")
        key_number = re.search(r":K[cv](\d+)$", slot_value)
        if key_number and key_number.group(1) != keys["card_key_nb"]:
            problems.append(f"[{section}] card_key_nb = {keys['card_key_nb']} but its key slot holds {slot_value}")
    return problems


def check_keyset_families(values, families, manufacturer_keyset=None):
    # families: first digits of valid LkXXXXX keysets (customer_profiles.json "keysets")
    problems = []
    for slot, slot_value in values["keys"].items():
        keyset = re.match(r"Lk(\d)(\d{4}):", slot_value)
        if keyset and keyset.group(1) not in families and slot_value.split(":")[0] != manufacturer_keyset:
            problems.append(f"[keys] {slot} = {slot_value}: Lk{keyset.group(1)}XXXX is not a known keyset family")
    return problems


def check_ini(defaults, overrides, allowed=None, keysets=None):
    # Returns a list of problems with the INI that settings_default.ini + overrides produce.
    if allowed is None:
        allowed = load_allowed_values()

    problems = []
    for section, keys in overrides.items():
        for key, value in keys.items():
            default = defaults.get(section, {}).get(key)
            if default is None:
                problems.append(f"[{section}] {key} is not in settings_default.ini")
                continue
            problem = check_value(section, key, value, default, allowed)
            if problem:
                problems.append(problem)

    values = effective_values(defaults, overrides)
    problems.extend(check_key_slots(values))
    problems.extend(check_leaf_card_keys(values))
    if keysets and keysets.get("families"):
        problems.extend(check_keyset_families(values, keysets["families"], keysets.get("manufacturer_keyset")))
    return problems
