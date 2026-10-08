"""Layer 3: consistency checks on generated INIs. These need no reference INI."""
import os
import re

import pytest

from csv_parser import DEFAULT_INI_PATH, build_config, generate_ini, load_defaults
from helpers import form_names, read_form
from ini_checks import check_ini, check_key_slots, check_value, effective_values, load_allowed_values

# The checks read settings_default.ini, which is private company data
pytestmark = pytest.mark.skipif(not os.path.exists(DEFAULT_INI_PATH), reason="Needs private/settings_default.ini.")

DEFAULTS = load_defaults() if os.path.exists(DEFAULT_INI_PATH) else {}
ALLOWED = load_allowed_values() if os.path.exists(DEFAULT_INI_PATH) else {}

# A keyword app that leaves its key for the user to fill in. The generator warns about it.
MANUAL_KEY_PROBLEM = re.compile(r"se_key_nb = \d+: keys slot\d+ is empty")


@pytest.mark.parametrize("name", form_names())
def test_generated_ini_passes_checks(name):
    config = build_config(read_form(name))
    problems = check_ini(DEFAULTS, config.values, ALLOWED)
    unexplained = [p for p in problems if not (MANUAL_KEY_PROBLEM.search(p) and any("manually" in w for w in config.warnings))]
    assert unexplained == []


@pytest.mark.parametrize("name", form_names())
def test_generate_ini_runs(name):
    ini_text, warnings = generate_ini(read_form(name))
    assert ini_text.strip(), f"{name} produced an empty INI"
    assert all(isinstance(w, str) for w in warnings)


def test_default_ini_passes_its_own_checks():
    assert check_ini(DEFAULTS, DEFAULTS, ALLOWED) == []


def test_allowed_values_come_from_default_ini_comments():
    assert '"amber"' in ALLOWED[("av", "idle_color")]
    assert '"auto_detect"' in ALLOWED[("host_communication", "mode")]
    assert "106" in ALLOWED[("rfid/hf/nfc", "baudrate")]
    assert ALLOWED[("wiegand", "green_ctrl_mode")] == ALLOWED[("wiegand", "red_ctrl_mode")]


@pytest.mark.parametrize("section, key, value", [
    ("av", "idle_color", '"cyan"'),
    ("av", "silence_beeper", "True"),
    ("av", "red_intensity", "7"),
    ("ble/adv_data", "name_complete", '"ABCDEF"'),
    ("rfid/hf/app/wallet", "terminal_id", '"02090"'),
    ("rfid/lf", "filter_mask", '"0F8000000"'),
    ("rfid/hf/nfc", "enabled_protocols", '"AX"'),
    ("rfid/hf/app/csn", "mifare_classic_format", "2001"),
    ("wiegand", "default_format", '"9_bit"'),
    ("keys", "slot11", "Lk19991"),
])
def test_bad_values_are_flagged(section, key, value):
    assert check_value(section, key, value, DEFAULTS[section][key], ALLOWED)


def test_se_key_pointing_at_empty_slot_is_flagged():
    overrides = {"rfid/hf/app/leaf/desfire/4": {"enabled": "true", "se_key_nb": "20"}}
    problems = check_key_slots(effective_values(DEFAULTS, overrides))
    assert problems == ['[rfid/hf/app/leaf/desfire/4] se_key_nb = 20: keys slot20 is empty ("N/A")']


def test_se_key_of_disabled_app_is_ignored():
    overrides = {"rfid/hf/app/leaf/desfire/4": {"enabled": "false", "se_key_nb": "20"}}
    assert check_key_slots(effective_values(DEFAULTS, overrides)) == []


def test_mypass_keyset_2_checked_only_with_all_keys():
    overrides = {"mypass": {"allow_credentials": "true", "all_keys": "false", "km1_se_slot_nb": "03",
                            "kc1_se_slot_nb": "04", "km2_se_slot_nb": "13", "kc2_se_slot_nb": "14"}}
    assert check_key_slots(effective_values(DEFAULTS, overrides)) == []

    overrides["mypass"]["all_keys"] = "true"
    assert len(check_key_slots(effective_values(DEFAULTS, overrides))) == 2


def test_card_key_must_match_key_number():
    from ini_checks import check_leaf_card_keys
    overrides = {"rfid/hf/app/leaf/desfire/2": {"enabled": "true", "card_key_nb": "8", "se_key_nb": "11"},
                 "keys": {"slot11": "Lk19991:Kc1"}}
    problems = check_leaf_card_keys(effective_values(DEFAULTS, overrides))
    assert problems == ["[rfid/hf/app/leaf/desfire/2] card_key_nb = 8 but its key slot holds Lk19991:Kc1"]

    overrides["keys"]["slot11"] = "Lk19991:Kc8"
    assert check_leaf_card_keys(effective_values(DEFAULTS, overrides)) == []


def test_unknown_keyset_family_is_flagged():
    from ini_checks import check_keyset_families
    families = ["1", "5"]
    problems = check_keyset_families({"keys": {"slot11": "Lk39991:Kc8"}}, families)
    assert problems == ["[keys] slot11 = Lk39991:Kc8: Lk3XXXX is not a known keyset family"]
    assert check_keyset_families({"keys": {"slot11": "Lk59990:Kc8"}}, families) == []
    assert check_keyset_families({"keys": {"slot01": "Lk00009:Kaw"}}, families, manufacturer_keyset="Lk00009") == []
