import requests
import json
import sys
import signal
import csv
import os
import time
AUTH_TOKEN = 'NNSXS.2G6NDFNH4CU7DCSD24OV6WDWW7XKWFNVWLFYMUI.EGW3QDAGVXBXKWA7ZJZB3P543MKLTHQMTUFH2IGURJDM7NUNT4JA'
URL = "http://localhost:1885/api/v3/events"
HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "text/event-stream",
    "Accept": "text/event-stream",
}
PAYLOAD = {
    "identifiers": [
        {"application_ids": {"application_id": "ns-3-application1-test"}}
    ]
}
EVENT_NAMES_TO_EXCLUDE = {"as.end_device.delete", 'ns.end_device.delete'}
RESULTS_TEMPLATE = {
    "blocked_only": 0,
    "conflict_only": 0,
    "mixed": 0,
    "not_allowed": 0,
    "total_to_ack": 0,
}

device_stats = {}
gw_stats = {"recuento": {
    "total_failed_scheduling": 0,
    "total_block": 0,
    "total_failed_Rx1": 0,
    "total_failed_Rx2": 0,
    "total_failed_conflict": 0,
    "total_failed_duty_cycle": 0,
    "total_gw_blocked": 0,
    "total_failed_duty_cycle_rx1": 0,
    "total_failed_negated_rx1": 0,
    "total_failed_negated_rx2": 0,
    "total_failed_duty_cycle_rx2": 0,
    "total_gw_blocked_rx1": 0,
    "total_gw_blocked_rx2": 0,
    "total_failed_conflict_rx1": 0,
    "total_failed_conflict_rx2": 0,
    "rx_empty": 0,
    "unknown": 0,
    "total_to_ack": 0
}}


def extract_confirm_status(message):
    """
    Extracts the 'confirmed' field from the JSON message.
    Returns True if 'confirmed' is True, False otherwise.
    If the field is missing, returns None.
    """
    global gw_stats

    try:
        if "results" not in gw_stats:
            gw_stats["results"] = RESULTS_TEMPLATE.copy()
        uplink_message = message.get("result", {}).get("data", {}).get("uplink_message", {})
        confirm_or_not = uplink_message.get("confirmed", None)
        if confirm_or_not is not None:
            if confirm_or_not:
                gw_stats["results"]["total_to_ack"] += 1
            return confirm_or_not
        return None
    except (KeyError, TypeError):
        return None  # Return None if the expected field is not found

def classify_failures(json_messages):
    global gw_stats
    if "results" not in gw_stats:
        gw_stats["results"] = RESULTS_TEMPLATE.copy()

    gateways = json_messages.get('result', {}).get('data', {}).get('details', [{}])[0].get("path_errors", [])
    results = {}
    empty_rx = False

    for gateway in gateways:
        gateway_uid = gateway.get("attributes", {}).get("gateway_uid", "unknown_gateway")
        path_errors = gateway.get("cause", {}).get("details", [{}])[0].get("path_errors", [])
        cnt = 0

        for path_error in path_errors:
            path_error_name = path_error.get("name", "")
            window = path_error.get("attributes", {}).get("window", cnt + 1)

            if path_error_name == "rx_empty":
                empty_rx = True
            elif path_error_name == "rx_and_data_rate":
                results.setdefault(gateway_uid, {})[window] = path_error_name
            else:
                cause_name = path_error.get("cause", {}).get("name", "")
                if cause_name in ["blocked", "conflict"]:
                    results.setdefault(gateway_uid, {})[window] = cause_name

            cnt += 1
    print(results)
    # Define the CSV file path
    csv_file_path = f'{sys.argv[1]}_results.csv'

    
    # Prepare data for CSV
    csv_data = [[time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), json.dumps(results)]]

    # Write data to CSV
    file_exists = os.path.isfile(csv_file_path)
    with open(csv_file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(["timestamp", "results"])  # Write headers if file does not exist
        writer.writerows(csv_data)  # Write data rows
    # Check failure types across all gateways
    has_blocked = any("blocked" in windows.values() for windows in results.values())
    has_conflict = any("conflict" in windows.values() for windows in results.values())
    has_not_allowed = any("rx_and_data_rate" in windows.values() for windows in results.values())

    # Classify failure type
    if has_blocked and has_conflict or empty_rx and has_not_allowed or has_blocked and has_not_allowed or has_conflict and has_not_allowed: 
        gw_stats["results"]["mixed"] += 1
    elif has_blocked:
        gw_stats["results"]["blocked_only"] += 1
    elif has_conflict:
        gw_stats["results"]["conflict_only"] += 1
    elif has_not_allowed:
        gw_stats["results"]["not_allowed"] += 1
    elif has_not_allowed:
        gw_stats["results"]["rx_empty"] += 1

def classify_failures_before(json_messages):
    global gw_stats
    if "results" not in gw_stats:
        gw_stats["results"] = RESULTS_TEMPLATE.copy()

    gateways = json_messages['result']['data']['details'][0]["path_errors"]
    results = {}
    empty_rx = False

    for gateway in gateways:
        path_errors = gateway["cause"]["details"][0]
        gateway_uid = gateway["attributes"]["gateway_uid"]
        cnt = 0

        for path_error in path_errors["path_errors"]:
            if path_error["name"] not in ["rx_empty", "not_allowed"]:
                cause_name = path_error['cause']['name']
                window = path_error["attributes"]["window"]
                if cause_name in ["blocked", "conflict"]:
                    results.setdefault(gateway_uid, {})[window] = cause_name
            elif path_error["name"] == "rx_and_data_rate":
                window = cnt + 1
                results.setdefault(gateway_uid, {})[window] = 'not_allowed'
            else:
                empty_rx = False
            cnt += 1

    has_blocked = any('blocked' in results[gw].values() for gw in results)
    has_conflict = any('conflict' in results[gw].values() for gw in results)
    not_allowed = any('rx_and_data_rate' in results[gw].values() for gw in results)

    if has_blocked and has_conflict and empty_rx:
        gw_stats["results"]["mixed"] += 1
    elif has_blocked:
        gw_stats["results"]["blocked_only"] += 1
    elif has_conflict:
        gw_stats["results"]["conflict_only"] += 1
    elif not_allowed:
        gw_stats["results"]["not_allowed"] += 1
def process_schedule_fail_event(event):
    global device_stats, gw_stats
    
    dev_addr = event["result"]["identifiers"][0]["device_ids"]["dev_addr"]
    device_stats.setdefault(dev_addr, {
        "schedulling_failure": 0,
        "scheduling_conflict_rx1": 0,
        "scheduling_conflict_rx2": 0,
        "duty_cycle_rx1": 0,
        "duty_cycle_rx2": 0,
        "gw_blocked_rx1": 0,
        "gw_blocked_rx2": 0,
        "conflict_no_detected_in_ns": 0
    })
    device_stats[dev_addr]["schedulling_failure"] += 1
    gw_stats["recuento"]['total_failed_scheduling'] += 1
    
    details = event["result"].get("data", {}).get("details", [])
    if not details:
        return
    
    for detail in details:
        path_errors = detail.get("path_errors", [])
        for gateway_error in path_errors:
            gateway_uid = gateway_error["attributes"].get("gateway_uid", "unknown_gateway")
            gw_stats.setdefault(gateway_uid, {
                "schedulling_failure": 0,
                "blocked": 0,
                "not_allowed": 0,
                "scheduling_conflict_rx1": 0,
                "scheduling_conflict_rx2": 0,
                "not_allowed_rx2": 0,
                "not_allowed_rx1": 0,
                "duty_cycle_rx1": 0,
                "duty_cycle_rx2": 0,
                "gw_blocked_rx1": 0,
                "gw_blocked_rx2": 0,
                "conflict_no_detected_in_ns": 0,
                "rx_empty": 0
            })
            gw_stats[gateway_uid]["schedulling_failure"] += 1
            
            cause = gateway_error.get("cause", {})
            if "details" in cause:
                for window_error in cause["details"]:
                    for rx_error in window_error.get("path_errors", []):
                        if "attributes" in rx_error:
                            window = rx_error["attributes"].get("window")
                            reason = rx_error.get("cause", {}).get("name", "unknown")
                            if window == 1:
                                gw_stats["recuento"]['total_failed_Rx1'] += 1
                            elif window == 2:
                                gw_stats["recuento"]['total_failed_Rx2'] += 1

                            if reason == "conflict":
                                key = f"scheduling_conflict_rx{window}"
                                device_stats[dev_addr][key] += 1
                                gw_stats[gateway_uid][key] += 1
                                gw_stats["recuento"][f'total_failed_conflict_rx{window}'] += 1
                            elif reason == "duty_cycle":
                                key = f"duty_cycle_rx{window}"
                                device_stats[dev_addr][key] += 1
                                gw_stats[gateway_uid][key] += 1
                                gw_stats["recuento"][f'total_failed_duty_cycle_rx{window}'] += 1
                            elif reason == 'blocked':
                                gw_stats[gateway_uid]["blocked"] += 1
                                key = f"gw_blocked_rx{window}"
                                device_stats[dev_addr][key] += 1
                                gw_stats[gateway_uid][key] += 1
                                gw_stats["recuento"][f'total_gw_blocked_rx{window}'] += 1
                            elif reason == 'rx_and_data_rate':
                                gw_stats[gateway_uid]["not_allowed"] += 1
                                key = f"not_allowed_rx{window}"
                                gw_stats[gateway_uid][key] += 1
                                gw_stats["recuento"][f'total_failed_negated_rx{window}'] += 1
                        elif rx_error.get("name") == 'rx_empty':
                            gw_stats["recuento"]["rx_empty"] += 1
                            gw_stats[gateway_uid]["rx_empty"] += 1
                        else:
                            gw_stats["recuento"]["unknown"] += 1

def process_schedule_fail_event_before(event):
    global device_stats, gw_stats
    dev_addr = event["result"]["identifiers"][0]["device_ids"]["dev_addr"]
    device_stats.setdefault(dev_addr, {
        "schedulling_failure": 0,
        "scheduling_conflict_rx1": 0,
        "scheduling_conflict_rx2": 0,
        "duty_cycle_rx1": 0,
        "duty_cycle_rx2": 0,
        "gw_blocked_rx1": 0,
        "gw_blocked_rx2": 0,
        "conflict_no_detected_in_ns": 0
    })
    device_stats[dev_addr]["schedulling_failure"] += 1
    gw_stats["recuento"]['total_failed_scheduling'] += 1

    path_errors_list = event["result"]["data"]["details"][0]
    path_errors = path_errors_list["path_errors"]

    for gateway_error in path_errors:
        gateway_uid = gateway_error["attributes"]["gateway_uid"]
        gw_stats.setdefault(gateway_uid, {
            "schedulling_failure": 0,
            "blocked": 0,
            "not_allowed": 0,
            "scheduling_conflict_rx1": 0,
            "scheduling_conflict_rx2": 0,
            "not_allowed_rx2": 0,
            "not_allowed_rx1": 0,
            "duty_cycle_rx1": 0,
            "duty_cycle_rx2": 0,
            "gw_blocked_rx1": 0,
            "gw_blocked_rx2": 0,
            "conflict_no_detected_in_ns": 0,
            "rx_empty": 0
        })
        gw_stats[gateway_uid]["schedulling_failure"] += 1

        window_error = gateway_error["cause"]["details"][0]
        for rx_error in window_error["path_errors"]:
            if "attributes" in rx_error:
                window = rx_error["attributes"]["window"]
                reason = rx_error["cause"]["name"]
                if window == 1:
                    gw_stats["recuento"]['total_failed_Rx1'] += 1
                elif window == 2:
                    gw_stats["recuento"]['total_failed_Rx2'] += 1

                if reason == "conflict":
                    if window == 1:
                        device_stats[dev_addr]["scheduling_conflict_rx1"] += 1
                        gw_stats[gateway_uid]["scheduling_conflict_rx1"] += 1
                        gw_stats["recuento"]['total_failed_conflict_rx1'] += 1
                    elif window == 2:
                        device_stats[dev_addr]["scheduling_conflict_rx2"] += 1
                        gw_stats[gateway_uid]["scheduling_conflict_rx2"] += 1
                        gw_stats["recuento"]['total_failed_conflict_rx2'] += 1
                elif reason == "duty_cycle":
                    if window == 1:
                        device_stats[dev_addr]["duty_cycle_rx1"] += 1
                        gw_stats[gateway_uid]["duty_cycle_rx1"] += 1
                        gw_stats["recuento"]['total_failed_duty_cycle_rx1'] += 1
                    elif window == 2:
                        device_stats[dev_addr]["duty_cycle_rx2"] += 1
                        gw_stats[gateway_uid]["duty_cycle_rx2"] += 1
                        gw_stats["recuento"]['total_failed_duty_cycle_rx2'] += 1
                elif reason == 'blocked':
                    gw_stats[gateway_uid]["blocked"] += 1
                    if window == 1:
                        device_stats[dev_addr]["gw_blocked_rx1"] += 1
                        gw_stats[gateway_uid]["gw_blocked_rx1"] += 1
                        gw_stats["recuento"]['total_gw_blocked_rx1'] += 1
                    elif window == 2:
                        device_stats[dev_addr]["gw_blocked_rx2"] += 1
                        gw_stats[gateway_uid]["gw_blocked_rx2"] += 1
                        gw_stats["recuento"]['total_gw_blocked_rx2'] += 1
                elif reason == 'not_allowed':
                    gw_stats[gateway_uid]["not_allowed"] += 1
                    if window == 1:
                        gw_stats[gateway_uid]["not_allowed_rx1"] += 1
                        gw_stats["recuento"]["total_failed_negated_rx1"] += 1
                    elif window == 2:
                        gw_stats[gateway_uid]["not_allowed_rx2"] += 1
                        gw_stats["recuento"]["total_failed_negated_rx2"] += 1
            elif rx_error["name"] == 'rx_empty':
                gw_stats["recuento"]["rx_empty"] += 1
                gw_stats[gateway_uid]["rx_empty"] += 1
            else:
                gw_stats["recuento"]["unknown"] += 1

def tx_fail_gs(event):
    global gw_stats
    gw_addr = event['result']["identifiers"][0]["gateway_ids"]["gateway_id"]
    gw_stats.setdefault(gw_addr, {
        "schedulling_failure": 0,
        "scheduling_conflict_rx1": 0,
        "scheduling_conflict_rx2": 0,
        "duty_cycle_rx1": 0,
        "duty_cycle_rx2": 0,
        "gw_blocked_rx1": 0,
        "gw_blocked_rx2": 0,
        "conflict_no_detected_in_ns": 0
    })
    gw_stats[gw_addr]["conflict_no_detected_in_ns"] += 1

def tx_fail_ed(event):
    global device_stats
    ED_addr = event['result']["identifiers"][0]["device_ids"]["dev_addr"]
    device_stats.setdefault(ED_addr, {
        "schedulling_failure": 0,
        "scheduling_conflict_rx1": 0,
        "scheduling_conflict_rx2": 0,
        "duty_cycle_rx1": 0,
        "duty_cycle_rx2": 0,
        "gw_blocked_rx1": 0,
        "gw_blocked_rx2": 0,
        "conflict_no_detected_in_ns": 0
    })
    device_stats[ED_addr]["conflict_no_detected_in_ns"] += 1

def finish():
    with open(f'{sys.argv[1]}_ED.json', 'w') as json_file:
        json.dump(device_stats, json_file, indent=4)
    with open(f'{sys.argv[1]}_GW.json', 'w') as json_file:
        json.dump(gw_stats, json_file, indent=4)

def signal_handler(sig, frame):
    print("Process interrupted, closing the file and exiting gracefully.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def subscribe_and_stream_events(response):
    with open(f'{sys.argv[1]}.json', 'w+') as file:
        for line in response.iter_lines():
            if line:
                json_response = json.loads(line.decode('utf-8'))
                event_name = json_response.get("result", {}).get("name")
                if event_name not in EVENT_NAMES_TO_EXCLUDE:
                    json.dump(json_response, file)
                    file.write('\n')
                    if event_name == "ns.down.data.schedule.fail":
                        #process_schedule_fail_event(json_response)
                        classify_failures(json_response)
                    elif event_name == "gs.down.tx.fail":
                        tx_fail_gs(json_response)
                    elif event_name == "as.up.data.forward":
                        extract_confirm_status(json_response)
                    elif event_name == "ns.down.transmission.fail":
                        tx_fail_ed(json_response)
                    elif event_name == 'end_device.delete':
                        finish()
                        print("Process Finished")
                        break

if __name__ == "__main__":
    response = requests.post(URL, headers=HEADERS, json=PAYLOAD, stream=True)
    if response.status_code == 200:
        subscribe_and_stream_events(response)
