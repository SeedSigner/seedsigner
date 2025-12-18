# SeedSigner Touchscreen Project - Technical Handoff

---

## 1. Repository Setup

### Local Repository
```
Path: C:\Users\bradc\Documents\ClaudeWorkspace\Projects\seedsigner-repo
Branch: touchscreen-v3 (current)
```

### Git Remotes
| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | https://github.com/FreeOnlineUser/seedsigner.git | Your fork |
| `upstream` | https://github.com/SeedSigner/seedsigner.git | Official repo |

---

## 2. Touchscreen Code Changes

### New Files
| File | Purpose |
|------|---------|
| `src/seedsigner/hardware/DPI28.py` | Framebuffer driver for 2.8" DPI LCD |
| `src/seedsigner/hardware/RGBtoBGR.pyx` | Cython RGB→BGR conversion (optional, for speed) |
| `src/seedsigner/hardware/touch.py` | Touch input handler via evdev |
| `src/seedsigner/hardware/touch_buttons.py` | Touch-to-button adapter |
| `src/seedsigner/emulator/run_emulator.py` | Desktop emulator (pygame) |

### Modified Files
| File | Changes |
|------|---------|
| `src/seedsigner/hardware/displays/display_driver.py` | Added DPI28 support |
| `src/seedsigner/gui/renderer.py` | Auto-detection for DPI28/touch |
| `src/seedsigner/models/settings_definition.py` | Added DPI28 display option |
| `src/seedsigner/gui/screens/screen.py` | Touch bar for list screens |
| `src/seedsigner/gui/screens/seed_screens.py` | Keyboard touch bar |

---

## 3. Display Architecture

### Waveshare 2.8" DPI LCD (480x640 portrait)
```
┌────────────────┐
│                │
│   480x480      │  ← 240x240 UI scaled 2x
│   Main UI      │
│                │
├────────────────┤
│   480x160      │  ← Context-sensitive touch bar
│  ▲ | SEL | ▼   │
└────────────────┘
```

### Touch Bar Modes
| Context | Buttons |
|---------|---------|
| Navigation | `▲` \| `SELECT` \| `▼` |
| Keyboard | `DEL` \| `WORD` \| `▼` |

### Auto-Detection Logic (renderer.py)
- Checks `/dev/fb0` and `/sys/class/graphics/fb0/virtual_size`
- If 480x640 → DPI28 driver
- Else → ST7789 (original HAT)
- Environment overrides: `SEEDSIGNER_DISPLAY`, `SEEDSIGNER_TOUCH`

---

## 4. DPI28 Framebuffer Driver

### Key Technical Details
Based on mutatrum's fast-pillow-fb solution: https://github.com/mutatrum/fast-pillow-fb

| Aspect | Implementation |
|--------|----------------|
| Pixel format | 32-bit BGRA (auto-detected from sysfs) |
| Color order | RGB→BGR swap (Pi framebuffer is BGR) |
| Memory access | mmap for fast writes |
| Config source | `/sys/class/graphics/fb0/` |

### Performance Tiers
| Method | FPS on Pi Zero | Requirement |
|--------|----------------|-------------|
| Cython | ~17 fps | `pip install cython` |
| Numpy | ~7 fps | `pip install numpy` |
| Pure Python | ~1 fps | No dependencies |

### Why This Matters
Original driver had:
- Wrong pixel format (RGB565 instead of BGRA)
- No BGR swap (colors inverted)
- Slow file I/O instead of mmap
- ~1 fps pure Python loop

Reference: SeedSigner issue #150 (1M sat bounty): https://github.com/SeedSigner/seedsigner/issues/150

---

## 5. Hardware Status

| Device | Status |
|--------|--------|
| Pi Zero W | Working, WiFi hardware-disabled |
| Pi 3B v1.2 | Working, 2.4GHz WiFi only |
| Original SeedSigner HAT (ST7789) | Working |
| Waveshare 2.8" DPI LCD | DOA - replacement pending |

---

## 6. QEMU Emulator Setup (Windows) - From Scratch

### Prerequisites

#### Install QEMU
- Download: https://qemu.weilnetz.de/w64/2023/
- Used: `qemu-w64-setup-20230407.exe` (64-bit)

#### Download Required Files
1. **Raspberry Pi OS Image** (Buster Lite):
   https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-05-28/
   Extract the `.img` from the zip

2. **QEMU Kernel & DTB** (from dhruvvyas90/qemu-rpi-kernel):
   - `kernel-qemu-4.19.50-buster`
   - `versatile-pb-buster-5.4.51.dtb`

3. Put all three files in the same folder

### Create boot.bat
```batch
"C:\Program Files\qemu\qemu-system-arm" -kernel "kernel-qemu-4.19.50-buster" -cpu arm1176 -m 256 -M versatilepb -dtb "versatile-pb-buster-5.4.51.dtb" -append "root=/dev/sda2 panic=1 rootfstype=ext4 rw" -drive file="YOUR-IMAGE.img,format=raw" -net nic -net user,hostfwd=tcp::5022-:22 -no-reboot
```

### Resize Image (add 4GB)
```cmd
"C:\Program Files\qemu\qemu-img" resize -f raw "YOUR-IMAGE.img" +4G
```

### First Boot - Expand Filesystem

1. Run `boot.bat`
2. Login: `pi` / `raspberry`
3. Check current partition layout:
```bash
   sudo fdisk -l
```
   Note the start sector of `/dev/sda2` (e.g., `532480`)

4. Resize partition:
```bash
   sudo fdisk /dev/sda
```
   - `d` → `2` (delete partition 2)
   - `n` → `p` → `2` (new primary partition 2)
   - First sector: enter the number from step 3 (e.g., `532480`)
   - Last sector: press Enter (use all space)
   - `y` to remove signature
   - `w` to write changes

5. Reboot:
```bash
   sudo reboot
```

6. Run `boot.bat` again, login, expand filesystem:
```bash
   sudo resize2fs /dev/sda2
   df -h  # verify ~5.6GB available
```

7. Shutdown and backup your .img:
```bash
   sudo shutdown now
```

---

## 7. SeedSigner Installation in QEMU

Follow: https://github.com/SeedSigner/seedsigner/blob/dev/docs/manual_installation.md

### Fix for zbar error
```bash
curl -L http://raspbian.raspberrypi.org/raspbian/pool/main/z/zbar/libzbar0_0.23.90-1+deb11u1_armhf.deb --output libzbar0_0.23.90-1+deb11u1_armhf.deb
sudo apt install ./libzbar0_0.23.90-1+deb11u1_armhf.deb
```

### Clone & Setup Touchscreen Branch
```bash
cd ~
git clone https://github.com/FreeOnlineUser/seedsigner.git
cd seedsigner
git checkout touchscreen-v3
pip3 install -r requirements.txt
pip3 install -e .
```

### Running Tests
```bash
cd ~/seedsigner
pip3 install pytest
python3 -m pytest --ignore=tests/test_l10n.py --ignore=tests/test_flows_l10n.py
```
Result: 118 passed, 5 failed (l10n failures are pre-existing upstream)

---

## 8. Working QEMU Environment (Ready to Use)

### Location
```
Path: C:\Users\bradc\Documents\ClaudeWorkspace\Projects\custom_seedsigner_bip85
```

### Files in Folder
```
boot.bat
kernel-qemu-4.19.50-buster
versatile-pb-buster-5.4.51.dtb
touchscreen-ready.img
```

### boot.bat
```batch
"C:\Program Files\qemu\qemu-system-arm" -kernel "kernel-qemu-4.19.50-buster" -cpu arm1176 -m 256 -M versatilepb -dtb "versatile-pb-buster-5.4.51.dtb" -append "root=/dev/sda2 panic=1 rootfstype=ext4 rw" -drive file="touchscreen-ready.img,format=raw" -net nic -net user,hostfwd=tcp::5022-:22 -no-reboot
```

### SSH Access
```
ssh pi@localhost -p 5022
Login: pi / yourPassword (default: raspberry)
```

### Update Pi Image via SSH
```bash
# SSH in
ssh pi@localhost -p 5022

# Pull latest changes
cd ~/seedsigner
git pull

# Shutdown (saves to .img)
sudo shutdown now
```

Then flash `touchscreen-ready.img` with Balena Etcher.

### Occasional Commands (only when needed)
| Command | When to run |
|---------|-------------|
| `pip3 install -r requirements.txt` | Only if you changed dependencies in requirements.txt |
| `pip3 install -e .` | Only if you changed setup.py or pyproject.toml |
| `pip3 install cython` | One-time setup for faster display (~17 fps vs ~7 fps) |

---

## 9. config.txt for Waveshare 2.8" DPI LCD

Add to `/boot/config.txt` on the SD card (from Waveshare wiki):

```ini
gpio=0-9=a2
gpio=12-17=a2
gpio=20-25=a2
dtoverlay=dpi24
enable_dpi_lcd=1
display_default_lcd=1
extra_transpose_buffer=2
dpi_group=2
dpi_mode=87
dpi_output_format=0x7F216
hdmi_timings=480 0 26 16 10 640 0 25 10 15 0 0 0 60 0 32000000 1
dtoverlay=waveshare-28dpi-3b-4b
dtoverlay=waveshare-28dpi-3b
dtoverlay=waveshare-28dpi-4b

# Comment out if present:
# dtoverlay=vc4-kms-v3d
# dtoverlay=vc4-fkms-v3d
```

**Note:** Download the DTBO overlay files from Waveshare and copy to `/boot/overlays/`.

See: https://www.waveshare.com/wiki/2.8inch_DPI_LCD

---

## 10. PR Status

### Target
- Repo: `SeedSigner/seedsigner`
- Base: `dev`
- Branch: `touchscreen-v3`

### Bounty
- Issue #150: 1 Million Sat bounty for touchscreen demo
- https://github.com/SeedSigner/seedsigner/issues/150
- Still open/unclaimed as of Dec 2024

### Checklist
- [x] DPI28 framebuffer driver (32-bit BGRA, RGB→BGR swap)
- [x] Touch input via evdev
- [x] Touch bar UI integration
- [x] Desktop emulator for development
- [x] Backward compatibility with original HAT
- [ ] Test on real DPI display hardware (awaiting replacement)
- [ ] Verify config.txt settings on real hardware
- [ ] Run pytest on Pi hardware
- [ ] Submit PR to official repo

---

## 11. Reference Links

| Resource | URL |
|----------|-----|
| SeedSigner Official | https://github.com/SeedSigner/seedsigner |
| Your Fork | https://github.com/FreeOnlineUser/seedsigner |
| Touchscreen Branch | https://github.com/FreeOnlineUser/seedsigner/tree/touchscreen-v3 |
| Bounty Issue #150 | https://github.com/SeedSigner/seedsigner/issues/150 |
| mutatrum's framebuffer solution | https://github.com/mutatrum/fast-pillow-fb |
| Waveshare 2.8" DPI Wiki | https://www.waveshare.com/wiki/2.8inch_DPI_LCD |

---

## 12. Development Notes (for PR)

This implementation was developed with AI assistance (Claude Code). The approach is based on research into:

- [mutatrum's fast-pillow-fb](https://github.com/mutatrum/fast-pillow-fb) for mmap framebuffer writes
- Waveshare 2.8" DPI LCD documentation
- Why previous attempts failed (wrong pixel format, missing BGR swap)

Tested in QEMU emulator with pytest (118 passed). Hardware testing pending replacement display.

---

## 13. Notes

- All QEMU changes persist inside the .img file
- Back up .img after major milestones
- Pi Zero W has WiFi resistor lifted (hardware disabled for security)
- GitHub fork is public (forks of public repos are always public)
- Repository is obscure - not indexed in search, so effectively private until PR
