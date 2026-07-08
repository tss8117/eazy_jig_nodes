#!/usr/bin/env python3
"""
MCP23S17 SPI helper for the EAZY JIG.

Shared by multiple Node-RED subflows: Check Relay, Digital Input Read,
Digital Output, JIG Board Controls. Each subflow's exec node calls this
helper with the appropriate arguments.

Usage:
    mcp23s17_helper.py write --chip <0-7> --pin <0-15> --value <0|1>
    mcp23s17_helper.py read  --chip <0-7> --pin <0-15>

Prints a JSON result on stdout. Exit code 0 on success, non-zero on failure.

Requires: spidev (pip install spidev), Pi with SPI0 enabled.
"""

import argparse
import json
import sys
import time

try:
    import spidev
except ImportError:
    print(json.dumps({"success": False, "error": "spidev module not installed. Install with: pip install spidev"}))
    sys.exit(1)

# MCP23S17 registers (BANK=0 mode, default after reset).
IODIRA = 0x00  # I/O direction, port A
IODIRB = 0x01  # I/O direction, port B
GPIOA  = 0x12  # port A read/write
GPIOB  = 0x13  # port B read/write
OLATA  = 0x14  # output latch, port A
OLATB  = 0x15  # output latch, port B

SPI_BUS = 0
SPI_DEVICE = 0     # CE0 — all 5 MCP23S17 chips share this per the block diagram
SPI_SPEED_HZ = 1_000_000

def open_spi():
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEVICE)
    spi.max_speed_hz = SPI_SPEED_HZ
    spi.mode = 0
    return spi

def read_reg(spi, chip_addr, register):
    # MCP23S17 opcode: 0x40 | (addr << 1) | R/W bit (1 = read)
    opcode = 0x40 | (chip_addr << 1) | 0x01
    result = spi.xfer2([opcode, register, 0x00])
    return result[2]

def write_reg(spi, chip_addr, register, value):
    opcode = 0x40 | (chip_addr << 1) | 0x00  # 0 = write
    spi.xfer2([opcode, register, value & 0xFF])

def pin_to_port_bit(pin):
    """Convert 0-15 pin to (port_letter, bit)."""
    if pin < 8:
        return "A", pin
    return "B", pin - 8

def do_write(chip, pin, value):
    port, bit = pin_to_port_bit(pin)
    latch_reg = OLATA if port == "A" else OLATB
    dir_reg = IODIRA if port == "A" else IODIRB
    spi = open_spi()
    try:
        # Make sure pin is configured as output (0 in IODIR = output for MCP23S17).
        current_dir = read_reg(spi, chip, dir_reg)
        new_dir = current_dir & ~(1 << bit)
        if new_dir != current_dir:
            write_reg(spi, chip, dir_reg, new_dir)
        # Update output latch to new value.
        current_latch = read_reg(spi, chip, latch_reg)
        if value:
            new_latch = current_latch | (1 << bit)
        else:
            new_latch = current_latch & ~(1 << bit)
        write_reg(spi, chip, latch_reg, new_latch)
        return {"success": True, "chip": chip, "pin": pin, "commanded": value, "port": port, "bit": bit}
    finally:
        spi.close()

def do_read(chip, pin):
    port, bit = pin_to_port_bit(pin)
    dir_reg = IODIRA if port == "A" else IODIRB
    gpio_reg = GPIOA if port == "A" else GPIOB
    spi = open_spi()
    try:
        # Make sure pin is configured as input (1 in IODIR = input).
        current_dir = read_reg(spi, chip, dir_reg)
        new_dir = current_dir | (1 << bit)
        if new_dir != current_dir:
            write_reg(spi, chip, dir_reg, new_dir)
            # Give the chip a moment to sample after direction change.
            time.sleep(0.001)
        # Read the GPIO port and extract the bit.
        port_value = read_reg(spi, chip, gpio_reg)
        pin_value = (port_value >> bit) & 0x01
        return {"success": True, "chip": chip, "pin": pin, "actual": pin_value, "port": port, "bit": bit}
    finally:
        spi.close()

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    write_parser = sub.add_parser("write")
    write_parser.add_argument("--chip", type=int, required=True, help="Chip hardware address (0-7)")
    write_parser.add_argument("--pin", type=int, required=True, help="Pin number 0-15")
    write_parser.add_argument("--value", type=int, required=True, choices=[0, 1], help="0 or 1")

    read_parser = sub.add_parser("read")
    read_parser.add_argument("--chip", type=int, required=True, help="Chip hardware address (0-7)")
    read_parser.add_argument("--pin", type=int, required=True, help="Pin number 0-15")

    args = parser.parse_args()

    try:
        if args.command == "write":
            result = do_write(args.chip, args.pin, args.value)
        elif args.command == "read":
            result = do_read(args.chip, args.pin)
        print(json.dumps(result))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "type": type(e).__name__}))
        sys.exit(1)

if __name__ == "__main__":
    main()
