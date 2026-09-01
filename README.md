# Downlink Traffic Analysis and Experiment Automation for ELoRa Based Framework

## Complementary ELoRa Emulator and ns-3 Simulator Files for Enhanced LoRaWAN Downlink Study

These files extend the ELoRa emulator and the ns-3 simulator with a more complete traffic analysis module. The module captures the path of downlink traffic at three essential points:

- **Network server.** Extracts events related to downlink packet scheduling and failures. This part supports The Things Stack only.
- **Interface between the network server and the gateway.** Captures the UDP packets exchanged between the two components to trace their communication.
- **ns-3 simulator.** Extends the ns-3 logging system to expose additional information on downlink transmission and reception inside the simulator.

The repository also includes an automation module that standardizes the emulation inputs and runs series of experiments unattended.

---

## Repository structure


```
.
├── PATCH_FILES/                    files overlaid onto contrib/elora/helper
│   ├── lora-packet-tracker.cc
│   ├── lora-packet-tracker.h
│   ├── lorawan-mac-helper.cc
│   └── lorawan-mac-helper.h
├── auto_run.py                     experiment launcher
├── install_patch.sh                installs the overlay
├── uninstall_patch.sh              restores the upstream files
└── examples/
    └── elora-example-two-channels.cc
```

---

## Prerequisites

- A running instance of the [ELoRa emulation tool](https://github.com/Orange-OpenSource/elora).
- A running network server, either [The Things Stack](https://www.thethingsindustries.com/docs/) or [ChirpStack](https://www.chirpstack.io/).
- Python 3.10.12

- The following Python packages:

```bash
pip install pycryptodome requests scapy
```

**Version compatibility.** The files in `PATCH_FILES/` are complete replacements for their upstream
counterparts, not incremental patches, so they are tied to the revisions below.

| Component        | Version / commit |
|------------------|------------------|
| ns-3             | 3.48             |
| ELoRa            | 0.3.0            |
| The Things Stack | 3.36.1           |
| ChirpStack       | 4.19.0           |
| Python           | 3.10.12          |

---

## Installation

```bash
cd ~/ns-3-dev
git clone https://gitlab.com/Carlosfhz/Downlink-Traffic-Module-ELORA.git
cd Downlink-Traffic-Module-ELORA
chmod +x install_patch.sh
./install_patch.sh ~/ns-3-dev
cd ~/ns-3-dev
./ns3 build
```

The script copies the files from `PATCH_FILES/` into `contrib/elora/helper/`, saving the original versions in `.backup/` first. To restore the upstream files:

```bash
./install_patch.sh ~/ns-3-dev --dry-run   # preview without writing
./uninstall_patch.sh ~/ns-3-dev           # restore the originals
```

**If the original `lorawan` module is also installed.** ELoRa is derived from the signetlabdei `lorawan` module and shares these filenames with it. The two conflict when built together, and the build may compile the wrong copy. Reconfigure so that only ELoRa is built:

```bash
./ns3 clean
./ns3 configure --enable-modules "elora;tap-bridge;csma"
./ns3 build
```

---

## Usage

### Configuring the topology

`auto_run.py` defines the topology of the emulated network through the following parameters:

- `GW_number`: number of gateways.
- `array`: number of end devices.
- `seed`: initial seed for random events.
- `period_array`: period, or average period, in seconds between uplink transmissions. The interpretation depends on the traffic type configured in the ns-3 LoRaWAN module.
- `percentage_array`: percentage of end devices using confirmed traffic. Confirmed traffic must also be enabled inside the ns-3 simulator.
- `n_runs`: number of repetitions per topology. The seed changes on each iteration.

Example:

```python
GW_number = [4]
array = [100, 400]
seed = 250
period_array = [360]
percentage_array = [50]
n_runs = 10
```

This configures two topologies — 100 and 400 end devices, both with 4 gateways — with a 360 s uplink period and 50% of the end devices using confirmed traffic. Each topology is emulated 10 times, for 20 runs in total.

### Launching the experiments

```bash
python3 auto_run.py <experiment_name> <network_server>
```

- `experiment_name`: prefix used to identify the output files.
- `network_server`: either `Chirpstack` or `TTS`.



### Tracking functions

`elora-example-two-channels.cc` shows how to call the tracking functions introduced by this module:

```cpp
ss << title << "_EndDevicesOut" << ".csv";
helper.DoPrintDeviceStatus(endDevices, gateways, ss.str());

ss3 << title << "_log_uplinks" << ".csv";
tracker.LogUplinks(Seconds(0), Hours(1) * periods, gateways, endDevices, ss3.str());
```

- `DoPrintDeviceStatus`: writes a CSV file with per-device statistics on all uplink packets transmitted, confirmed and unconfirmed, and on all acknowledgments transmitted and received.
- `LogUplinks`: writes a CSV file detailing every uplink and downlink packet.

---



## Troubleshooting

**The build does not pick up the changes.** Confirm that the files were actually replaced and that ELoRa is in the enabled module list:

```bash
git -C ~/ns-3-dev/contrib/elora status --short
```

**Multiple ns-3 trees.** `install_patch.sh` prints the destination path before copying anything. Check that it matches the tree you intend to build.


---






