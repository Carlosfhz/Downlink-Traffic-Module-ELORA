#!/usr/bin/expect -f
set password [lindex $argv 0]  ;# Take password as an argument
set file [lindex $argv 1]   ;# Number of devices from argument
set devices [lindex $argv 2]   ;# Number of devices from argument
set period [lindex $argv 3]   ;# Number of devices from argument
set gateways [lindex $argv 4]   ;# Number of devices from argument
set seed [lindex $argv 5]   ;# Number of devices from argument
set title [lindex $argv 6]   ;# Number of devices from argument
set Percent [lindex $argv 7] ;# Number of devices from argument

set timeout -1

spawn ./ns3 run --enable-sudo "$file --log --test --devices=$devices --period=$period --gateways=$gateways -seed=$seed --title=$title --perConfirmed=$Percent"
#spawn ./ns3 run --enable-sudo "$file --log --test --devices=$devices --period=$period --gateways=$gateways --title=$title --seed=$seed"
#spawn ./ns3 run --enable-sudo "elora-example-TTN --log --test --devices=$devices --period=$period --gateways=$gateways --title=$title --seed=$seed"
#spawn ./ns3 run --enable-sudo "forwarder-test-example --log --gateways=$gateways"

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

