# Waveshare 2.8" DPI LCD Setup for SeedSigner

This guide covers setting up SeedSigner with the Waveshare 2.8" DPI touchscreen display (480x640).

## Hardware

- Raspberry Pi Zero (or Zero W/2W)
- Waveshare 2.8" DPI LCD (SKU: 18292)
- Compatible camera module

## Setup Steps

### 1. Flash SeedSignerOS

Download and flash the SeedSignerOS image to your SD card using Raspberry Pi Imager or similar tool.

### 2. Configure Display

Before first boot, mount the SD card's boot partition and copy the config files:

**On Windows:**
- Open the boot partition in File Explorer
- Copy `config_dpi28.txt` → `config.txt`
- Copy `cmdline_dpi28.txt` → `cmdline.txt`

**On Linux/Mac:**
```bash
cp config_dpi28.txt /path/to/boot/config.txt
cp cmdline_dpi28.txt /path/to/boot/cmdline.txt
cp overlays_dpi28/*.dtbo /path/to/boot/overlays/
```

### 3. Copy Overlay Files

Copy the Waveshare overlay files from `overlays_dpi28/` to the SD card's `overlays/` folder:
- `waveshare-28dpi-3b-4b.dtbo`
- `waveshare-28dpi-3b.dtbo`
- `waveshare-touch-28dpi.dtbo`

### 4. First Boot

Insert the SD card and power on. The display should show the SeedSigner interface with touch enabled.

## Troubleshooting

### Display shows wrong colors (red/blue swapped)

The `dpi_output_format` value is wrong. Ensure it's set to `0x7F206` (not `0x7F216`).

You can fix this by running the included script:
```bash
sudo ./setup_dpi28.sh
sudo reboot
```

### Touch not working

Touch should auto-detect. If not working:

1. Check I2C is enabled: `dtparam=i2c_arm=on` in config.txt
2. Verify touch device exists: `ls /sys/class/input/event*/device/name`
3. Set environment variable: `export SEEDSIGNER_TOUCH=1`

### Display not detected

Ensure these lines are in config.txt:
```
dtoverlay=vc4-kms-dpi-generic
dpi_group=2
dpi_mode=87
```

## Files

- `config_dpi28.txt` - Complete config.txt for DPI28 display
- `cmdline_dpi28.txt` - Complete cmdline.txt (hides console cursor)
- `overlays_dpi28/` - Waveshare DPI overlay files
- `setup_dpi28.sh` - Script to fix dpi_output_format on existing setup
