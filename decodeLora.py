import base64
from Crypto.Cipher import AES
from Crypto.Util import Counter

def decode_mhdr(mhdr_byte):
    mtype = (mhdr_byte >> 5) & 0x07  # Message Type (MType)
    return {
        'MType': mtype,
    }

def decode_fhdr(fhdr_bytes):
    dev_addr = fhdr_bytes[:4]  # Device address is first 4 bytes
    f_ctrl = fhdr_bytes[4]     # Frame control field is next 1 byte
    f_cnt = int.from_bytes(fhdr_bytes[5:7], 'little')  # Frame counter is next 2 bytes
    return {
        'DevAddr': dev_addr.hex(),
        'FCtrl': f_ctrl,
        'FCnt': f_cnt,
    }

def decrypt_lorawan_payload(base64_payload, app_skey):
    # Decode payload from Base64
    raw_payload = base64.b64decode(base64_payload)

    # Extract and decode MHDR, FHDR, and FPort
    mhdr_byte = raw_payload[0]
    fhdr_bytes = raw_payload[1:8]  # Adjust based on actual FHDR length
    f_port = raw_payload[8]
    encrypted_payload = raw_payload[9:]

    # Decode MHDR and FHDR
    mhdr = decode_mhdr(mhdr_byte)
    fhdr = decode_fhdr(fhdr_bytes)

    # Decrypt FRMPayload (if present and encrypted)
    decrypted_data = None  # Default if no payload or not encrypted
    if f_port != 0:  # Assuming FRMPayload is encrypted if FPort is not 0
        key = bytes.fromhex(app_skey)
        counter_block = fhdr_bytes[:4][::-1] + fhdr_bytes[5:7] + b'\x00' * 9  # Adjust based on actual structure
        ctr = Counter.new(128, initial_value=int.from_bytes(counter_block, 'big'))
        cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
        decrypted_payload = cipher.decrypt(encrypted_payload)
        decrypted_data = decrypted_payload.hex()

    return {
        'MHDR': mhdr,
        #'FHDR': fhdr, #this
        'DevAddr':fhdr['DevAddr'],
        'FCtrl':fhdr['FCtrl'],
        'Fcnt': fhdr['FCnt'],
        'FPort': f_port,
        'FRMPayload': decrypted_data
    }

# Example usage
#base64_payload = 'gAIAAAIABAABAAAAAAAAAAAAAAAAAAAAAAAAAAAwnHQ8'  # Your Base64-encoded payload here
#app_skey = '2b7e151628aed2a6abf7158809cf4f3c'  # Your AppSKey here

#decoded_data = decrypt_lorawan_payload(base64_payload, app_skey)
#print('Decoded Data:', decoded_data)
