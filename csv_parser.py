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

def get_ble_section():
    lines = [
        '[ble]'
    ]
    
    return "\n".join(lines) 

def get_ble_adv_params_section():
    lines = [
        '[ble/adv_params]'
    ]
    
    return "\n".join(lines) 

def get_ble_adv_data_section():
    lines = [
        '[ble/adv_data]'
    ]
    
    return "\n".join(lines) 

def get_ble_av_section():
    lines = [
        '[ble/av]'
    ]
    
    return "\n".join(lines) 

def get_ble_configure_section():
    lines = [
        '[ble/configure]'
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

def get_mypass_section():
    lines = [
        '[mypass]',
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

def get_rfid_av_section():
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

def get_rfid_hf_app_mypass_section():
    lines = [
        '[rfid/hf/app/mypass]',
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

def get_rfid_hf_app_smartmax_classic_section():
    lines = [
        '[rfid/hf/app/smartmax/classic]',
    ]
    
    return "\n".join(lines)

def get_rfid_hf_app_smartmax_desfire_section():
    lines = [
        '[rfid/hf/app/smartmax/desfire]',
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

def get_rfid_hf_app_wallet_section():
    lines = [
        '[rfid/hf/app/wallet]',
    ]
    
    return "\n".join(lines)

def get_tamper_section():
    lines = [
        '[tamper]',
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

def get_wiegand_section():
    lines = [
        '[wiegand]',
    ]
    
    return "\n".join(lines)

def get_keys_section():
    lines = [
        '[keys]',
    ]
    
    return "\n".join(lines)

def generate_ini(rows):
    sections = [
        get_av_section(rows),
        get_ble_section(),
        get_ble_adv_params_section(),
        get_ble_adv_data_section(),
        get_ble_av_section(),
        get_ble_configure_section(),
        get_card_tracker_section(),
        get_host_communication_section(),
        get_keypad_section(),
        get_keypad_mullion_section(),
        get_mfg_data_section(),
        get_mypass_section(),
        get_osdp_section(),
        get_osdp_comms_section(),
        get_rfid_section(),
        get_rfid_av_section(),
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
        get_rfid_hf_app_mypass_section(),
        get_rfid_hf_app_nexpacs_section(),
        get_rfid_hf_app_pkoc_section(),
        get_rfid_hf_app_smartmax_classic_section(),
        get_rfid_hf_app_smartmax_desfire_section(),
        get_rfid_hf_app_software_house_classic_section(),
        get_rfid_hf_app_software_house_desfire_section(),
        get_rfid_hf_app_vanderbilt_classic_section(),
        get_rfid_hf_app_vanderbilt_desfire_section(),
        get_rfid_hf_app_visa_section(),
        get_rfid_hf_app_wallet_section(),
        get_tamper_section(),
        get_tamper_accel_section(),
        get_wiegand_section(),
        get_keys_section()
    ]
    
    return "\n\n".join(sections)