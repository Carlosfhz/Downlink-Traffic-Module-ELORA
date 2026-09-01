import subprocess
import time
from scapy.all import *
import base64
import json
import csv
import re
import traceback
import datetime
from decodeLora import decrypt_lorawan_payload

def extract_sf_bw(sf_bw_string):
    """
    Extracts the spreading factor and bandwidth from a string formatted as 'SFxBWy'.
    
    Args:
    - sf_bw_string (str): The input string formatted as 'SFxBWy'.

    Returns:
    - tuple: (spreading_factor, bandwidth) where bandwidth is multiplied by 1000.
    """
    # Regular expression to match the pattern
    match = re.match(r'SF(\d+)BW(\d+)', sf_bw_string)
    
    if match:
        # Extract spreading factor and bandwidth, convert them to integers
        spreading_factor = int(match.group(1))
        bandwidth = int(match.group(2)) * 1000  # Multiply the bandwidth by 1000
        
        return spreading_factor, bandwidth
    else:
        raise ValueError("Input string does not match the expected format 'SFxBWy'")



def convert_high_precision_epoch_to_date(epoch_ns):
    # Split the epoch into seconds and nanoseconds
    seconds = int(epoch_ns)  # Get the integer part for seconds
    nanoseconds = int((epoch_ns - seconds) * 1e9)  # Multiply fractional part by 1e9 to get nanoseconds

    # Convert seconds to datetime object
    date_time = datetime.datetime.fromtimestamp(seconds)

    # Format datetime object to string
    #formatted_date = date_time.strftime('%Y-%m-%d %H:%M:%S')
    formatted_date = date_time.strftime('%H:%M:%S')
    full_formatted_date = f"{formatted_date}.{nanoseconds:09d}"

    return full_formatted_date
file_name = "TEST_scapt_faster"  # Change to your .pcap file path
forw_message = ['PUSH_DATA','PUSH_ACK ','PULL_DATA','PULL_RESP','PULL_ACK','TX_ACK']

current_token_dl = []
current_token_ul = []

def callback(pkt):
    #pkt.show()
    payload = pkt[UDP].payload

    # Convert payload to string if it's not empty
    if payload:
        raw_bytes = bytes(payload)
        #print("Payload data:", raw_bytes)
        token = raw_bytes[1:3].hex() #the position 2 is not inclusive that I put 3 instead of 2 
        eventId = raw_bytes[3]
        #print(f"Token:{token}")
    app_skey = '.......'  # Your AppSKey here
    #PUSH_DATA COMES WITH UL FROM BYTE 12 and GW
    #PUSH_ACK
    #PULL_DATA Comes with GW ID from byte 4 to 11
    #PULL_ACK comes with the same token as PULL_DATA
    #PULL_RESP comes with DL FROM byte 4
    #PULL_ACK
    #TX_ACK Comes with the same 
    #Byte 3 is identify in all
    csv_file_path = file_name+'.csv'
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file, delimiter=',')
        ul_ed = {}

        try:
            # Attempt to extract the payload as binary data
            timeStamp = convert_high_precision_epoch_to_date(float(pkt.time))
       
            token = raw_bytes[1:3].hex() #the position 2 is not inclusive that I put 3 instead of 2 
            eventId = raw_bytes[3]

            match eventId:
                case 0: #PUSH_DATA
                    json_uplink = raw_bytes[12::]
                    decoded_string = json_uplink.decode('utf-8')
                    message_tmp = json.loads(decoded_string)

                    gatewayid = raw_bytes[4:12].hex()
                    #print(message_tmp)
                    UL_now = []
                    if 'rxpk' in message_tmp.keys():
                        for tx_param in message_tmp['rxpk']:
                            payload = tx_param['data']
                            freq = tx_param['freq']
                            cr = tx_param['codr']
                            sf,bw = extract_sf_bw(tx_param['datr'])
                            tmst = tx_param['tmst']
                            lsnr = tx_param['lsnr']
                            rssi = tx_param['rssi']
                            message = {'phyPayload':payload,'ulID':token,'tmst':tmst, 'txInfo': {'frequency': freq, 'modulation': {'lora': {'bandwidth': bw, 
                                    'spreadingFactor': sf, 'codeRate': cr}}}, 'rxInfo': {'gatewayId': gatewayid, 
                                    'uplinkId': token, 'time': timeStamp, 'rssi': rssi, 'snr': lsnr, 'context': 'unknown', 'crcStatus': 'unknown'}}
                            decodMSG =  decrypt_lorawan_payload(payload, app_skey)
                            event = 'up'
                            UL_now.append([message,decodMSG,gatewayid])

                            ul_ed = {"ID_ED":decodMSG['DevAddr'],"TOKEN":token,"TMST":tmst}
                            #print(ul_ed)
                            current_token_ul.append(ul_ed)

                            print(f"Timestamp:{timeStamp}, {forw_message[0]},TOKEN:{token},Gateway:{gatewayid}, Uplink:{message}")
                    else:
                        #event = 'skip'
                        message = message_tmp
                        decodMSG = 'y'
                        event = 'skip'



                case 1:#PUSH_ACK
                    message = {'token':token}
                    event = 'push-ack'
                    
                case 2:#PULL_DATA
                    message = {'token':token}

                    event = 'pull-data'
                    
                case 3:#PULL_RESP
                    
                    json_downlink = raw_bytes[4::]
                    #print(json_downlink)
                    decoded_string = json_downlink.decode('utf-8')
                    downlink_tmp = json.loads(decoded_string)
                    payload = downlink_tmp['txpk']['data']
                    freq = downlink_tmp['txpk']['freq']
                    cr = downlink_tmp['txpk']['codr']
                    power = downlink_tmp['txpk']['powe']
                    tmst = downlink_tmp['txpk']['tmst']
                    sf,bw = extract_sf_bw(downlink_tmp['txpk']['datr'])
                    decodMSG =  decrypt_lorawan_payload(payload, app_skey)
                    ul_token = -1
                    delay = -1
                    to_be_remove = []
                    for ul in current_token_ul:
                        delay_tmp = tmst-ul["TMST"]
     

                        if decodMSG['DevAddr'] == ul["ID_ED"] and (delay_tmp == 2*1e6 or delay_tmp ==1e6):
                            ul_token = ul["TOKEN"]
                            delay = delay_tmp
                        elif delay_tmp>=2*1e6 and decodMSG['DevAddr'] == ul["ID_ED"]:
                            to_be_remove.append(ul)
                            

                    downlink = {'downlinkId': token,'uplinkId':ul_token,'tmst':tmst, 'items': [{'phyPayload': payload, 
                                                         'txInfo': {'frequency': freq  , 'power': power, 
                                                                    'modulation': {'lora': {'bandwidth': bw, 'spreadingFactor': sf, 'codeRate':cr, 
                                                                    'polarizationInversion': True}}, 'timing': {'delay': {'delay': delay/1e6}}, 'context': 'UNKNOWN'}}, 
                                                                    {}],
                                'gatewayId': '0001000000000003'}
                    
                    for ul_rem in to_be_remove:
                        current_token_ul.remove(ul_rem)
                    data_resp = {"Timestamp":timeStamp,"forw":forw_message[3],"TOKEN":token, "Downlink":downlink,'decodpay':decodMSG}
                    current_token_dl.append([token,data_resp])
                    event='pull-resp'
                    #print(json_downlink)
                    print(f"Timestamp:{timeStamp},{forw_message[3]},TOKEN:{token}, Downlink:{downlink}")

                case 4:#PULL_ACK
                    event = 'pull-ack'
                    message = {'token':token}

                    
                case 5:#TX_ACK
                    down_elem = {}
                    event = 'ack'


                    to_delete = 0
                    gatewayid = raw_bytes[4:12].hex()
                    message = {'gatewayId':gatewayid,'downlinkId':token,'items': []}

                    for elem in current_token_dl:
                        token_out,dicta = elem
                        #print(f"looking of {token}  and  found {token_out}")

                        if token_out==token: 

                            down_elem = dicta["Downlink"]
                            timeStamp_dl = dicta["Timestamp"]
                            decodeMSG_dl = dicta["decodpay"]
                            down_elem['gatewayId'] = gatewayid

                            if len(raw_bytes)>19:
                                json_ack =  json.loads(raw_bytes[12::].decode('utf-8'))['txpk_ack']['error']
                                #print(f"Jason ACK: {json_ack}")
                                #print(json_ack)
                                if down_elem['items'][0]['txInfo']['frequency'] == 869.525:
                                    message['items'].append({'status':'NO'})
                                    message['items'].append({'status':json_ack})
                                else:       
                                    message['items'].append({'status':json_ack})
                                    message['items'].append({})    
                                print(f"Timestamp:{timeStamp},{forw_message[5]},TOKEN:{token},Gateway:{gatewayid}, ACK_DL:{raw_bytes[12::]}")
                            else:

                                if down_elem['items'][0]['txInfo']['frequency'] == 869.525:
                                    message['items'].append({'status':'NO'})
                                    message['items'].append({'status':'OK'})
                                else:       
                                    message['items'].append({'status':'OK'})
                                    message['items'].append({}) 

                                print(f"Timestamp:{timeStamp},{forw_message[5]},TOKEN:{token},Gateway:{gatewayid}")

                            to_delete = elem
                            
                    current_token_dl.remove(to_delete)




                    



                case _:
                    
                    print("NOT FOUND")

            if eventId == 5:
                row1 = [timeStamp_dl,gatewayid,forw_message[3],"down",down_elem,decodeMSG_dl]
                #print(row1)
                writer.writerow(row1)
            
            if event!='skip' and (event =='up' or event == 'ack' or event =='up-mas'):
                if event =='up':
                    for mes,deco,gw in UL_now:
                        row2 = [timeStamp,gw,forw_message[eventId],event,mes,deco]
                        writer.writerow(row2)

                else:
                    row2 = [timeStamp,gatewayid,forw_message[eventId],event,message,"y"]
                    writer.writerow(row2)
                #print(row2)




        except Exception as e:
            print("Error processing packet:", e)
            traceback.print_exc()  # This will print the stack trace including line numbers




def is_interface_up(interface):
    """Check if the specified interface is up using the 'ip link' command."""
    try:
        # Execute the command to check the interface status
        output = subprocess.check_output(['ip', 'link', 'show', interface], text=True)
        # Look for 'state UP' in the command output

        return '<BROADCAST,MULTICAST,UP,LOWER_UP>' in output
    except subprocess.CalledProcessError:
        # If the command fails, assume the interface is not up or does not exist
        return False

def monitor_interface(interface):
    """Monitor the specified interface and notify when it is up."""
    while True:
        if is_interface_up(interface):
            print(f"Interface {interface} is now UP.")
            break  # Exit the loop if the interface is up
        else:
            #print(f"Interface {interface} is down. Checking again in 5 seconds...")
            continue

if __name__ == "__main__":
    file_name = sys.argv[1]
    interface_to_monitor = "ns3-tap"  # Specify the interface you want to monitor
    csv_file_path = file_name+'.csv'
    with open(csv_file_path, mode='w+', newline='') as file:
        writer = csv.writer(file, delimiter=',')
        writer.writerow(['Timestamp', 'Gateway', 'Topic', 'Traffic', 'Message', 'Decoded-Payload'])
    monitor_interface(interface_to_monitor)
    sniff(iface=interface_to_monitor,prn=callback, filter="udp and ( port 1700)")

