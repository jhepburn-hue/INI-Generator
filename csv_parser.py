import csv
import io
import json
import os
import re

from config_ids import PRIVATE_DIR, lookup_config_id
from ini_checks import DEFAULT_INI_PATH, check_ini
from prox_filter import build_prox_filter

SUPPORTED_COLORS = ["off", "red", "green", "blue", "amber", "magenta", "white"]

KEYPAD_FORMATS = {
    "4-bit": "4_bit",
    "8-bit": "8_bit",
    "buffered 26-bit": "26_bit",
    "magstripe - 4 digit": "magstripe_4",
    "magstripe - 5 digit": "magstripe_5",
}

# Form dropdown value -> rfid/hf/app/csn format code
CSN_FORMATS = {
    "": "0x2001",  # CSN On with no format chosen defaults to 32-bit MSB
    "standard": "0x0000",
    "csn_26_bit": "0x1A00",
    "csn_32_bit_lsb": "0x2000",
    "32-bit lsb": "0x2000",
    "32 bit, reverse byte (rp40)": "0x2000",
    "csn_32_bit_msb": "0x2001",
    "32-bit msb": "0x2001",
    "32 bit": "0x2001",
    "standard ethos": "0x2001",
    "csn_32_bit_lsb_xor": "0x2003",
    "csn_32_bit_msb_xor": "0x2004",
    "csn_32_bit_plus": "0x2005",
    "csn_34_bit_msb_parity": "0x2200",
    "csn_40_bit_msb_lrc": "0x2801",
    "csn_40_bit_pcsc": "0x2801",
    "csn_56_bit": "0x3800",
    "56 bit, reverse byte (seos)": "0x3800",
    "csn_56_bit_msb": "0x3801",
    "csn_6400": "0x4000",
    "csn_75_bit_pcsc": "0x4B00",
}

# Form CSN row -> csn keys it controls
CSN_ROWS = {
    "MFC CSN": ["mifare_classic_format"],
    "EV1/EV2 CSN": ["mifare_desfire_format", "mifare_plus_format", "mifare_ultralight_format"],
    "iClass CSN": ["pico15693_format"],
    "ISO15693 CSN": ["iso15693_format"],
    "ISO14443A CSN": ["iso14443a_cl1_format", "iso14443a_cl2_format", "iso14443b_format", "felica_format"],
}

# Keys written as 0xFFFF when every CSN row is Off (matches the reference INIs)
CSN_DISABLED_KEYS = [
    "mifare_classic_format",
    "iso14443a_cl1_format",
    "iso14443a_cl2_format",
    "iso14443b_format",
    "iso15693_format",
    "pico15693_format",
]


FORM_LABELS = {
    "mfc csn",
    "ev1/ev2 csn",
    "iclass csn",
    "iso15693 csn",
    "iso14443a csn",
}

# Customer and partner specific settings live in private/customer_profiles.json, which is not
# committed. customer_profiles.example.json shows the format.
PROFILES_PATH = os.path.join(PRIVATE_DIR, "customer_profiles.json")
EMPTY_PROFILES = {
    "default_tci": None,
    "keysets": {},
    "ble_names": [],
    "mobile_keysets": {},
    "keyword_apps": [],
    "customer_profiles": [],
    "wallet_overrides": [],
}


def load_profiles(path=PROFILES_PATH):
    if not os.path.exists(path):
        return dict(EMPTY_PROFILES)
    with open(path) as f:
        return {**EMPTY_PROFILES, **json.load(f)}


PROFILES = load_profiles()


def keyset_setting(name, default=None):
    return PROFILES["keysets"].get(name, default)


def parse_csv_file(file_contents):
    if isinstance(file_contents, bytes):
        file_contents = file_contents.decode('utf-8-sig', errors='ignore')

    reader = csv.reader(io.StringIO(file_contents))
    cleaned_rows = []

    for row in reader:
        cleaned_row = [cell.strip() for cell in row]
        if any(cleaned_row):
            cleaned_rows.append(cleaned_row)

    return cleaned_rows


def load_defaults(path=DEFAULT_INI_PATH):
    # Returns {section: {key: value}} in file order, with comments stripped.
    defaults = {}
    section = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            match = re.match(r"\[(.+)\]$", line)
            if match:
                section = match.group(1)
                defaults[section] = {}
                continue

            if "=" in line and section:
                key, value = line.split("=", 1)
                defaults[section][key.strip()] = strip_inline_comment(value.strip())

    return defaults


def strip_inline_comment(value):
    if value.startswith('"'):
        end = value.find('"', 1)
        return value[:end + 1] if end != -1 else value
    return value.split(";", 1)[0].strip()


def quoted(value):
    return f'"{value}"'


def ini_bool(value):
    return "true" if value else "false"


def clean_number(value):
    # Spreadsheet exports turn 206 into "206.0" and 1000 into "1,000"
    if value is None:
        return None
    value = value.replace(",", "").strip()
    if re.fullmatch(r"\d+(\.0+)?", value):
        return int(float(value))
    return None


class Form:
    def __init__(self, rows):
        self.rows = rows

    def get(self, *labels, index=0):
        # Returns the first non-empty value after the label. Labels match a full cell,
        # case-insensitive. Rows with no value (section headers) are skipped, so
        # "Prox Filter" finds the On/Off row, not the heading above it.
        # Only the 4 cells after the label are read so the "Card Details" column
        # on the right side of the form is never picked up as a value.
        targets = [normalize_label(label) for label in labels]

        for row in self.rows:
            for idx, cell in enumerate(row):
                if normalize_label(cell) in targets:
                    values = [c for c in row[idx + 1:idx + 5] if c != ""]
                    if len(values) > index:
                        return values[index]
                    if values:
                        return ""
        return None

    def get_by_prefix(self, prefix):
        # For labels that vary between form versions, e.g. "Legacy Credentials (...)"
        prefix = normalize_label(prefix)
        for row in self.rows:
            for cell in row:
                label = normalize_label(cell)
                if label.startswith(prefix):
                    value = self.get(cell)
                    if value is not None:
                        return value
        return None

    def is_on(self, *labels):
        value = self.get(*labels)
        return value is not None and value.lower() in ("on", "yes", "enabled")

    def is_off(self, *labels):
        value = self.get(*labels)
        return value is not None and value.lower() in ("off", "no", "disabled")

    def text_cells(self):
        # Every cell except form labels, so "iClass CSN" does not count as mentioning iClass
        return [cell for row in self.rows for cell in row if normalize_label(cell) not in FORM_LABELS]

    def mentions(self, pattern):
        return any(re.search(pattern, cell, re.IGNORECASE) for cell in self.text_cells())

    def cells_mentioning(self, pattern):
        return [cell for cell in self.text_cells() if re.search(pattern, cell, re.IGNORECASE)]


def normalize_label(label):
    # Multi-line labels arrive as "Custom\nApplication\nNotes" in a CSV export, or as
    # "Custom / Application / Notes" in older tooling. Both become "custom application notes".
    label = re.sub(r"\s+/\s+", " ", label)
    return re.sub(r"\s+", " ", label).strip().lower()


class Config:
    def __init__(self):
        self.values = {}
        self.warnings = []

    def set(self, section, key, value):
        self.values.setdefault(section, {})[key] = value

    def warn(self, message):
        self.warnings.append(message)


def get_keyset_cell(form):
    return form.get("Keyset ID (LkXXXXX)", "Keyset ID (Lk#)", "Keyset ID") or ""


def get_keyset_id(form):
    value = get_keyset_cell(form)
    # "LMk5XXXX" is written for keyset Lk5XXXX
    match = re.search(r"\b(?:LM|L|M)k(\d{5})\b", value, re.IGNORECASE)
    if match:
        return "Lk" + match.group(1)

    # Older forms only mention the customer keyset in the notes. Skip the manufacturer keyset.
    notes = form.get("Custom / Application / Notes") or ""
    for keyset in re.findall(r"\bLk(\d{5})\b", notes, re.IGNORECASE):
        if "Lk" + keyset != keyset_setting("manufacturer_keyset"):
            return "Lk" + keyset
    return None


def set_mfg_data(form, config):
    config_name = form.get("Config Name")
    config_id = clean_number(form.get("Config ID"))

    if config_id is None and config_name:
        config_id = lookup_config_id(config_name)

    if config_id is None:
        config.warn(f"No Config ID for '{config_name}'. Add it to config_ids.csv. cfg_id left at default.")
        return

    config.set("mfg_data", "cfg_id", f"0x{config_id:04X}")


def set_av(form, config):
    idle_led = form.get("Idle LED")
    if idle_led:
        color = idle_led.lower()
        if color in SUPPORTED_COLORS:
            config.set("av", "idle_color", quoted(color))
        else:
            config.warn(f"Idle LED '{idle_led}' is not a supported color. idle_color left at default.")

    if form.is_off("Beeper"):
        config.set("av", "silence_beeper", "true")


def set_rfid_av(form, config):
    report_led = form.get("Credential Report LED")
    if not report_led:
        return

    color = report_led.lower()
    if color == "off":
        config.set("rfid/av", "led_enabled", "false")
        config.set("rfid/av", "color", quoted("off"))
    elif color in SUPPORTED_COLORS:
        config.set("rfid/av", "color", quoted(color))
    else:
        config.warn(f"Credential Report LED '{report_led}' is not a supported color.")


def set_wiegand(form, config):
    keypad_format = form.get("Keypad Format")
    if not keypad_format:
        return

    default_format = KEYPAD_FORMATS.get(keypad_format.lower())
    if default_format:
        config.set("wiegand", "default_format", quoted(default_format))
    else:
        config.warn(f"Keypad Format '{keypad_format}' not recognized.")


def set_host_communication(form, config):
    if form.mentions(r"wiegand[\s-]*only|only\s+wiegand"):
        config.set("host_communication", "mode", quoted("wiegand"))


def set_tamper(form, config):
    # The first "Tamper Monitoring" row is Wiegand/OSDP. The second one is F2F.
    if form.is_off("Tamper Monitoring"):
        config.set("tamper", "wiegand_reporting_enabled", "false")
        config.set("tamper", "osdp_reporting_enabled", "false")


def set_ble(form, config):
    ble_functionality = (form.get("BLE Functionality", "Mobile Functionality") or "").lower()
    ble_admin = form.get("BLE Admin")
    ble_credentials = (form.get("BLE Credentials") or "").lower()

    if ble_admin is not None:
        # Apex sheet layout
        disabled = ble_admin.lower() == "no" and ble_credentials in ("", "no")
        credentials = ble_credentials in ("yes", "mypass")
    else:
        disabled = ble_functionality == "disabled"
        credentials = any(s in ble_functionality for s in ("mypass", "admin + credentials", "custom credential"))

    # BLE Functionality covers Configure and MyPass. A custom advertising name
    # still needs BLE broadcasting, so BLE stays on for those.
    custom_name = set_ble_name(form, config)
    if disabled and not custom_name:
        config.set("ble", "enabled", "false")

    config.set("mypass", "km1_se_slot_nb", "03")
    config.set("mypass", "km2_se_slot_nb", "13")
    config.set("mypass", "kc1_se_slot_nb", "04")
    config.set("mypass", "kc2_se_slot_nb", "14")
    config.set("mypass", "allow_credentials", ini_bool(credentials))

    legacy_value = form.get_by_prefix("Legacy Credentials")
    legacy_credentials = (legacy_value or "").lower() in ("on", "yes", "enabled")
    if legacy_credentials:
        config.set("ble/configure", "secure_transactions", "false")
        config.set("ble/configure", "allow_credentials", "true")

    # Legacy credential configs leave the MyPass NFC application off
    config.set("rfid/hf/app/mypass", "enabled", ini_bool(credentials and not legacy_credentials))

    set_mobile_keyset(form, config, credentials)

    # all_keys enables MyPass keyset 1 and 2. Keyset 2 lives in keys slot13/slot14.
    keyset_2 = "slot13" in config.values.get("keys", {})
    config.set("mypass", "all_keys", ini_bool(keyset_2))


def set_ble_name(form, config):
    apex_name = form.get("BLE Advertising Name")
    adv_config = (form.get("BLE Advertising Config") or "").lower()

    name = None
    if apex_name:
        name = apex_name.upper()
    else:
        name = next((entry["name"] for entry in PROFILES["ble_names"] if re.search(entry["pattern"], adv_config)), None)

    if name and name != "APEX":
        if len(name) > 5:
            config.warn(f"BLE name '{name}' is longer than 5 characters.")
        config.set("ble/adv_data", "name_complete", quoted(name))
        return name
    return None


def set_mobile_keyset(form, config, credentials):
    mobile_keyset = (form.get("Mobile Keyset") or "").lower()

    # Transport keysets ("<Vendor> Transport") come from customer_profiles.json
    transport = PROFILES["mobile_keysets"].get(mobile_keyset)
    if transport:
        if credentials or not transport.get("requires_credentials", True):
            set_keys(config, transport.get("keys", {}), None)
    elif not credentials:
        return
    elif mobile_keyset == "custom":
        mobile_notes = form.get("Mobile Notes") or ""

        # Test mobile keysets have their own key names (customer_profiles.json)
        for test_keyset in keyset_setting("test_mobile_keysets", []):
            if re.search(test_keyset["pattern"], mobile_notes, re.IGNORECASE):
                set_keys(config, test_keyset["keys"], None)
                return

        # Mobile Notes like "Custom mobile Mk5XXXX" (or "LMk5XXXX") name the keyset.
        # Otherwise the custom mobile keys come from the form's LEAF keyset.
        match = re.search(r"\bL?Mk(\d{5})\b", mobile_notes, re.IGNORECASE)
        mobile_keyset_id = "Lk" + match.group(1) if match else get_keyset_id(form)

        if not mobile_keyset_id:
            config.warn("Mobile Keyset is 'Custom' but no Mk/Lk keyset was found. Set keys slot13/slot14 (Mkm/Mkc) manually.")
            return

        if int(mobile_keyset_id[2:]) <= keyset_setting("last_separate_mobile_keyset", -1):
            # Older keysets keep their mobile keys in a separate MkXXXXX keyset
            mobile_keyset_id = "Mk" + mobile_keyset_id[2:]
            config.warn(f"Mobile keys use the separate {mobile_keyset_id} keyset (older keyset). "
                        "No reference INI uses an Mk keyset yet. Verify on a reader.")

        # Bluetooth key pair 1 is written Mkm/Mkc. A customer on pair 2 (notes mention Mkm2/Mkc2)
        # gets pair 1 in MyPass keyset 1 (slots 03/04) and pair 2 in keyset 2 (slots 13/14).
        if re.search(r"\bmk[mc]2\b", mobile_notes, re.IGNORECASE):
            config.set("keys", "slot03", f"{mobile_keyset_id}:Mkm")
            config.set("keys", "slot04", f"{mobile_keyset_id}:Mkc")
            config.set("keys", "slot13", f"{mobile_keyset_id}:Mkm2")
            config.set("keys", "slot14", f"{mobile_keyset_id}:Mkc2")
        else:
            config.set("keys", "slot13", f"{mobile_keyset_id}:Mkm")
            config.set("keys", "slot14", f"{mobile_keyset_id}:Mkc")


def set_leaf(form, config, keyset_id):
    leaf_application = (form.get("Leaf Application") or "").lower()
    leaf_si = (form.get("Leaf Si Application (Kv1)") or "").lower() == "leaf si" or leaf_application == "leaf si"
    leaf_cc = (
        (form.get("Leaf Cc Application (Kc1)") or "").lower() == "leaf cc"
        or leaf_application == "leaf cc"
        or form.is_on("Custom Keyset (LEAF Cc)", "Custom Keyset")
    )

    keyset_cell = get_keyset_cell(form)
    if leaf_cc and keyset_cell and not keyset_id:
        # Some forms put a test keyset name here. That is not a LEAF keyset, so Cc cannot read.
        config.warn(f"Keyset ID '{keyset_cell}' is not a LEAF keyset (LkXXXXX). Leaf Cc left off.")
        leaf_cc = False

    if not (leaf_si or leaf_cc):
        return

    # Both LEAF slots are always defined. Only the enabled flag follows the form.
    config.set("rfid/hf/app/leaf/desfire", "enabled", "true")

    config.set("rfid/hf/app/leaf/desfire/1", "enabled", ini_bool(leaf_si))
    config.set("rfid/hf/app/leaf/desfire/1", "app_id", quoted("F51CD8"))
    config.set("rfid/hf/app/leaf/desfire/1", "card_key_nb", "2")
    config.set("rfid/hf/app/leaf/desfire/1", "se_key_nb", "2")

    config.set("rfid/hf/app/leaf/desfire/2", "enabled", ini_bool(leaf_cc))
    config.set("rfid/hf/app/leaf/desfire/2", "app_id", quoted("F51CDB"))
    config.set("rfid/hf/app/leaf/desfire/2", "card_key_nb", "8")
    config.set("rfid/hf/app/leaf/desfire/2", "se_key_nb", "11")

    if leaf_cc:
        if not keyset_id and not form.is_on("Custom Keyset (LEAF Cc)", "Custom Keyset"):
            # Without a custom keyset, Cc uses the manufacturer keyset
            keyset_id = keyset_setting("manufacturer_keyset")

        # Always Kc8 (108 of 113 references). Form notes say "Kc1 of LkXXXXX" on almost every form,
        # including Kc8 customers, so they cannot pick the key.
        if keyset_id:
            config.set("keys", "slot11", f"{keyset_id}:Kc8")
        else:
            config.warn("Leaf Cc is enabled but no Keyset ID (LkXXXXX) was found. Set keys slot11 manually.")

    # A second customer keyset in the notes (e.g. "Lk1XXXX (site A) / Lk1YYYY (site B)") reads
    # through desfire/3. se_key_nb is the keys slot that holds its Kc8.
    second_keyset = get_second_keyset_id(form, keyset_id)
    if leaf_cc and second_keyset:
        config.set("rfid/hf/app/leaf/desfire/3", "enabled", "true")
        config.set("rfid/hf/app/leaf/desfire/3", "app_id", quoted("F51CDB"))
        config.set("rfid/hf/app/leaf/desfire/3", "card_key_nb", "8")
        config.set("rfid/hf/app/leaf/desfire/3", "se_key_nb", "12")
        config.set("keys", "slot12", f"{second_keyset}:Kc8")


def get_second_keyset_id(form, keyset_id):
    notes = form.get("Custom / Application / Notes") or ""
    for keyset in re.findall(r"\bLk(\d{5})\b", notes, re.IGNORECASE):
        keyset = "Lk" + keyset
        if keyset not in (keyset_id, keyset_setting("manufacturer_keyset")):
            return keyset
    return None


def set_wallet(form, config, keyset_id):
    ecp_enabled = form.is_on("ECP DESFire", "ECP DESFire (Apple Wallet)")
    mifare_2go_enabled = form.is_on("MiFare2Go", "MiFare2Go (Android Wallet)")

    # NFC Functionality repeats what the ECP/MiFare2Go rows say. Only flag contradictions.
    nfc_functionality = (form.get("NFC Functionality") or "").lower()
    if nfc_functionality == "disabled" and (ecp_enabled or mifare_2go_enabled):
        config.warn("NFC Functionality is 'Disabled' but a wallet row is Enabled. Check the form.")
    elif nfc_functionality == "wallet" and not (ecp_enabled or mifare_2go_enabled):
        config.warn("NFC Functionality is 'Wallet' but both wallet rows are Disabled. Check the form.")

    # SE key numbers point at keys slots. Without a custom keyset the wallet uses the
    # manufacturer wallet keys already in slots 05-07 (Kr0/Kr1/Kr5). Otherwise slots 15-17.
    manufacturer_wallet = (ecp_enabled or mifare_2go_enabled) and form.is_off("Custom Keyset (LEAF Cc)", "Custom Keyset")
    first_slot = 5 if manufacturer_wallet else 15
    config.set("rfid/hf/app/meridian", "privacy_se_key_nb", f"{first_slot:02d}")
    config.set("rfid/hf/app/meridian", "credential_se_key_nb", f"{first_slot + 1:02d}")
    config.set("rfid/hf/app/mifare_2go/generic", "se_key_nb", f"{first_slot + 2:02d}")

    if ecp_enabled:
        config.set("rfid/hf/app/meridian", "enabled", "true")

        # A blank bit count keeps the default of 40. "1" is the placeholder forms use when wallet is disabled.
        raw_bit_count = form.get("Apple Meridian Bit Count")
        bit_count = clean_number(raw_bit_count)
        if bit_count in (32, 40, 57, 128):
            config.set("rfid/hf/app/meridian", "bit_nb", str(bit_count))
        elif raw_bit_count:
            config.warn(f"Apple Meridian Bit Count '{raw_bit_count}' is not valid. bit_nb left at 40.")

    if mifare_2go_enabled:
        config.set("rfid/hf/app/mifare_2go/generic", "enabled", "true")

    # Without a valid TCI on the form, use the default TCI from customer_profiles.json
    terminal_id = form.get("ECP TCI") or ""
    default_tci = PROFILES["default_tci"]
    if re.fullmatch(r"[0-9A-Fa-f]{6}", terminal_id):
        config.set("rfid/hf/app/wallet", "terminal_id", quoted(terminal_id.upper()))
    elif default_tci:
        config.set("rfid/hf/app/wallet", "terminal_id", quoted(default_tci))
        if ecp_enabled or mifare_2go_enabled:
            config.warn(f"Wallet is enabled but ECP TCI '{terminal_id}' is not 6 hex characters. Using default TCI {default_tci}.")
    elif ecp_enabled or mifare_2go_enabled:
        config.warn(f"Wallet is enabled but ECP TCI '{terminal_id}' is not 6 hex characters. Set terminal_id manually.")

    # A wallet override (see customer_profiles.json) brings its own wallet keys
    if not (ecp_enabled or mifare_2go_enabled) or manufacturer_wallet or find_wallet_override(form):
        return

    if keyset_id:
        config.set("keys", "slot15", f"{keyset_id}:Kr0")
        config.set("keys", "slot16", f"{keyset_id}:Kr1")
        config.set("keys", "slot17", f"{keyset_id}:Kr5")
    else:
        config.warn("Wallet is enabled but no Keyset ID was found. Set keys slot15-17 (Kr0/Kr1/Kr5) manually.")


def set_csn(form, config):
    rows = {label: form.get(label) for label in CSN_ROWS}
    rows_on = [label for label, value in rows.items() if value and value.lower() == "on"]

    if not rows_on:
        config.set("rfid/hf/app/csn", "enabled", "false")
        for key in CSN_DISABLED_KEYS:
            config.set("rfid/hf/app/csn", key, "0xFFFF")
        return rows_on

    for label, keys in CSN_ROWS.items():
        if label in rows_on:
            format_name = form.get(label, index=1) or ""
            csn_format = CSN_FORMATS.get(format_name.lower())
            if csn_format is None:
                config.warn(f"{label} format '{format_name}' has no known mapping. Left as-is (0x0000).")
                csn_format = "0x0000"
        else:
            csn_format = "0xFFFF"

        for key in keys:
            config.set("rfid/hf/app/csn", key, csn_format)

    return rows_on


def set_nfc_protocols(config, csn_rows_on):
    # A = ISO14443-A, B = ISO14443-B, F = FeliCa, V = ISO/PICO15693 (iClass).
    # All CSNs On keeps the default "ABFV".
    if len(csn_rows_on) == len(CSN_ROWS):
        return

    iclass_app = config.values.get("rfid/hf/app/iclass", {}).get("enabled") == "true"
    needs_v = iclass_app or "iClass CSN" in csn_rows_on or "ISO15693 CSN" in csn_rows_on
    config.set("rfid/hf/nfc", "enabled_protocols", quoted("AV" if needs_v else "A"))


def set_lf(form, config):
    prox_filter_on = form.is_on("Prox Filter")

    # ASK cannot be on without LF. Both off turns LF off, unless a prox filter still needs it.
    if form.is_off("FSK Prox") and form.is_off("ASK Prox") and not prox_filter_on:
        config.set("rfid/lf", "enabled", "false")

    casi_format = (form.get("Casi Output Format") or "").upper()
    if casi_format == "CASI-4001":
        config.set("rfid/lf", "ask_output_format", quoted("casi_01"))

    if prox_filter_on:
        description = form.get("Prox / Filter / Description", "Prox Filter Description")
        settings, problem = build_prox_filter(description)
        if problem:
            config.warn(f"Prox Filter is On but {problem}: '{description}'. Set rfid/lf filter_* values manually.")
        else:
            for key, value in settings.items():
                config.set("rfid/lf", key, value)
    else:
        # Disabled filter values used by the reference INIs
        config.set("rfid/lf", "filter_function", quoted("equal"))
        config.set("rfid/lf", "filter_bit_len", "40")
        config.set("rfid/lf", "filter_mask", quoted("0000000000"))
        config.set("rfid/lf", "filter_value", quoted("0000000000"))


def set_keys(config, keys, keyset_id):
    # keys values may contain {keyset}, filled with the form's LEAF keyset
    for slot, value in keys.items():
        if "{keyset}" in value and not keyset_id:
            config.warn(f"keys {slot} needs a Keyset ID ({value}). Set it manually.")
            continue
        config.set("keys", slot, value.format(keyset=keyset_id))


def apply_rule(config, rule, keyset_id):
    for section, settings in rule.get("settings", {}).items():
        for key, value in settings.items():
            config.set(section, key, value)
    set_keys(config, rule.get("keys", {}), keyset_id)
    if rule.get("warning"):
        config.warn(rule["warning"])


def apply_keyword_app(form, config, app, keyset_id):
    # Enables an app when the form text mentions it. With variants (e.g. classic / desfire), a
    # variant is used when the text mentions it, or when the text mentions none of the variants.
    cells = form.cells_mentioning(app["pattern"])
    if not cells:
        return False

    apply_rule(config, app, keyset_id)
    variants = app.get("variants", [])
    texts = cells if app.get("per_cell") else [" ".join(cells)]
    for text in texts:
        matched = [v for v in variants if re.search(v["pattern"], text, re.IGNORECASE)]
        for variant in matched or variants:
            apply_rule(config, variant, keyset_id)
    return True


def set_custom_hf(form, config, keyset_id):
    detected = []

    # Only an explicit "iClass enabled" / "enable iClass" / "iClass app", not CSN descriptions
    if form.mentions(r"enabl\w*\s+iclass|iclass\s+(app\w*\s+)?(is\s+)?enabl|iclass\s+(app|application|support)"):
        config.set("rfid/hf/app/iclass", "enabled", "true")
        config.set("rfid/hf/app/iclass", "auth_err_report_csn", "true")
        detected.append("iClass")

    for app in PROFILES["keyword_apps"]:
        if apply_keyword_app(form, config, app, keyset_id):
            detected.append(app["name"])

    profile = find_customer_profile(form)
    if profile:
        apply_rule(config, profile, keyset_id)
        detected.append(profile["name"])

    nexpacs_enabled = config.values.get("rfid/hf/app/nexpacs", {}).get("enabled") == "true"
    if form.mentions(r"nexpacs") and not nexpacs_enabled:
        config.warn("NexPacs is mentioned but this customer has no NexPacs profile. Configure [rfid/hf/app/nexpacs] manually.")

    other_hf = form.get("Other Custom HF Application")
    if other_hf and other_hf.lower() != "none":
        if detected:
            config.warn(f"Other Custom HF Application is '{other_hf}'. Detected {', '.join(detected)}. Check nothing else is needed.")
        else:
            config.warn(f"Other Custom HF Application is '{other_hf}' but no known app is mentioned. Likely a customer-specific app. Configure it manually.")


def find_customer_profile(form):
    # Customer profiles match the letters in the config name ("CXY4" -> "XY")
    match = re.match(r"C([A-Z]+)\d", (form.get("Config Name") or "").upper())
    if not match:
        return None
    return next((p for p in PROFILES["customer_profiles"] if p["config_prefix"] == match.group(1)), None)


def find_wallet_override(form):
    # A wallet override applies when the config name matches, or when the notes mention it outside
    # an excluded context (e.g. "backwards compatibility")
    config_name = (form.get("Config Name") or "").upper()
    for override in PROFILES["wallet_overrides"]:
        if re.search(override["config_name_pattern"], config_name):
            return override
        exclude = override.get("exclude_pattern")
        for cell in form.cells_mentioning(override["mention_pattern"]):
            if not exclude or not re.search(exclude, cell, re.IGNORECASE):
                return override
    return None


def set_wallet_override(form, config):
    # Some wallets replace the standard Apple/Google wallet apps with their own (customer_profiles.json)
    override = find_wallet_override(form)
    if not override:
        return

    apply_rule(config, override, None)
    for extra in override.get("if_mentioned", []):
        if form.mentions(extra["pattern"]):
            apply_rule(config, extra, None)


def build_config(rows):
    form = Form(rows)
    config = Config()
    keyset_id = get_keyset_id(form)

    set_mfg_data(form, config)
    set_av(form, config)
    set_rfid_av(form, config)
    set_wiegand(form, config)
    set_host_communication(form, config)
    set_tamper(form, config)
    set_ble(form, config)
    set_leaf(form, config, keyset_id)
    set_wallet(form, config, keyset_id)
    set_wallet_override(form, config)
    csn_rows_on = set_csn(form, config)
    set_lf(form, config)
    set_custom_hf(form, config, keyset_id)
    set_nfc_protocols(config, csn_rows_on)

    return config


def render_ini(defaults, overrides):
    # Writes only the keys that differ from settings_default.ini, in default file order.
    sections = []

    for section, default_values in defaults.items():
        changed = overrides.get(section, {})
        lines = [
            f"{key} = {changed[key]}"
            for key in default_values
            if key in changed and changed[key] != default_values[key]
        ]
        if lines:
            sections.append("\n".join([f"[{section}]"] + lines))

    for section in overrides:
        if section not in defaults:
            raise ValueError(f"Section [{section}] is not in settings_default.ini")
        unknown = set(overrides[section]) - set(defaults[section])
        if unknown:
            raise ValueError(f"Keys {sorted(unknown)} are not in [{section}] of settings_default.ini")

    return "\n\n".join(sections) + "\n"


def generate_ini(rows, defaults=None):
    if defaults is None:
        defaults = load_defaults()

    config = build_config(rows)
    if not os.path.exists(PROFILES_PATH):
        config.warn("private/customer_profiles.json is missing. Customer and partner apps were not generated.")
    ini_text = render_ini(defaults, config.values)
    warnings = config.warnings + [f"Check: {problem}" for problem in check_ini(defaults, config.values, keysets=PROFILES["keysets"])]
    return ini_text, warnings
