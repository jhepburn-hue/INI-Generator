"""Layer 2: one test per form-to-INI rule, using small hand-written forms.

These tests use made-up keysets, TCIs and customers, and the example profiles in
customer_profiles.example.json, so they run without any private data.
"""
import os

import pytest

import csv_parser
from csv_parser import CSN_FORMATS, Form, build_config, get_keyset_id, load_profiles
from prox_filter import build_prox_filter

EXAMPLE_PROFILES = os.path.join(os.path.dirname(__file__), "..", "customer_profiles.example.json")
FAKE_CONFIG_IDS = {"CXAA1": 206, "CXBB4": 170}


@pytest.fixture(autouse=True)
def example_data(monkeypatch):
    monkeypatch.setattr(csv_parser, "PROFILES", load_profiles(EXAMPLE_PROFILES))
    monkeypatch.setattr(csv_parser, "lookup_config_id", lambda name: FAKE_CONFIG_IDS.get(name.split("-")[0].upper()))


def make_rows(*rows):
    # make_rows(("Idle LED", "Red"), ("MFC CSN", "On", "CSN_32_BIT_MSB")) -> form rows with
    # the value in the third column, like the real config forms
    return [[label, "", *values] for label, *values in rows]


def generate(*rows):
    return build_config(make_rows(("Config Name", "CTEST"), ("Config ID", "1"), *rows))


def value(config, section, key):
    return config.values.get(section, {}).get(key)


def notes(text):
    return ("Custom / Application / Notes", text)


def credentials_with_custom_mobile(mobile_notes):
    return generate(("BLE Functionality", "Admin + Credentials"), ("Mobile Keyset", "Custom"), ("Mobile Notes", mobile_notes))


# Prox filter

@pytest.mark.parametrize("description, function, bit_len, mask, filter_value", [
    ("Ignore W36-8 with a facility code 15", "equal", "36", "0F80000000", "0780000000"),
    ("Ignore W35-0 cards with facility code 100", "equal", "35", "01FFE00000", "000C800000"),
    ("Ignore W35-0 with BID >= 500,000", "greater_or_equal", "35", "00001FFFFE", "00000F4240"),
    ("Ignore W37-0 with Facility Code 60,000", "equal", "37", "0FFFF00000", "0EA6000000"),
    ("Ignore W40-1 w/ FC 155,456", "equal", "40", "7FFFF00000", "25F4000000"),
    ("Ignore W37-1 with BID >= 700,000", "greater_or_equal", "37", "0FFFFFFFFE", "0000155CC0"),
    ("Ignore W37-1 with Badge ID >= 100,000 <= 524, 286", "greater_or_equal", "37", "00000FFFFE", "0000030D40"),
    ("Ignore all credentials of W37-4 with BID's greater than or equal to 90,000,000",
     "greater_or_equal", "37", "003FFFFFFE", "000ABA9500"),
    ("Filter 37-4, FC 11.", "equal", "37", "07C0000000", "02C0000000"),                       # no "W"
    ("Filter W35-0 BID ≥ 400,000", "greater_or_equal", "35", "00001FFFFE", "00000C3500"),     # "≥"
    ("Filter all 37-bit prox credentials", "greater_or_equal", "37", "1FFFFFFFFF", "0000000000"),
])
def test_prox_filter_descriptions(description, function, bit_len, mask, filter_value):
    settings, problem = build_prox_filter(description)
    assert problem is None
    assert settings == {
        "filter_enabled": "true",
        "filter_function": f'"{function}"',
        "filter_bit_len": bit_len,
        "filter_mask": f'"{mask}"',
        "filter_value": f'"{filter_value}"',
    }


@pytest.mark.parametrize("description", [
    "Filter all prox cards except for 40-bit and all 1's",  # exceptions cannot be one mask/value
    "Ignore W25-0 with FC 109",                             # format not in BIT_MAPS
    "KC1 of Lk19999",                                       # no format at all
    "Ignore W48-0 with FC 5",                               # longer than the 40-bit register
])
def test_prox_filter_problems_are_reported(description):
    settings, problem = build_prox_filter(description)
    assert settings is None and problem


def test_prox_filter_reads_multiline_label():
    config = generate(("Prox Filter", "On"), ("Prox\nFilter\nDescription", "Ignore W36-8 with a facility code 15"))
    assert value(config, "rfid/lf", "filter_enabled") == "true"


def test_prox_filter_off_writes_reference_defaults():
    config = generate(("Prox Filter", "Off"))
    assert value(config, "rfid/lf", "filter_function") == '"equal"'
    assert value(config, "rfid/lf", "filter_bit_len") == "40"
    assert value(config, "rfid/lf", "filter_value") == '"0000000000"'


# CSN

@pytest.mark.parametrize("dropdown, code", sorted(CSN_FORMATS.items()))
def test_csn_dropdown_values(dropdown, code):
    config = generate(("MFC CSN", "On", dropdown))
    assert value(config, "rfid/hf/app/csn", "mifare_classic_format") == code


def test_csn_blank_format_is_32_bit_msb():
    config = generate(("ISO14443A CSN", "On"))
    assert value(config, "rfid/hf/app/csn", "iso14443a_cl1_format") == "0x2001"


def test_csn_all_off_disables_csn():
    config = generate(*[(row, "Off") for row in ["MFC CSN", "EV1/EV2 CSN", "iClass CSN", "ISO15693 CSN", "ISO14443A CSN"]])
    assert value(config, "rfid/hf/app/csn", "enabled") == "false"
    assert value(config, "rfid/hf/app/csn", "pico15693_format") == "0xFFFF"
    assert value(config, "rfid/hf/nfc", "enabled_protocols") == '"A"'


def test_csn_off_rows_get_ffff():
    config = generate(("MFC CSN", "On", "CSN_32_BIT_MSB"), ("iClass CSN", "Off"))
    assert value(config, "rfid/hf/app/csn", "pico15693_format") == "0xFFFF"


def test_iclass_csn_adds_v_protocol():
    config = generate(("iClass CSN", "On"), ("MFC CSN", "Off"))
    assert value(config, "rfid/hf/nfc", "enabled_protocols") == '"AV"'


# Basic form fields

def test_av_and_feedback():
    config = generate(("Idle LED", "Amber"), ("Beeper", "Off"), ("Credential Report LED", "Off"))
    assert value(config, "av", "idle_color") == '"amber"'
    assert value(config, "av", "silence_beeper") == "true"
    assert value(config, "rfid/av", "led_enabled") == "false"
    assert value(config, "rfid/av", "color") == '"off"'


def test_unsupported_idle_color_warns():
    config = generate(("Idle LED", "Cyan"))
    assert value(config, "av", "idle_color") is None
    assert any("Cyan" in w for w in config.warnings)


@pytest.mark.parametrize("keypad, expected", [("4-bit", "4_bit"), ("buffered 26-bit", "26_bit"), ("Magstripe - 4 digit", "magstripe_4")])
def test_keypad_format(keypad, expected):
    assert value(generate(("Keypad Format", keypad)), "wiegand", "default_format") == f'"{expected}"'


def test_tamper_off():
    config = generate(("Tamper Monitoring", "Off"))
    assert value(config, "tamper", "osdp_reporting_enabled") == "false"


def test_wiegand_only_comment():
    config = generate(("Custom\nApplication\nNotes", "Customer is Wiegand only"))
    assert value(config, "host_communication", "mode") == '"wiegand"'


def test_casi_4001():
    assert value(generate(("Casi Output Format", "CASI-4001")), "rfid/lf", "ask_output_format") == '"casi_01"'


def test_lf_off_unless_prox_filter():
    assert value(generate(("FSK Prox", "Off"), ("ASK Prox", "Off")), "rfid/lf", "enabled") == "false"
    config = generate(("FSK Prox", "Off"), ("ASK Prox", "Off"), ("Prox Filter", "On"),
                      ("Prox / Filter / Description", "Ignore W36-8 with a facility code 15"))
    assert value(config, "rfid/lf", "enabled") is None


# Config ID

def test_config_id_from_form():
    config = build_config(make_rows(("Config Name", "CXAA1"), ("Config ID", "206.0")))
    assert value(config, "mfg_data", "cfg_id") == "0x00CE"


def test_config_id_from_lookup_when_blank():
    config = build_config(make_rows(("Config Name", "CXBB4-Lk59990"), ("Config ID", "")))
    assert value(config, "mfg_data", "cfg_id") == "0x00AA"


def test_blank_config_id_ignores_card_details_column():
    # "Config ID,,,,,,Bitstream" must not read "Bitstream" as the ID
    rows = [["Config Name", "CXBB4"], ["Config ID", "", "", "", "", "", "Bitstream"]]
    assert value(build_config(rows), "mfg_data", "cfg_id") == "0x00AA"


def test_unknown_config_id_warns():
    config = build_config(make_rows(("Config Name", "CXZZ9"), ("Config ID", "")))
    assert value(config, "mfg_data", "cfg_id") is None
    assert any("No Config ID" in w for w in config.warnings)


# BLE and MyPass

def test_ble_disabled():
    config = generate(("BLE Functionality", "Disabled"), ("BLE Advertising Config", "Standard"))
    assert value(config, "ble", "enabled") == "false"


def test_ble_stays_on_for_custom_advertising_name():
    config = generate(("BLE Functionality", "Disabled"), ("BLE Advertising Config", "Example (EXMP)"))
    assert value(config, "ble", "enabled") is None
    assert value(config, "ble/adv_data", "name_complete") == '"EXMP"'


@pytest.mark.parametrize("functionality", ["Admin + Credentials", "Admin + Custom Credential", "Admin + MyPass"])
def test_ble_credentials_enable_mypass(functionality):
    config = generate(("BLE Functionality", functionality))
    assert value(config, "mypass", "allow_credentials") == "true"
    assert value(config, "rfid/hf/app/mypass", "enabled") == "true"


@pytest.mark.parametrize("label", ["Legacy Credentials", "Legacy Credentials (any partner names)"])
def test_legacy_credentials(label):
    config = generate(("BLE Functionality", "Admin + Credentials"), (label, "On"))
    assert value(config, "ble/configure", "secure_transactions") == "false"
    assert value(config, "rfid/hf/app/mypass", "enabled") == "false"


def test_transport_keyset_and_all_keys():
    transport = generate(("BLE Functionality", "Admin + Credentials"), ("Mobile Keyset", "Example Transport"))
    assert value(transport, "keys", "slot13") == "Ck99999:KM2"
    assert value(transport, "mypass", "all_keys") == "true"

    admin_only = generate(("BLE Functionality", "Admin Only"), ("Mobile Keyset", "Example Transport"))
    assert value(admin_only, "keys", "slot13") is None
    assert value(admin_only, "mypass", "all_keys") == "false"


def test_transport_keyset_without_credentials():
    config = generate(("BLE Functionality", "Admin Only"), ("Mobile Keyset", "Zero Transport"))
    assert value(config, "keys", "slot03") == "GENERIC:ZEROS_KEY"


def test_custom_mobile_keyset_from_mobile_notes():
    config = credentials_with_custom_mobile("Custom mobile keys Mk59991")
    assert value(config, "keys", "slot13") == "Lk59991:Mkm"
    assert value(config, "keys", "slot14") == "Lk59991:Mkc"


# Keysets and LEAF

@pytest.mark.parametrize("cell, keyset", [("Lk19991", "Lk19991"), ("LMk59992", "Lk59992"), ("Mk59993", "Lk59993")])
def test_keyset_id_spellings(cell, keyset):
    assert get_keyset_id(Form(make_rows(("Keyset ID (LkXXXXX)", cell)))) == keyset


def test_keyset_id_from_notes_skips_manufacturer_keyset():
    form = Form(make_rows(notes("Kv1 of Lk00009, Kc1 of Lk59994")))
    assert get_keyset_id(form) == "Lk59994"


def test_leaf_si_and_cc():
    config = generate(("Custom Keyset (LEAF Cc)", "Enabled"), ("Keyset ID (LkXXXXX)", "Lk19991"),
                      ("Leaf Si Application (Kv1)", "Leaf Si"), ("Leaf Cc Application (Kc1)", "Leaf Cc"))
    assert value(config, "rfid/hf/app/leaf/desfire/1", "enabled") == "true"
    assert value(config, "rfid/hf/app/leaf/desfire/2", "enabled") == "true"
    assert value(config, "keys", "slot11") == "Lk19991:Kc8"


def test_leaf_cc_without_custom_keyset_uses_manufacturer_keyset():
    config = generate(("Leaf Application", "Leaf CC"))
    assert value(config, "keys", "slot11") == "Lk00009:Kc8"


def test_non_leaf_keyset_leaves_cc_off():
    config = generate(("Custom Keyset (LEAF Cc)", "Enabled"), ("Keyset ID (LkXXXXX)", "EXAMPLE_TEST"),
                      ("Leaf Cc Application (Kc1)", "Leaf Cc"))
    assert value(config, "rfid/hf/app/leaf/desfire/2", "enabled") is None
    assert any("EXAMPLE_TEST" in w for w in config.warnings)


def test_second_keyset_uses_desfire_3():
    config = generate(("Custom Keyset (LEAF Cc)", "Enabled"), ("Keyset ID (LkXXXXX)", "Lk19991"),
                      ("Leaf Cc Application (Kc1)", "Leaf Cc"),
                      ("Custom\nApplication\nNotes", "Example app\nLk19991 (site A)\nLk19992 (site B)"))
    assert value(config, "rfid/hf/app/leaf/desfire/3", "enabled") == "true"
    assert value(config, "rfid/hf/app/leaf/desfire/3", "se_key_nb") == "12"
    assert value(config, "keys", "slot12") == "Lk19992:Kc8"


def test_leaf_cc_always_uses_kc8_even_when_notes_say_kc1():
    # Forms say "Kc1 of LkXXXXX" for Kc8 customers too, so the notes are ignored
    config = generate(("Custom Keyset (LEAF Cc)", "Enabled"), ("Keyset ID (LkXXXXX)", "Lk59994"),
                      ("Leaf Cc Application (Kc1)", "Leaf Cc"), notes("Contains Kc1 of Lk59994"))
    assert value(config, "keys", "slot11") == "Lk59994:Kc8"
    assert value(config, "rfid/hf/app/leaf/desfire/2", "card_key_nb") == "8"


# Wallet

def test_wallet_with_custom_keyset():
    config = generate(("Custom Keyset (LEAF Cc)", "Enabled"), ("Keyset ID (LkXXXXX)", "Lk19991"),
                      ("ECP DESFire", "Enabled"), ("MiFare2Go", "Enabled"), ("ECP TCI", "0abc12"),
                      ("Apple Meridian Bit Count", "57"))
    assert value(config, "rfid/hf/app/meridian", "enabled") == "true"
    assert value(config, "rfid/hf/app/meridian", "bit_nb") == "57"
    assert value(config, "rfid/hf/app/meridian", "privacy_se_key_nb") == "15"
    assert value(config, "rfid/hf/app/wallet", "terminal_id") == '"0ABC12"'
    assert value(config, "keys", "slot15") == "Lk19991:Kr0"


def test_wallet_with_manufacturer_keyset_uses_slots_05_to_07():
    config = generate(("Custom Keyset (LEAF Cc)", "Disabled"), ("ECP DESFire", "Enabled"), ("MiFare2Go", "Enabled"))
    assert value(config, "rfid/hf/app/meridian", "privacy_se_key_nb") == "05"
    assert value(config, "rfid/hf/app/mifare_2go/generic", "se_key_nb") == "07"
    assert value(config, "keys", "slot15") is None


def test_wallet_without_tci_uses_default_tci():
    config = generate(("ECP DESFire", "Enabled"), ("ECP TCI", "1"))
    assert value(config, "rfid/hf/app/wallet", "terminal_id") == '"0ABCDE"'
    assert any("default TCI" in w for w in config.warnings)


def test_bit_count_placeholder_does_not_warn():
    config = generate(("ECP DESFire", "Disabled"), ("Apple Meridian Bit Count", "1"))
    assert not any("Bit Count" in w for w in config.warnings)


def test_nfc_functionality_contradiction_warns():
    config = generate(("NFC Functionality", "Disabled"), ("ECP DESFire", "Enabled"))
    assert any("NFC Functionality" in w for w in config.warnings)


# Apps found in the notes (keyword_apps in the profiles)

def test_iclass_needs_explicit_enable():
    assert value(generate(notes("iClass and ISO15693 reported as 56-bit output")), "rfid/hf/app/iclass", "enabled") is None
    assert value(generate(notes("iCLASS Enabled")), "rfid/hf/app/iclass", "enabled") == "true"


def test_keyword_app():
    config = generate(notes("Supplied with ExampleApp"))
    assert value(config, "rfid/hf/app/example", "se_key_nb") == "20"
    assert value(config, "keys", "slot20") == "EXAMPLE:KEY"


def test_keyword_app_whole_word_only():
    assert value(generate(notes("NotExampleApps here")), "rfid/hf/app/example", "enabled") is None


@pytest.mark.parametrize("text, classic, desfire", [
    ("MFC/MFD ExampleVariant", True, True),
    ("ExampleVariant DESFire", False, True),
    ("ExampleVariant Classic", True, False),
    ("ExampleVariant support added", True, True),
])
def test_keyword_app_variants(text, classic, desfire):
    config = generate(notes(text))
    assert (value(config, "rfid/hf/app/example/classic", "enabled") == "true") == classic
    assert (value(config, "rfid/hf/app/example/desfire", "enabled") == "true") == desfire


def test_keyword_app_variants_per_cell():
    # One cell names DESFire, another mentions the app generally: both variants
    config = generate(notes("ExampleVariant DESFire"), ("Notes/Other Products", "ExampleVariant support added"))
    assert value(config, "rfid/hf/app/example/classic", "enabled") == "true"
    assert value(config, "rfid/hf/app/example/desfire", "enabled") == "true"


@pytest.mark.parametrize("text", ["Manual App", "manualapp"])
def test_keyword_app_warning(text):
    config = generate(notes(text))
    assert value(config, "rfid/hf/app/example/manual", "enabled") == "true"
    assert any("slot30" in w for w in config.warnings)


def test_customer_profile_by_config_name():
    config = build_config(make_rows(("Config Name", "CEX9"), ("Keyset ID", "Lk59990")))
    assert value(config, "rfid/hf/app/nexpacs", "app_id") == '"ABCDEF"'
    assert value(config, "keys", "slot30") == "Lk59990:APPVK"


def test_customer_profile_needs_keyset_for_keyset_keys():
    config = build_config(make_rows(("Config Name", "CEX9")))
    assert value(config, "keys", "slot30") is None
    assert any("slot30" in w for w in config.warnings)


def test_nexpacs_mention_without_profile_warns():
    config = generate(notes("NexPacs smart card app supported"))
    assert any("no NexPacs profile" in w for w in config.warnings)


def test_wallet_override_by_config_name():
    config = build_config(make_rows(("Config Name", "CEXW9"), ("ECP DESFire", "Enabled"), ("MiFare2Go", "Enabled")))
    assert value(config, "rfid/hf/app/meridian", "enabled") == "false"
    assert value(config, "rfid/hf/app/wallet", "terminal_id") == '"0ABCDF"'
    assert value(config, "keys", "slot15") == "EXAMPLE_TEST:Kr0"
    assert value(config, "rfid/hf/app/nexpacs", "enabled") is None


def test_wallet_override_extra_when_mentioned():
    config = build_config(make_rows(("Config Name", "CEXW9"), ("ECP DESFire", "Enabled"), notes("NexPacs too")))
    assert value(config, "rfid/hf/app/nexpacs", "se_key_nb") == "19"
    assert value(config, "keys", "slot19") == "EXAMPLE_TEST:TEST"


def test_wallet_override_by_mention_but_not_in_excluded_context():
    assert value(generate(notes("ExampleWallet reader")), "rfid/hf/app/wallet", "terminal_id") == '"0ABCDF"'
    config = generate(notes("Keys kept for backwards compatbility with ExampleWallet"))
    assert value(config, "rfid/hf/app/meridian", "enabled") is None


def test_unknown_custom_app_warns():
    config = generate(("Other Custom HF Application", "Custom EV2"))
    assert any("customer-specific" in w for w in config.warnings)


def test_missing_profiles_disable_profile_rules(monkeypatch):
    monkeypatch.setattr(csv_parser, "PROFILES", load_profiles("/nonexistent/customer_profiles.json"))
    config = generate(notes("ExampleApp"), ("Mobile Keyset", "Example Transport"), ("BLE Functionality", "Admin + Credentials"))
    assert value(config, "rfid/hf/app/example", "enabled") is None
    assert value(config, "keys", "slot13") is None


# Mobile keys (the "keysets" block in the profiles)

def test_test_mobile_keyset():
    config = credentials_with_custom_mobile("NFC keys from MobileDemo")
    assert value(config, "keys", "slot13") == "MobileDemo:km"
    assert value(config, "keys", "slot14") == "MobileDemo:kc"


def test_older_keyset_mobile_keys_are_separate():
    # Keysets up to last_separate_mobile_keyset keep mobile keys in a separate MkXXXXX keyset
    config = credentials_with_custom_mobile("LMk00099")
    assert value(config, "keys", "slot13") == "Mk00099:Mkm"
    assert value(config, "keys", "slot14") == "Mk00099:Mkc"
    assert any("Verify on a reader" in w for w in config.warnings)


def test_newer_keyset_mobile_keys_are_combined():
    config = credentials_with_custom_mobile("Mk19996")
    assert value(config, "keys", "slot13") == "Lk19996:Mkm"
    assert not any("Verify on a reader" in w for w in config.warnings)


def test_bluetooth_key_pair_2_from_notes():
    # Pair 1 moves to MyPass keyset 1 (slots 03/04), pair 2 goes in keyset 2 (slots 13/14)
    config = credentials_with_custom_mobile("Mk59995, uses Mkm2/Mkc2")
    assert value(config, "keys", "slot03") == "Lk59995:Mkm"
    assert value(config, "keys", "slot04") == "Lk59995:Mkc"
    assert value(config, "keys", "slot13") == "Lk59995:Mkm2"
    assert value(config, "keys", "slot14") == "Lk59995:Mkc2"


def test_bluetooth_key_pair_1_by_default():
    config = credentials_with_custom_mobile("Mk59995")
    assert value(config, "keys", "slot03") is None
    assert value(config, "keys", "slot13") == "Lk59995:Mkm"
