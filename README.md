# EAZY JIG — Node-RED Nodes

Reusable Node-RED subflows and Python helpers for building the EAZY JIG generic PCB test framework on a Raspberry Pi.

Repository: [github.com/tss8117/eazy_jig_nodes](https://github.com/tss8117/eazy_jig_nodes)

---

## Contents

1. [What this is](#what-this-is)
2. [Repository layout](#repository-layout)
3. [Architecture layers](#architecture-layers)
4. [Setting up a Raspberry Pi](#setting-up-a-raspberry-pi)
5. [Importing into Node-RED](#importing-into-node-red)
6. [Building a test flow](#building-a-test-flow)
7. [Node reference](#node-reference)
8. [Data shapes](#data-shapes)
9. [Built vs scaffolded](#built-vs-scaffolded)
10. [Troubleshooting](#troubleshooting)

---

## What this is

EAZY JIG is a Raspberry Pi-based test framework that replaces the older per-product STM32 JIG board approach. The Pi drives external ICs (MCP23S17 SPI expanders, ADS1115 ADC, small STM32 co-processor for frequency measurement) and orchestrates the full test cycle in Node-RED.

Each file in this repository is either a Node-RED subflow (`.json`) or a Python helper script (`.py`). Import the subflows into Node-RED, copy the helpers to the Pi, and wire together a test flow appropriate to your product.

The framework covers the full test scope from the EAZY JIG requirements: 64 digital inputs, 16 relays, DC voltage and current measurement, AC calibration, RS-485 / RS-232 / UART, SPI-based ADE metering, RTC crystal frequency, and firmware programming for STM32, CC1310, ESP32, and SIMCOM controllers on the DUT.

## Repository layout

All files sit at the top level (flat structure — no subfolders):

```
eazy_jig_nodes/
├── README.md                              ← This file
│
├── mcp23s17_helper.py                     ← Shared Python helper for SPI expanders
├── spi_helper.py                          ← Shared Python helper for generic SPI
│
├── check_relay.json                       ← Compound test operations (main flow)
├── check_zone.json
├── check_peripheral.json
├── ads1115_adc_read.json
│
├── program_bootloader.json                ← Three-stage firmware programming
├── program_test_firmware.json
├── program_final_firmware.json
├── cc1310_flash.json                      ← Other controller flashing (scaffolds)
├── esp32_flash.json
├── simcom_flash.json
│
├── qr_scanner_input.json                  ← Workflow and UI nodes
├── rtc_set_to_dut.json
├── operator_control_panel.json
├── test_status_cards.json
├── overall_verdict_aggregator.json
├── local_result_logger.json
├── uid_mac_write.json
│
├── esp_wifi_test.json                     ← DUT-connectivity tests (scaffolds)
├── 4g_test.json
├── ac_calibration.json
├── frequency_coprocessor_read.json
├── dut_reports_result.json
│
├── digital_input_read.json                ← Atomic subflows (internal use)
├── digital_output.json
├── jig_board_controls.json
├── i2c_read_write.json
├── spi_read_write.json
└── serial_protocol.json
```

## Architecture layers

Three layers, from bottom to top. Understanding these matters because it determines which nodes go directly in the main flow versus which stay hidden inside other subflows.

**Layer 1 — Python helpers.** Two small scripts that do the actual hardware talk. Node-RED calls them via `exec`. This layer exists because Node-RED does not have great built-in support for MCP23S17 SPI expanders, and because putting SPI/GPIO logic in Python is easier to debug than a Node-RED function node.

- `mcp23s17_helper.py` — reads and writes MCP23S17 pins over SPI0
- `spi_helper.py` — arbitrary SPI transfers on SPI0

**Layer 2 — Atomic subflows.** Small subflows that wrap one primitive operation. These are the building blocks for the compound subflows above them. **Do not drop these directly into a main flow** — they clutter the flow with plumbing detail. Use them only when building new compound subflows.

- `digital_input_read.json`, `digital_output.json`, `jig_board_controls.json`
- `i2c_read_write.json`, `spi_read_write.json`, `serial_protocol.json`

**Layer 3 — Compound subflows.** Semantically meaningful test operations. **These are what you wire into a main flow.** Each one does something an engineer or operator can name — "check this relay", "measure this voltage", "flash the bootloader".

Rule of thumb: if it does one meaningful thing an engineer can name, it belongs in the main flow. If it just moves bits around, it stays inside a compound.

## Setting up a Raspberry Pi

Complete step-by-step for a fresh Raspberry Pi OS install.

### 1. Enable required interfaces

```bash
sudo raspi-config
```

Under **Interface Options**, enable:
- **SPI** — required for MCP23S17 expanders
- **I2C** — required for ADS1115 ADC and any I2C device
- **Serial Port** — enable but *disable* the serial console when asked, so UART0 is free for real work

Reboot when prompted.

### 2. Install system dependencies

```bash
sudo apt update
sudo apt install -y openocd i2c-tools python3-pip nodejs
```

Verify:

```bash
openocd --version    # Open On-Chip Debugger 0.11.0 or newer
i2cdetect -y 1       # Prints an address grid
python3 --version    # 3.9 or newer
node --version       # v18 or newer
```

### 3. Install Node-RED

If Node-RED is not already on the Pi:

```bash
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
```

Enable and start it as a service:

```bash
sudo systemctl enable nodered.service
sudo systemctl start nodered.service
```

Confirm by browsing to `http://<pi-ip-address>:1880` from any device on the same network.

### 4. Install Python dependency

```bash
sudo pip3 install spidev --break-system-packages
```

The `--break-system-packages` flag is required on Raspberry Pi OS bookworm and later. Drop it on older versions.

### 5. Install Node-RED community packages

In the Node-RED editor: menu (top right) → **Manage palette** → **Install** tab. Install:

- `node-red-node-serialport` — direct serial support
- `node-red-contrib-ads1x15` — ADS1115 ADC support

If you plan to use dashboards for the Operator Control Panel and Test Status Cards, also install one dashboard package (not both):

- `node-red-dashboard` (Dashboard v1), or
- `@flowfuse/node-red-dashboard` (Dashboard v2)

### 6. Copy the Python helpers to the Pi

On the Pi:

```bash
mkdir -p /home/pi/eazy_jig
```

From your development machine (or clone the repo directly on the Pi):

```bash
scp mcp23s17_helper.py pi@<pi-ip>:/home/pi/eazy_jig/
scp spi_helper.py      pi@<pi-ip>:/home/pi/eazy_jig/
```

On the Pi, make them executable:

```bash
chmod +x /home/pi/eazy_jig/*.py
```

Quick sanity test:

```bash
python3 /home/pi/eazy_jig/mcp23s17_helper.py read --chip 0 --pin 0
```

Should print a JSON success or a clear error. If it hangs or prints nothing, SPI is not correctly enabled — return to step 1.

## Importing into Node-RED

You can either clone the repo and import the `.json` files, or paste each one directly.

### Option A — Clone the repo

```bash
git clone https://github.com/tss8117/eazy_jig_nodes.git
```

Then in the Node-RED editor, use menu → **Import** → **select a file to import** for each `.json` file.

### Option B — Paste directly

Open each `.json` file on GitHub, click the **Copy raw contents** button, and paste into the Node-RED **Import** dialog.

Either way, once imported each subflow shows up in the palette on the left under a category called `eazy`. Drag and drop like any other node.

**Tip:** import all 28 subflows in one session, then Deploy once. The palette becomes fully populated for building flows.

## Building a test flow

A minimal working test cycle looks like this:

```
Operator Control Panel
  → Turn On DUT (JIG Board Controls: control_name=dut_power, value=1)
  → Program Bootloader
  → Program Test Firmware
  → Check Peripheral × N       (once per peripheral: EEPROM, RTC, etc.)
  → Check Zone × N             (once per digital input zone)
  → Check Relay × N            (once per relay)
  → ADS1115 ADC Read × N       (once per voltage rail)
  → Overall Verdict Aggregator
  → (branch) if PASS → Program Final Firmware
  → Local Result Logger
  → Show Pass/Fail Indicator (JIG Board Controls: control_name=green_led or red_led)
  → Turn Off DUT (JIG Board Controls: control_name=dut_power, value=0)
```

Each node in the chain is a subflow instance. Configure per-instance via the env vars shown when you double-click the instance.

For results display, add a parallel path branching from each Check node to a Test Status Cards subflow, then to a dashboard `ui_template` node in the main flow (the `ui_template` node cannot live inside a subflow due to Dashboard v1 limitations).

## Node reference

Nodes are grouped by role. **BUILT** means the node fully works. **SCAFFOLD** means the node returns a well-formed `not yet implemented` response and is waiting on an external decision (usually from the firmware team). Scaffolds are still importable and wireable — they just refuse to do real work.

### Compound test operations (main flow)

| File | Purpose | Status | Notes |
|---|---|---|---|
| `check_relay.json` | Drive one relay ON, verify, drive OFF, verify | BUILT | Full ON/OFF cycle with configurable settle time. Uses `mcp23s17_helper.py`. |
| `check_zone.json` | Read one digital input zone, compare to expected value | BUILT | Compares actual state to expected, returns PASS or FAIL. |
| `check_peripheral.json` | Ask the DUT to self-test one peripheral | SCAFFOLD | Waiting on per-DUT protocol for query and response. |
| `ads1115_adc_read.json` | Read one voltage from an ADS1115 channel | BUILT | Requires `node-red-contrib-ads1x15` community package. |

### Firmware programming — three-stage DUT sequence

Each of the three stages is now a distinct main-flow node. This matches the actual firmware flow: bootloader is flashed first, then test firmware runs the tests, then final production firmware is flashed only if tests pass.

| File | Purpose | Status | Notes |
|---|---|---|---|
| `program_bootloader.json` | Flash the bootloader .hex to the STM32 on the DUT | BUILT | First stage. Wraps openocd via ST-Link. |
| `program_test_firmware.json` | Flash the diagnostic / test firmware | BUILT | Second stage. This firmware runs the on-DUT self-tests. |
| `program_final_firmware.json` | Flash the production firmware (after tests pass) | BUILT | Third stage. Only fired if the aggregated verdict is PASS. |

### Other controller flashing

| File | Purpose | Status | Notes |
|---|---|---|---|
| `cc1310_flash.json` | Flash a TI CC1310 on the DUT | SCAFFOLD | Waiting on tool choice (openocd via XDS110, or TI UniFlash). |
| `esp32_flash.json` | Flash an ESP32 on the DUT via esptool | SCAFFOLD | Waiting on the four-file flash address layout. |
| `simcom_flash.json` | Flash a SIMCOM cellular module on the DUT | SCAFFOLD | Waiting on decision whether flashed on-line, and if so which tool. |

### Workflow and UI (main flow)

| File | Purpose | Status | Notes |
|---|---|---|---|
| `qr_scanner_input.json` | Receive scanned code from a USB QR gun | BUILT | Validates scanned value against a configurable regex. |
| `rtc_set_to_dut.json` | Send Pi's current time to the DUT | BUILT | Command template is configurable per product. |
| `operator_control_panel.json` | Validate operator input (product, serial, MAC, mode) | BUILT | Actual dashboard nodes live in the main flow; this subflow validates and emits. |
| `test_status_cards.json` | Format a category slice for dashboard display | BUILT | Prepares data for a `ui_template` node in the main flow. |
| `overall_verdict_aggregator.json` | Combine per-item results into overall PASS or FAIL | BUILT | Any non-PASS makes the overall FAIL. |
| `local_result_logger.json` | Append test result to JSONL file on the Pi | BUILT | One file per day; results stay local, nothing uploaded. |
| `uid_mac_write.json` | Write serial / MAC to DUT storage | SCAFFOLD | Waiting on per-controller storage protocol. |

### DUT-connectivity tests (main flow)

| File | Purpose | Status | Notes |
|---|---|---|---|
| `esp_wifi_test.json` | Verify ESP32 connects to test WiFi AP | SCAFFOLD | Waiting on test-line WiFi AP and debug UART parse format. |
| `4g_test.json` | Verify SIMCOM module registers with cellular network | SCAFFOLD | Waiting on cellular signal or simulator at test line. |
| `ac_calibration.json` | Coordinate AC calibration with phase relays | SCAFFOLD | Waiting on calibrator source decision and DUT reporting protocol. |
| `frequency_coprocessor_read.json` | Read frequency measurement from the STM32 co-processor | SCAFFOLD | Waiting on co-processor firmware register map. |
| `dut_reports_result.json` | Ask the DUT for pass/fail on a self-test | SCAFFOLD | Waiting on per-DUT protocol for query and response. |

### Atomic subflows (internal use — do not drop into main flow)

| File | Purpose | Status | Notes |
|---|---|---|---|
| `digital_input_read.json` | Read one MCP23S17 pin | BUILT | Uses `mcp23s17_helper.py`. |
| `digital_output.json` | Write one MCP23S17 pin | BUILT | DUT-facing outputs only. Uses `mcp23s17_helper.py`. |
| `jig_board_controls.json` | Actuate one JIG-side relay (DUT power, LEDs, calibration) | BUILT | Pin map is configurable per instance. |
| `i2c_read_write.json` | I2C register read or write | BUILT | Uses `i2cget` and `i2cset` from `i2c-tools`. |
| `spi_read_write.json` | Arbitrary SPI transfer | BUILT | Uses `spi_helper.py`. |
| `serial_protocol.json` | Send/receive over UART, RS-232, or RS-485 | BUILT | Uses `stty` and `timeout` via exec (no community package required). |

## Data shapes

Consistent output shapes across all nodes make wiring the main flow predictable.

**All BUILT nodes emit `msg.payload` as an object with at least these fields:**

```json
{
  "success": true,
  "timestamp": "2026-07-08T13:47:22.123Z"
}
```

Plus operation-specific fields. For example, `check_relay` adds `relay_name`, `status` (PASS or FAIL), `on_check`, and `off_check`. The three firmware programming nodes add `stage` (`bootloader`, `test_firmware`, or `final_firmware`), `hex_path`, `elapsed_ms`, `exit_code`, and a short `log` tail.

**All SCAFFOLD nodes emit:**

```json
{
  "success": false,
  "scaffold": true,
  "error": "<what the node is waiting on>",
  "timestamp": "2026-07-08T13:47:22.123Z"
}
```

The `scaffold: true` field is intentional — downstream nodes (aggregator, logger) can detect scaffolds and either display them differently or skip them, without treating them as real failures.

**The Overall Verdict Aggregator expects an array of results.** It looks at each item's `status` field. Any non-PASS is counted as a fail, including SCAFFOLD outputs.

## Built vs scaffolded

Summary count:

- **19 built** — three firmware programming stages, `check_relay`, `check_zone`, `ads1115_adc_read`, all 6 atomic subflows (Layer 2), all 6 workflow / UI nodes, plus the QR scanner and RTC set nodes
- **9 scaffolded** — CC1310, ESP32, SIMCOM flash; `check_peripheral`, `dut_reports_result`, `uid_mac_write`, `esp_wifi_test`, `4g_test`, `ac_calibration`, `frequency_coprocessor_read`

The scaffolds are not blocked by our code. They are blocked by:

- Firmware team decisions on which flashing tool to use (CC1310, SIMCOM)
- Firmware team decisions on the DUT reporting protocol (check_peripheral, dut_reports_result, uid_mac_write)
- Facility decisions on WiFi AP and cellular signal availability (esp_wifi_test, 4g_test)
- Hardware confirmation of AC calibrator interface (ac_calibration)
- Frequency co-processor firmware register map (frequency_coprocessor_read)

When a blocker resolves, the scaffold gets replaced with a real subflow. If the new subflow keeps the same input and output shape, no other node in any main flow needs to change.

## Troubleshooting

**"Missing node types" banner after import.** Something needs a community package that is not installed. Check which node type Node-RED is complaining about, install the corresponding package via the palette manager, and redeploy. Most common cause: `ads1x15-adc` needs `node-red-contrib-ads1x15`.

**Helper script errors like `Permission denied` or `cannot access /dev/spidev0.0`.** The user running Node-RED needs SPI and I2C permissions. If Node-RED runs as `pi`:

```bash
sudo usermod -aG spi,i2c,dialout pi
sudo systemctl restart nodered
```

**Helper script errors like `no module named spidev`.** Reinstall the Python package:

```bash
sudo pip3 install spidev --break-system-packages
```

**Serial Protocol node gets no response.** Check the DUT is connected, the port name (`/dev/ttyAMA0`, `/dev/ttyUSB0`, etc.) matches the wiring, and the baud rate matches what the DUT expects. Also verify the Pi is using the PL011 UART, not the mini-UART (which drifts). Add `dtoverlay=disable-bt` to `/boot/config.txt` to force UART0 onto GPIO 14/15.

**Dashboard nodes don't appear or don't update.** Confirm exactly one dashboard package is installed (either v1 or v2, not both). Check that each dashboard node is assigned to a Group, which is assigned to a Tab.

**A scaffold node fires in the flow and I don't want it to.** Scaffold nodes fire because they're wired in. If you don't want a scaffold to run yet, remove the wire feeding it. The scaffold sits unwired in the palette until its blockers resolve.

---

Questions or issues, contact Siddharth Sheth.
