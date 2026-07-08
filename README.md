# EAZY JIG — Node-RED Nodes (Real Versions)

One file per node. Import each into Node-RED (Menu → Import → paste file contents).
Each imports as a subflow named for the node. Configure per instance via env vars.

## Legend

- **BUILT** — implemented and testable. Downstream flows can rely on the output shape.
- **SCAFFOLD** — placeholder returning `{ success: false, scaffold: true, error: '...' }`. Downstream flows should treat this as a known missing dependency, not a mystery failure.

## Shared prerequisites

Three helper files live in the parent `outputs/` folder alongside the `nodes/` folder:

- `mcp23s17_helper.py` — used by Check Relay, Digital Input Read, Digital Output, JIG Board Controls
- `spi_helper.py` — used by SPI Read/Write
- (No helper needed for ADS1115 — uses `node-red-contrib-ads1x15` community package)

Deploy the helpers to `/home/pi/eazy_jig/` on the Pi (or override the `helper_path` env var per subflow instance). Run `chmod +x` on both and `pip install spidev`.

## Nodes by group

### Group 1 — Controller flashing

| File | Node | Status | Notes |
|---|---|---|---|
| `stm32_flash.json` | STM32 Flash | BUILT | Wraps openocd with ST-Link. Tested pattern from existing utility. |
| `cc1310_flash.json` | CC1310 Flash | SCAFFOLD | Waiting on firmware team to confirm openocd vs UniFlash. |
| `esp32_flash.json` | ESP32 Flash | SCAFFOLD | Waiting on firmware team for four-file addresses. |
| `simcom_flash.json` | SIMCOM Flash | SCAFFOLD | Waiting on decision whether flashed on-line, and which tool. |

### Group 2 — Communication protocols

| File | Node | Status | Notes |
|---|---|---|---|
| `serial_protocol.json` | Serial Protocol | BUILT | Covers RS-485, RS-232, UART. Uses stty + timeout via exec (portable, no community package required). |
| `i2c_read_write.json` | I2C Read/Write | BUILT | Uses `i2cget`/`i2cset` from `i2c-tools`. |
| `spi_read_write.json` | SPI Read/Write | BUILT | Uses the `spi_helper.py` script. |
| `dut_reports_result.json` | DUT Reports Result | SCAFFOLD | Waiting on per-DUT protocol for query/response. |

### Group 3 — Hardware I/O and measurement

| File | Node | Status | Notes |
|---|---|---|---|
| `digital_input_read.json` | Digital Input Read | BUILT | MCP23S17 via helper. |
| `digital_output.json` | Digital Output | BUILT | MCP23S17 via helper. DUT-facing outputs only. |
| `jig_board_controls.json` | JIG Board Controls | BUILT | DUT power, LEDs, calibration relays, etc. Pin map is configurable per instance. |
| `ads1115_adc_read.json` | ADS1115 ADC Read | BUILT | Requires `node-red-contrib-ads1x15`. |
| `check_relay.json` | Check Relay | BUILT | Full ON/OFF cycle with settle time. Uses MCP23S17 helper. |
| `frequency_coprocessor_read.json` | Frequency Read | SCAFFOLD | Waiting on co-processor firmware register map. |
| `ac_calibration.json` | AC Calibration | SCAFFOLD | Waiting on calibrator source decision and DUT reporting protocol. |

### Group 4 — Workflow

| File | Node | Status | Notes |
|---|---|---|---|
| `qr_scanner_input.json` | QR Scanner Input | BUILT | Validates scanned codes against configurable regex. |
| `rtc_set_to_dut.json` | RTC Set to DUT | BUILT | Reads Pi time, writes to DUT via configurable command template. |
| `operator_control_panel.json` | Operator Control Panel | BUILT | Validation + emit. Dashboard nodes go in the main flow (v1 subflow limitation). |
| `test_status_cards.json` | Test Status Cards | BUILT | Formats a category slice for ui_template rendering. |
| `overall_verdict_aggregator.json` | Overall Verdict Aggregator | BUILT | Combines results into PASS/FAIL summary. |
| `local_result_logger.json` | Local Result Logger | BUILT | Appends JSONL to a daily log file. |
| `uid_mac_write.json` | UID / MAC Write to DUT | SCAFFOLD | Waiting on per-controller storage protocol. |
| `esp_wifi_test.json` | ESP WiFi Test | SCAFFOLD | Waiting on test-line WiFi AP and debug UART parse format. |
| `4g_test.json` | 4G Connection Test | SCAFFOLD | Waiting on cellular signal / simulator at test line. |

## Summary

- 24 subflow files total across the four groups
- 13 built, 10 scaffolded, plus the ADS1115 (13 real + 10 scaffold + 1 = the ADS1115 was already built earlier so it's counted here as built)
- All scaffolds return a consistent `{ success: false, scaffold: true, error: '...' }` shape

## Usage pattern

Each node's `info` (visible in Node-RED when you open the subflow) documents its env vars, prerequisites, and output shape. When wiring the JIG flow:

1. Start from the Operator Control Panel subflow's output.
2. Chain nodes in the required test sequence (flash → configure → test → write UID → aggregate → log).
3. Wire per-category outputs into their Test Status Cards subflow, then into the dashboard's ui_template.
4. Feed the aggregated results into Overall Verdict Aggregator, then into Local Result Logger.

When a scaffolded node is hit, the flow continues cleanly — the scaffold produces a well-formed error payload that downstream nodes (aggregator, logger) handle without crashing.

## When scaffolds resolve

Replace the scaffold JSON with a proper built version. The subflow ID and env var names should be kept stable so any flow using the scaffold continues to work without rewiring.
