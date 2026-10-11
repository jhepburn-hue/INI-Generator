# INI Generator

A small Flask app that turns a reader configuration form (exported as CSV) into an INI settings file.

Upload the CSV and the app shows the generated INI. You can copy it or download it as `<form name>.ini`. Anything the form cannot settle on its own is listed under **Needs Manual Review**.

## How it works

- The generator starts from `settings_default.ini` and applies the values the form asks for.
- The output lists only the keys that differ from the defaults, in the same order as `settings_default.ini`.
- Form fields are matched by label, so the parser handles several versions of the form layout.
- Customer- and partner-specific rules (custom apps, wallet setups, key names) are data, not code. They live in `private/customer_profiles.json`.
- After generating, the INI is checked for:
  - values the firmware accepts (allowed options, hex lengths, ranges)
  - every enabled app's `se_key_nb` pointing to a key slot that holds a key

## Setup

Requires Python 3.

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### Private data

Company and customer data is never committed. Create a `private/` folder with these files:

| File | Contents |
|---|---|
| `private/settings_default.ini` | The reader's default settings file |
| `private/config_ids.csv` | Config name to config ID lookup (`config_name,config_id`) |
| `private/customer_profiles.json` | Customer and partner rules. Copy `customer_profiles.example.json` to see the format. |

To build `config_ids.csv` from a configurations report:

```
venv/bin/python ini_generator/config_ids.py <config_ids_report.txt>
```

Without `customer_profiles.json` the app still runs, but customer and partner apps are not generated and a warning says so.

## Running

```
venv/bin/python app.py
```

Open http://127.0.0.1:5000, upload a CSV and select **Generate INI File**.

## Customer profiles

`private/customer_profiles.json` has these sections. `customer_profiles.example.json` shows each one with made-up values.

| Section | What it does |
|---|---|
| `default_tci` | Wallet terminal ID used when the form has no valid TCI |
| `keysets` | Manufacturer keyset, valid keyset families, the last keyset with separate mobile keys, test mobile keysets |
| `ble_names` | Maps "BLE Advertising Config" values to an advertising name |
| `mobile_keysets` | Key slots for each "Mobile Keyset" transport option |
| `keyword_apps` | Apps enabled when the form notes mention them, with optional classic/DESFire variants |
| `customer_profiles` | Settings applied by config name prefix (`CXY4` matches `"config_prefix": "XY"`) |
| `wallet_overrides` | Wallet setups that replace the standard Apple/Google wallet apps |

Settings are written as `{"section": {"key": "value"}}`, using INI syntax for the value (`"true"`, `"\"QUOTED\""`, `"0x03"`). Key slot values may use `{keyset}`, which is replaced with the form's keyset ID.

## Tests

```
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

| File | What it covers | Needs private data |
|---|---|---|
| `tests/test_rules.py` | One test per form-to-INI rule, using fake values and the example profiles | No |
| `tests/test_checks.py` | Runs the INI checks on every fixture form | `private/settings_default.ini` |
| `tests/test_reference_configs.py` | Compares generated INIs with known-good reference INIs | Fixtures and `tests/known_differences.py` |

Tests that need private data skip when it is missing, so a fresh clone runs only `test_rules.py`.

### Reference tests

1. Build the fixtures from the configuration workbooks and reference INIs:

   ```
   venv/bin/python tools/build_test_fixtures.py <workbook folder> <reference INI folder>
   ```

   This writes `tests/fixtures/` (gitignored). To keep the fixtures elsewhere, set `INI_FIXTURES_DIR`.

2. Any difference between a generated INI and its reference must be listed in `tests/known_differences.py` (gitignored) with a reason:
   - `REFERENCE_MISTAKE`
   - `PENDING_COLLEAGUES`
   - `DECISION`
   - `NOT_ON_FORM`

   A listed difference that no longer happens also fails the test. 

## Using it from another app

The generator is an installable package (`ini_generator`). Another app, such as CALIGA, installs it pinned to a commit:

```
ini-generator @ git+https://github.com/jhepburn-hue/INI-Generator.git@<commit>
```

Set `INI_GENERATOR_PRIVATE_DIR` to the folder holding `settings_default.ini` and `customer_profiles.json` before importing it. Without it, the package looks for `private/` at the repo root, which only exists in a clone.

```python
import os
os.environ["INI_GENERATOR_PRIVATE_DIR"] = "/path/to/private"

from ini_generator import generate_ini

rows = [["Config Name", "", "CXY1"], ["Idle LED", "", "Blue"], ["MFC CSN", "", "On", "32-bit msb"]]
ini_text, warnings = generate_ini(rows)
```

`rows` use the same layout as the CSV form: a label, then its value in the next few cells.

## Project layout

```
app.py                          Flask app (upload page and /upload endpoint)
ini_generator/csv_parser.py     Form parsing and the form-to-INI rules
ini_generator/prox_filter.py    Prox filter descriptions to filter mask/value
ini_generator/ini_checks.py     Validation of generated INIs
ini_generator/config_ids.py     Config ID lookup and report import
pyproject.toml                  Package definition
customer_profiles.example.json  Format of private/customer_profiles.json
templates/index.html            Upload page
tools/build_test_fixtures.py    Builds test fixtures from workbooks
tests/                          Tests
private/                        Company data (gitignored)
```
