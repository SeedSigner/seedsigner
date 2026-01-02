# SeedSigner Display Setup Guide

This guide covers setting up SeedSigner with different displays.

## Supported Displays

| Display | Config File | Overlays Required |
|---------|-------------|-------------------|
| Waveshare 1.3" SPI LCD (240x240) | `config_spi13.txt` | None (standard) |
| Waveshare 2.8" DPI LCD (480x640) | `config_dpi28.txt` | Yes |

## Hardware

- Raspberry Pi Zero (or Zero W/2W)
- Waveshare display (1.3" SPI or 2.8" DPI)
- Compatible camera module

---

## 1.3" SPI Display Setup (Standard)

### Steps

1. Flash SeedSignerOS image to SD card
2. Copy `config_spi13.txt` → `config.txt` on boot partition
3. Boot

No additional overlays needed - this is the standard SeedSigner display.

---

## 2.8" DPI Touchscreen Setup

### Steps

1. Flash SeedSignerOS image to SD card
2. Copy `config_dpi28.txt` → `config.txt` on boot partition
3. Copy `cmdline_dpi28.txt` → `cmdline.txt` on boot partition
4. Copy overlay files from `overlays_dpi28/` to `overlays/` folder:
   - `waveshare-28dpi-3b-4b.dtbo`
   - `waveshare-28dpi-3b.dtbo`
   - `waveshare-touch-28dpi.dtbo`
5. Boot

### Quick Setup (Linux/Mac)

```bash
cp config_dpi28.txt /path/to/boot/config.txt
cp cmdline_dpi28.txt /path/to/boot/cmdline.txt
cp overlays_dpi28/*.dtbo /path/to/boot/overlays/
```

---

## Troubleshooting

### DPI28: Display shows wrong colors (red/blue swapped)

The `dpi_output_format` value is wrong. Ensure it's set to `0x7F206` (not `0x7F216`).

### DPI28: Touch not working

1. Check I2C is enabled: `dtparam=i2c_arm=on` in config.txt
2. Verify touch device exists: `ls /sys/class/input/event*/device/name`

### DPI28: Display not detected

Ensure overlay files are copied to the `overlays/` folder.

---

## Files

- `config_spi13.txt` - Config for 1.3" SPI display (standard)
- `config_dpi28.txt` - Config for 2.8" DPI touchscreen
- `cmdline_dpi28.txt` - Cmdline for DPI28 (hides console cursor)
- `overlays_dpi28/` - Waveshare DPI overlay files
- `setup_dpi28.sh` - Script to fix dpi_output_format on existing setup
