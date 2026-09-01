import csv
import datetime
import json
import ast
import subprocess 
import os
import sys  # Import sys to read command-line arguments
import time
if len(sys.argv) < 2:
    print("Usage: python script_name.py <filename>")
    sys.exit(1)  # Exit if the filename is not provided


def run_command_and_notify(cmd):
    print(f"[AUTO_RUN-NS3] Starting NS-3 Emulation")
    
    # Start the process
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid = process.pid
    print(f"[AUTO_RUN-NS3] subprocess NS3 with PID: {pid}")
    # Wait for the process to complete
    stdout, stderr = process.communicate()

    # Check if the process was successful
    if process.returncode == 0:
        print("[AUTO_RUN-NS3] Process completed successfully.")
        # Optionally, print the output
        print(f"[AUTO_RUN-NS3] Output: {stdout.decode()}")
    else:
        print("[AUTO_RUN-NS3] Process failed.")
        # Optionally, print the error
        print(f"[AUTO_RUN-NS3]Error: {stderr.decode()}")
    print(f"[AUTO_RUN-NS3] Finish subprocess NS3 with PID: {pid}")

# Example usage

#filename = "elora-example"
#filename = "elora-example-TTN"
filename = "elora-example-two-channels"
PASSWORD = "......." # Password for SUDO mode
command = f"./run_ns3.sh {PASSWORD} %s %d %d %d %d %s %d %s %s_logDL.txt 2>&1" # Replace with your command

GW_number = [4]#first run
array = [100,400]#first run
seed = 250 #random seed default I used for other experiments is 250
period_array = [360]
percentage_array = [50]
n_runs = 10
server = sys.argv[2]
offset = 0
for k in range(n_runs):
    seed = seed*(1+k+offset)
    for ed in range(len(array)):
        for i in range(len(percentage_array)):
            for p in range(len(period_array)):
                for j in range(len(GW_number)):
                
                    ed_num = array[ed]
                    ed_period = period_array[p]
                    gw_num = GW_number[j]
                    per_conf = percentage_array[i]

                    print(f"/////////////////////////////// Start -*- ED number{ed_num}, GW number: {gw_num},%Conf: {per_conf}- RUN #: {k} -*-///////////////////////////////")

                    title = f"{sys.argv[1]}_TTS_stats_period_{ed_period}_gateway_{gw_num}_seed_{seed}_percentage_{per_conf}_log_N_ED_{ed_num}"
                    #ed_num = increment*(i+1)
                    #script_path = f"python3 log_mqtt.py {sys.argv[1]}_log_N_ED_{ed_num}.csv"
                    #process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    com = command%(filename,ed_num,ed_period,gw_num,seed,title, per_conf,'>',title)
                    #script_path = "udp_scrapt.py"
                    #process2 = subprocess.Popen(['python3',"MqttLog.py",f"{sys.argv[1]}_log_N_ED_{increment*(i+1)}.csv"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    #process2 = subprocess.Popen(['sudo','./python3',script_path,f"{sys.argv[1]}_log_N_ED_{ed_num}"], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    com2 = f"./run_scapy.sh minarady {sys.argv[1]}_period_{ed_period}_gateway_{gw_num}_seed_{seed}_percentage_{per_conf}_log_N_ED_{ed_num} > {sys.argv[1]}_cmd_output_period_SCAPY_{ed_period}_gateway_{gw_num}_seed_{seed}_percentage_{per_conf}_log_N_ED_{ed_num}.txt 2>&1" # Commented > {sys.argv[1]}_cmd_output_period_{ed_period}_gateway_{gw_num}_percentage_{per_conf}_log_N_ED_{ed_num}.txt 2>&1
                    if server == 'TTS':
                        com3 = f"python3 request_ttn_v4.py {sys.argv[1]}_events_period_{ed_period}_gateway_{gw_num}_seed_{seed}_percentage_{per_conf}_log_N_ED_{ed_num} > {sys.argv[1]}_REQUEST_cmd_output_period_{ed_period}_gateway_{gw_num}_seed_{seed}_percentage_{per_conf}_log_N_ED_{ed_num}.txt 2>&1"
                        print("[AUTO_RUN] Starting REST API")

                        process3 = subprocess.Popen(com3, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        pid3 = process3.pid
                        print(f"[AUTO_RUN] Started REST API  with PID: {pid3}")


                    if server == 'Chirpstack':
                        print("[AUTO_RUN] REST APO NOT USED BECAUSE IS CHIRPSTACK")
                    elif process3.poll() is None:
                        print("[AUTO_RUN] REST API is running good")

                    else:
                        print("[AUTO_RUN] REST API is not running")
                    #print("Starting",com2)
                    #print("ED number:",ed_num, "Period:",ed_period)
                    print("[AUTO_RUN] Starting UDP SNIFFER")
                    process2 = subprocess.Popen(com2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    #time.sleep(60)  # Adjust the sleep time as needed
                    pid = process2.pid
                    print(f"[AUTO_RUN] Started UDP SNIFFER  with PID: {pid}")


                    

                    print(f"[AUTO_RUN] Starting NS-3 EMULATION for ED number: {ed_num}, GW number: {gw_num}")
                    run_command_and_notify(com)
                    
                    # Terminate the process
                    print(f"[AUTO_RUN] Sent terminate signal to UDP SNIFFER PID: {pid}")
                    process2.terminate()
                    if server == "TTS":
                        print(f"[AUTO_RUN] Sent terminate signal to MQTT PID: {pid3}")
                        process3.terminate()
                    
                    # Wait a bit to give the process time to terminate gracefully

                    # Check if the process has indeed terminated, if not, force kill
                    if process2.poll() is None:  # If poll() returns None, the process is still running
                        print(f"[AUTO_RUN] Force killing SCAPY PID: {pid}")
                        process2.kill()
                    else:
                        print("[AUTO_RUN] SCAPY was TERMINATED")

                    if server == "TTS":
                        if process3.poll() is None:
                            print(f"Force killing REST API PID: {pid}")
                            process3.kill()
                        else:
                            print("[AUTO_RUN] REST API was TERMINATED")
                        #time.sleep(400)  # Adjust the sleep time as needed

                    # Wait for process to terminate and get the exit code
                    return_code = process2.wait()
                    print(f"[AUTO_RUN] Process SCAPY with PID {pid} terminated with return code {return_code}")
                    if server == "TTS":    
                        return_code = process3.wait()
                        print(f"[AUTO_RUN] Process REST API with PID {pid3} terminated with return code {return_code}")
                    print(f"////////////////////////////////////////////////////////// -*- FINISH -*- //////////////////////////////////////////")

