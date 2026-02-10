# Waveshare 2.8" DPI LCD Setup Guide

## Hardware
- Waveshare 2.8" DPI LCD (480x640, capacitive touch)
- Raspberry Pi Zero 2W (or other Pi with 40-pin GPIO)

## Display Configuration

### 1. Copy Overlay Files

Copy the DPI overlay file to the boot overlays folder:
```
/boot/overlays/waveshare-28dpi.dtbo
```

The overlay file can be obtained from Waveshare's wiki or the `overlays/` folder in this repo.

### 2. Edit config.txt

Add these lines to `/boot/config.txt`:

```ini
# Waveshare 2.8" DPI LCD
dtoverlay=waveshare-28dpi
overscan_left=0
overscan_right=0
overscan_top=0
overscan_bottom=0
framebuffer_width=480
framebuffer_height=640
enable_dpi_lcd=1
display_default_lcd=1
dpi_group=2
dpi_mode=87
dpi_output_format=0x7F206
hdmi_timings=480 0 26 16 10 640 0 16 2 14 0 0 0 60 0 32000000 3
dtparam=spi=off
dtparam=i2c_arm=on
```

### 3. Touch Input

The capacitive touch controller uses I2C. It should be auto-detected as `/dev/input/event*`.

To verify touch is working:
```bash
evtest /dev/input/event0
```

### 4. Auto-Detection

SeedSigner will auto-detect the DPI28 display by checking:
- Framebuffer size at `/sys/class/graphics/fb0/virtual_size` (should be `480,640`)
- Touch input via evdev multitouch capability

You can also force the display type with environment variables:
```bash
export SEEDSIGNER_DISPLAY=dpi28
export SEEDSIGNER_TOUCH=1
```

## Display Layout

```
+------------------+
|                  |
|    UI Area       |  480x480 (scaled from 240x240)
|    (touch)       |
|                  |
+------------------+
|  ▲  | SELECT | ▼ |  480x160 Touch Bar
+------------------+
```

## Troubleshooting

### No display output
- Check config.txt settings are correct
- Verify overlay file is in `/boot/overlays/`
- Check `/sys/class/graphics/fb0/virtual_size` shows `480,640`

### Touch not working
- Ensure `dtparam=i2c_arm=on` is in config.txt
- Check `ls /dev/input/event*` shows a device
- Run `evtest` to verify touch events

### Display colors inverted
- Try adding `display_rotate=2` to config.txt
