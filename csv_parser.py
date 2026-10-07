import csv
import io

def parse_csv_file(file_contents):
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
    target = setting_label.strip().lower()
    
    for row in rows:
        for idx, cell in enumerate(row):
            if cell.lower() == target:
                for next_cell in row[idx + 1:]:
                    if next_cell != "":
                        return next_cell
    return None

def is_setting_mentioned(rows, setting):
    for row in rows:
        for cell in row:
            cell_lower = cell.lower()
            if setting in cell_lower:
                return True

    return False

def get_av_section(rows):
    idle_led_raw = get_setting_value(rows, "Idle LED")
    beeper_raw = get_setting_value(rows, "Beeper")
    
    idle_color = idle_led_raw.lower() if idle_led_raw else "white"
    
    silence_beeper = "false"
    if beeper_raw and beeper_raw.lower() == "off":
        silence_beeper = "true"

    lines = [
        '[av]',
        f'silence_beeper = {silence_beeper}',
        'host_control_enabled = true',
        'host_control_exclusive = false',
        f'idle_color = "{idle_color}"',
        'red_intensity = 6',
        'green_intensity = 5',
        'blue_intensity = 5'
    ]
    
    return "\n".join(lines)

def get_ble_section(rows):
    setting_value = get_setting_value(rows, "BLE Functionality")
    enabled = False if setting_value == 'Disabled' else True

    lines = [
        '[ble]',
        f'enabled = {enabled}',
        'connection_timeout_ms = 10000',
        'allow_fw_updates = true'
    ]
    
    return "\n".join(lines) 

def get_ble_adv_params_section():
    lines = [
        '[ble/adv_params]',
        'interval_min = 48',
        'interval_max = 96',
        'options = 0x0001'
    ]
    
    return "\n".join(lines) 

def get_ble_adv_data_section():
    lines = [
        '[ble/adv_data]'
    ]
    
    return "\n".join(lines) 

def get_ble_av_section():
    lines = [
        '[ble/av]',
        'override_osdp_leds = true',
        'color = "amber"',
        'is_blinking = false',
        'blinking_period = 0'
    ]
    
    return "\n".join(lines) 

def get_ble_configure_section(rows):
    setting_value = get_setting_value(rows, "BLE Functionality")
    enabled = True if "Admin" in setting_value else False

    lines = [
        '[ble/configure]',
        f'secure_transactions = {enabled}',
        'allow_credentials = false',
        'bcd_credentials = false',
        'admin_timeout_s = 60'
    ]
    
    return "\n".join(lines) 

def get_card_tracker_section():
    lines = [
        '[card_tracker]',
        'enabled = true',
        'max_cards = 4',
        'timeout_ms = 1000'
    ]
    
    return "\n".join(lines) 

def get_host_communication_section():
    lines = [
        '[host_communication]',
        'mode = "auto_detect"'
    ]
    
    return "\n".join(lines) 

def get_keypad_section():
    lines = [
        '[keypad]',
        'keymap_kp1 = "1"',
        'keymap_kp2 = "2"',
        'keymap_kp3 = "3"',
        'keymap_kp4 = "4"',
        'keymap_kp5 = "5"',
        'keymap_kp6 = "6"',
        'keymap_kp7 = "7"',
        'keymap_kp8 = "8"',
        'keymap_kp9 = "9"',
        'keymap_kp0 = "0"',
        'keymap_kpasterisk = "*"',
        'keymap_kppound = "#"'
    ]

    return "\n".join(lines)    

def get_keypad_mullion_section():
    lines = [
        '[keypad_mullion]',
        'keymap_kp1 = "1"',
        'keymap_kp2 = "2"',
        'keymap_kp3 = "3"',
        'keymap_kp4 = "4"',
        'keymap_kp5 = "5"',
        'keymap_kp6 = "6"',
        'keymap_kp7 = "7"',
        'keymap_kp8 = "8"',
        'keymap_kp9 = "9"',
        'keymap_kp0 = "0"',
        'keymap_kpasterisk = "#"',
        'keymap_kppound = "*"'
    ]
    
    return "\n".join(lines)

def get_mfg_data_section():
    lines = [
        '[mfg_data]',
    ]
    
    return "\n".join(lines) 

def get_mypass_section(rows):
    setting_value = get_setting_value(rows, "BLE Functionality")
    enabled = False
    km1_se_slot_nb = 0
    km2_se_slot_nb = 0
    kc1_se_slot_nb = 0
    kc2_se_slot_nb = 0

    if setting_value and 'Credentials' in setting_value:
        enabled = True
        km1_se_slot_nb = '03'
        km2_se_slot_nb = '13'
        kc1_se_slot_nb = '04'
        kc2_se_slot_nb = '14'

    lines = [
        '[mypass]',
        f'allow_credentials = {enabled}',
        'bcd_credentials = false',
        f'km1_se_slot_nb = {km1_se_slot_nb}',
        f'km2_se_slot_nb = {km2_se_slot_nb}',
        f'kc1_se_slot_nb = {kc1_se_slot_nb}',
        f'kc2_se_slot_nb = {kc2_se_slot_nb}',
        'allow_keys = true',
        'metadata = "00000000"',
        'allow_key_rolling = true'
    ]
    
    return "\n".join(lines) 

def get_osdp_section():
    lines = [
        '[osdp]',
        'response_time_limit_ms = 200',
        'vendor_code = "5C2623"',
        'comset_kills_sc = false',
        'allow_stacked_osdp_av_cmds = false',
        'reverse_red_green_led = false',
        'prevent_sc_with_ba = false',
        'prevent_sc_no_scs_15 = false',
        'sc_exclusive = false',
        'scs_timeout_follows_spec = true',
        'clear_scbk = false',
        'allow_all_commands_on_broadcast = false',
        'ext_info_ethos_format = false',
        'skip_poll_cmd_length_check = false',
        'allow_scb_checksum = false'
    ]
    
    return "\n".join(lines)

def get_osdp_comms_section():
    lines = [
        '[osdp/comms]',
        'baud_rate = 9600',
        'addr = 0'
    ]
    
    return "\n".join(lines)

def get_rfid_section():
    lines = [
        '[rfid]',
        'poll_period_ms = 100'
    ]
    
    return "\n".join(lines)

def get_rfid_av_section(rows):
    lines = [
        '[rfid/av]',
    ]
    
    return "\n".join(lines)

def get_rfid_lf_section():
    lines = [
        '[rfid/lf]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_nfc_section():
    lines = [
        '[rfid/hf/nfc]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_allegion_android_section():
    lines = [
        '[rfid/hf/app/allegion/android]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_allegion_ios_section():
    lines = [
        '[rfid/hf/app/allegion/ios]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_config_section():
    lines = [
        '[rfid/hf/app/config]',
        'enabled = true',
        'startup_timeout_s = 60'
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_csn_section():
    lines = [
        '[rfid/hf/app/csn]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_dormakaba_section():
    lines = [
        '[rfid/hf/app/dormakaba]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_fidelity_section():
    lines = [
        '[rfid/hf/app/fidelity]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_iclass_section():
    lines = [
        '[rfid/hf/app/iclass]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_desfire_section():
    lines = [
        '[rfid/hf/app/leaf/desfire]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_desfire_one_section():
    lines = [
        '[rfid/hf/app/leaf/desfire/1]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_desfire_two_section():
    lines = [
        '[rfid/hf/app/leaf/desfire/2]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_desfire_three_section():
    lines = [
        '[rfid/hf/app/leaf/desfire/3]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_desfire_four_section():
    lines = [
        '[rfid/hf/app/leaf/desfire/4]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_leaf_duox_openid_section():
    lines = [
        '[rfid/hf/app/leaf/duox/openid]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_meridian_section():
    lines = [
        '[rfid/hf/app/meridian]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_mifare_2go_generic_section():
    lines = [
        '[rfid/hf/app/mifare_2go/generic]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_mypass_section(rows):
    setting_value = get_setting_value(rows, "BLE Functionality")
    enabled = True if setting_value else False

    lines = [
        '[rfid/hf/app/mypass]',
        f'enabled = {enabled}'
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_nexpacs_section():
    lines = [
        '[rfid/hf/app/nexpacs]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_pkoc_section():
    lines = [
        '[rfid/hf/app/pkoc]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_smartmax_classic_section(rows):
    enabled = False
    se_key_nb = 0
    setting_values = ['smartmax classic', 'smartmax mfc', 'classic smartmax', 'mfc/mfd smartmax']

    for setting in setting_values:
        if is_setting_mentioned(rows, setting):
            enabled = True
            break

    if enabled:
        se_key_nb = 30

    lines = [
        '[rfid/hf/app/smartmax/classic]',
        f'enabled = {enabled}',
        f'se_key_nb = {se_key_nb}',
        'bcd_format = false'
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_smartmax_desfire_section(rows):
    enabled = False
    se_key_nb = 0
    setting_values = ['smartmax desfire', 'smartmax mfd', 'desfire smartmax', 'mfc/mfd smartmax']

    for setting in setting_values:
        if is_setting_mentioned(rows, setting):
            enabled = True
            break

    if enabled:
        se_key_nb = 31

    lines = [
        '[rfid/hf/app/smartmax/desfire]',
        f'enabled = {enabled}',
        f'se_key_nb = {se_key_nb}',
        'bcd_format = false'
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_software_house_classic_section():
    lines = [
        '[rfid/hf/app/software_house/classic]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_software_house_desfire_section():
    lines = [
        '[rfid/hf/app/software_house/desfire]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_vanderbilt_classic_section():
    lines = [
        '[rfid/hf/app/vanderbilt/classic]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_vanderbilt_desfire_section():
    lines = [
        '[rfid/hf/app/vanderbilt/desfire]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_visa_section():
    lines = [
        '[rfid/hf/app/visa]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_wallet_section(rows):
    setting_value = get_setting_value(rows, "ECP TCI")
    terminal_id = setting_value if setting_value else "000000"

    lines = [
        '[rfid/hf/app/wallet]',
        f'terminal_id = "{terminal_id}"',
        'selected_format = 0x2',
        'terminal_mode = 0x0',
        'terminal_info = 0xC3',
        'terminal_type = 0x02',
        'terminal_subtype = 0x2'
    ]
    
    return "\n".join(lines)

def get_tamper_section(rows):
    setting_value = get_setting_value(rows, "Tamper Monitoring")
    enabled = True if setting_value == 'On' else False

    lines = [
        '[tamper]',
        f'wiegand_reporting_enabled = {enabled}',
        f'osdp_reporting_enabled = {enabled}',
        'beeper_during_osdp_enabled = false',
        'report_state_change_only_enabled = true',
        'num_reads_enter_active = 5',
        'num_reads_enter_inactive = 25',
        'sample_frequency_ms = 200'
    ]
    
    return "\n".join(lines)

def get_tamper_accel_section():
    lines = [
        '[tamper/accel]',
        'sensitivity = "default"',
        'x_axis_enabled = true',
        'y_axis_enabled = true',
        'z_axis_enabled = true'
    ]
    
    return "\n".join(lines)

def get_wiegand_section(rows):
    setting_value = get_setting_value(rows, "Keypad Format")
    default_format_values = {
        '4-bit':'4_bit',
        '8-bit':'8_bit',
        'buffered 26-bit':'26_bit',
        'Magstripe - 4 digit':'magstripe_4',
        'Magstripe - 5 digit':'magstripe_5'
    }
    default_format = default_format_values[setting_value]

    lines = [
        '[wiegand]',
        'space_duration_us = 200',
        'pulse_duration_us = 20',
        'lines_inverted = false',
        'red_ctrl_mode = "red"',
        'green_ctrl_mode = "green"',
        'buzzer_ctrl_mode = "buzzer"',
        f'default_format = {default_format}',
        'default_facility_code = 0'
    ]
    
    return "\n".join(lines)

def get_keys_section():
    lines = [
        '[keys]',
    ]

    # smartmax classic -- slot30 = AMAG:MFC
    # smartmax desfire -- slot31 = AMAG:USER_APP_READ_KEYSET
    
    return "\n".join(lines)

def generate_ini(rows):
    sections = [
        get_av_section(rows),
        get_ble_section(rows),
        get_ble_adv_params_section(),
        get_ble_adv_data_section(),
        get_ble_av_section(),
        get_ble_configure_section(),
        get_card_tracker_section(),
        get_host_communication_section(),
        get_keypad_section(),
        get_keypad_mullion_section(),
        get_mfg_data_section(),
        get_mypass_section(rows),
        get_osdp_section(),
        get_osdp_comms_section(),
        get_rfid_section(),
        get_rfid_av_section(rows),
        get_rfid_lf_section(),
        get_rfid_hf_nfc_section(),
        get_rfid_hf_app_allegion_android_section(),
        get_rfid_hf_app_allegion_ios_section(),
        get_rfid_hf_app_config_section(),
        get_rfid_hf_app_csn_section(),
        get_rfid_hf_app_dormakaba_section(),
        get_rfid_hf_app_fidelity_section(),
        get_rfid_hf_app_iclass_section(),
        get_rfid_hf_app_leaf_desfire_section(),
        get_rfid_hf_app_leaf_desfire_one_section(),
        get_rfid_hf_app_leaf_desfire_two_section(),
        get_rfid_hf_app_leaf_desfire_three_section(),
        get_rfid_hf_app_leaf_desfire_four_section(),
        get_rfid_hf_app_leaf_duox_openid_section(),
        get_rfid_hf_app_meridian_section(),
        get_rfid_hf_app_mifare_2go_generic_section(),
        get_rfid_hf_app_mypass_section(rows),
        get_rfid_hf_app_nexpacs_section(),
        get_rfid_hf_app_pkoc_section(),
        get_rfid_hf_app_smartmax_classic_section(rows),
        get_rfid_hf_app_smartmax_desfire_section(rows),
        get_rfid_hf_app_software_house_classic_section(),
        get_rfid_hf_app_software_house_desfire_section(),
        get_rfid_hf_app_vanderbilt_classic_section(),
        get_rfid_hf_app_vanderbilt_desfire_section(),
        get_rfid_hf_app_visa_section(),
        get_rfid_hf_app_wallet_section(rows),
        get_tamper_section(rows),
        get_tamper_accel_section(),
        get_wiegand_section(rows),
        get_keys_section()
    ]
    
    return "\n\n".join(sections)