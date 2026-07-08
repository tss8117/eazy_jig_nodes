#!/usr/bin/env python3
"""
Generic SPI helper for the EAZY JIG.

Called by the Node-RED SPI Read/Write subflow via exec. Handles arbitrary
SPI transfers on the Pi's SPI0 bus.

Usage:
    spi_helper.py --ce <0|1> --speed <hz> --mode <0-3> --tx '<hex_bytes>' --rx-length <n>

Where <hex_bytes> is a comma-separated list of hex values, e.g. '0x02,0x00,0x2A'.
Rx bytes are read after the tx completes; total transfer length is len(tx) + rx_length.

Prints a JSON result on stdout. Exit code 0 on success.

Requires: spidev (pip install spidev), Pi with SPI0 enabled.
"""

import argparse
import json
import sys

try:
    import spidev
except ImportError:
    print(json.dumps({"success": False, "error": "spidev module not installed. pip install spidev"}))
    sys.exit(1)

def parse_hex_list(s):
    if not s:
        return []
    return [int(x, 0) & 0xFF for x in s.split(",") if x.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ce", type=int, required=True, choices=[0, 1])
    ap.add_argument("--speed", type=int, default=1_000_000)
    ap.add_argument("--mode", type=int, default=0, choices=[0, 1, 2, 3])
    ap.add_argument("--tx", type=str, default="")
    ap.add_argument("--rx-length", type=int, default=0)
    args = ap.parse_args()

    try:
        tx_bytes = parse_hex_list(args.tx)
        rx_pad = [0x00] * args.rx_length
        transfer = tx_bytes + rx_pad

        spi = spidev.SpiDev()
        spi.open(0, args.ce)
        spi.max_speed_hz = args.speed
        spi.mode = args.mode
        result = spi.xfer2(transfer)
        spi.close()

        # rx bytes are the tail of the transfer.
        rx = result[len(tx_bytes):] if args.rx_length > 0 else []
        print(json.dumps({
            "success": True,
            "rx": [f"0x{b:02X}" for b in rx],
            "rx_raw": rx
        }))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "type": type(e).__name__}))
        sys.exit(1)

if __name__ == "__main__":
    main()
