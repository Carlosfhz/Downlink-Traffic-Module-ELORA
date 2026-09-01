#!/usr/bin/expect -f
set password [lindex $argv 0]  ;# Take password as an argument
set file [lindex $argv 1]   ;# Number of devices from argument
set timeout -1

spawn sudo python3 udp_scrapt.py $file
#spawn ./ns3 run "elora-example --log --test --devices=$devices"
#Wait for the password prompt
expect {
    -exact "Sudo password:" {
        sleep 1              ;# Wait for a moment just in case
        send "$password\r"   ;# Send the password
        exp_continue         ;# Continue expecting for additional prompts or end
    }
    timeout {
        send_user "Timed out waiting for password prompt\n"
        exit
    }
}

interact
