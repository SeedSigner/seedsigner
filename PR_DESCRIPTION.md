# Touchscreen Support for Waveshare 2.8" DPI LCD

Relates to #150

## Summary

This PR adds touchscreen support for the **Waveshare 2.8" DPI LCD (480x640)**, enabling direct tap interaction while maintaining full backwards compatibility with the existing GPIO button interface.

**Key features:**
- **Auto-detection**: Automatically detects DPI LCD and touch hardware at boot
- Direct button tap selection (not D-pad emulation)
- Context-sensitive touch bar with scroll/navigation buttons
- Two-tap confirmation pattern for safety-critical actions
- Desktop emulator for development/testing without hardware
- Zero changes to existing GPIO button workflow

## Hardware

- **Display**: Waveshare 2.8" DPI LCD (480x640 resolution)
- **Interface**: DPI (parallel GPIO), not SPI
- **Touch**: Capacitive touch via evdev

## Auto-Detection

The system automatically detects hardware at boot:

1. **Display detection**: Checks `/sys/class/graphics/fb0/virtual_size` for `480,640`
2. **Touch detection**: Scans `/dev/input/event*` for multitouch capability

When detected, you'll see:
```
[Display] Auto-detected DPI28 framebuffer (480x640)
[Touch] Auto-detected touch device: <device name>
```

**No environment variables needed** - just connect the hardware and boot.

Manual override is still available via `SEEDSIGNER_DISPLAY` and `SEEDSIGNER_TOUCH` environment variables if needed.

## Architecture

```
┌─────────────────────────────┐
│      UI Area (480x480)      │  ← 240x240 scaled 2x
│                             │
│   SeedSigner native UI      │
│                             │
├─────────────────────────────┤
│  ▲    │  SELECT  │    ▼     │  ← Touch bar (480x160)
│ KEY1  │   KEY2   │  KEY3    │
└─────────────────────────────┘
```

**Touch bar modes** (uses SeedSigner icon fonts - language-agnostic):
- **List screens**: `▲ | ✓ | ▼` - scroll up/down with arrows (orange when active, grey at list boundaries)
- **Grid screens**: `  | ✓ |  ` - checkmark only (home screen)
- **Keyboard**: `🗑 | ⌨ | ▼` - smart color states:
  - Delete icon grey: no content to delete
  - Delete icon orange: content exists to delete
  - Keyboard icon grey: no words available
  - Keyboard icon orange: word(s) available for selection
  - ▼ grey: at bottom of word list
  - ▼ orange: can scroll down word list
- **Hidden**: No buttons shown (splash, screensaver, power off screens)

## Implementation Details

### New Files

| File | Purpose |
|------|---------|
| `src/seedsigner/hardware/DPI28.py` | Framebuffer driver for 2.8" DPI LCD |
| `src/seedsigner/hardware/RGBtoBGR.pyx` | Cython module for fast RGB→BGR conversion (optional) |
| `src/seedsigner/hardware/touch.py` | Capacitive touch input via Linux evdev |
| `src/seedsigner/hardware/touchbuttons.py` | Touch-to-HardwareButtons adapter |
| `src/seedsigner/emulator/run_emulator.py` | Desktop emulator using pygame |

### Modified Files

| File | Changes |
|------|---------|
| `src/seedsigner/hardware/displays/display_driver.py` | Added DPI28 display type to upstream's DisplayDriver abstraction |
| `src/seedsigner/gui/renderer.py` | Auto-detection + integration with upstream's Settings-based display configuration |
| `src/seedsigner/gui/screens/screen.py` | Direct tap handling, scroll fixes, touch bar management |
| `src/seedsigner/gui/screens/seed_screens.py` | Keyboard touch bar presets, BACK button handling, smart button states |
| `src/seedsigner/gui/keyboard.py` | Direct key tap detection |
| `src/seedsigner/gui/toast.py` | Touch-compatible toast display |
| `src/seedsigner/views/view.py` | Touch input integration |
| `src/seedsigner/views/screensaver.py` | Touch bar hiding, touch wake support |
| `src/seedsigner/controller.py` | Touch-aware screensaver initialization |

## User Interaction

### Two-Tap Selection Pattern
Most actions use a two-tap pattern for safety:
1. First tap highlights/selects the item
2. Second tap confirms the action

This prevents accidental activation of critical functions.

### Single-Tap Exceptions
- **Power button**: Single tap (has its own confirmation dialog)
- **Power Off / Restart buttons**: Single tap (have confirmation dialogs)
- **Cancel button**: Single tap
- **Back button**: Single tap navigation
- **Scroll arrows**: Single tap for page scrolling

### Direct Tap vs Navigation
- Buttons are registered with their screen positions
- Taps directly on buttons select them
- Taps outside buttons fall back to D-pad style navigation zones

## Testing

### Desktop Emulator

```bash
cd seedsigner-repo/src/seedsigner/emulator
python run_emulator.py          # Fast mode
python run_emulator.py --slow   # Simulate Pi framebuffer speed (~7fps)
```

The emulator provides:
- Mouse clicks simulate touch
- Same touch bar UI as hardware
- Full SeedSigner workflow testing
- `--slow` flag to simulate actual Pi performance

### Hardware Testing
1. Connect Waveshare 2.8" DPI LCD
2. Configure `/boot/config.txt` with DPI overlay
3. Boot - hardware is auto-detected
4. Run SeedSigner normally

## Compatibility

- **Backwards compatible**: Original ST7789 display works unchanged
- **Auto-detection**: No manual configuration needed for either mode
- **GPIO buttons**: Still work exactly as before on original hardware
- **Existing workflows**: All preserved
- **Touch-specific code**: Guarded by environment checks and `hasattr` guards

## Code Safety & Separation

This PR is designed to be **zero-risk to the existing GPIO code path**:

### Untouched Files (GPIO path)

| File | Status |
|------|--------|
| `src/seedsigner/hardware/buttons.py` | **100% unchanged** - all GPIO logic preserved |
| `src/seedsigner/hardware/ST7789.py` | **100% unchanged** |

### New Files (touch path only)

| File | Purpose |
|------|---------|
| `hardware/DPI28.py` | DPI LCD driver - only loaded when DPI28 detected |
| `hardware/touch.py` | Touch input - only loaded when touch detected |
| `hardware/touchbuttons.py` | Touch adapter - only loaded via `SEEDSIGNER_TOUCH=1` |

### Modified Files (all changes guarded)

All touch-related code in modified files uses `hasattr()` guards:

```python
# Example guard pattern - if touch not available, nothing happens
if hasattr(self.renderer, 'set_touch_bar_labels'):
    self.renderer.set_touch_bar_labels(DPI28.TOUCH_BAR_KEYBOARD)
```

### Path Selection

The input handler is selected at startup in `controller.py`:

- `SEEDSIGNER_TOUCH=1` → `TouchButtons` (touch path)
- Otherwise → `HardwareButtons` (GPIO path, unchanged)

No touch code executes on standard ST7789 + GPIO hardware.

## Maintainability

This implementation is designed to **not burden future GUI development**:

- **Display layer**: DPI28 receives the same 240x240 images as ST7789 - GUI code is display-agnostic
- **Input layer**: TouchButtons provides the identical interface as HardwareButtons (`wait_for()`, key constants) - screens don't need touch-specific code
- **Touch bar**: Managed automatically via existing screen lifecycle; defaults to `▲ | SELECT | ▼` unless explicitly changed
- **Guard pattern**: All touch-specific calls use `hasattr()` checks - if display lacks touch bar, nothing happens

New screens/views work automatically with touch - no modifications needed. Only keyboard-style screens benefit from explicit touch bar preset logic (and still work without it).

## Framebuffer Performance

The DPI28 driver uses memory-mapped framebuffer access with RGB→BGR color conversion (required by the Pi's 32-bit BGRA framebuffer format).

Based on [mutatrum's fast-pillow-fb](https://github.com/mutatrum/fast-pillow-fb) benchmarks on Pi Zero:

| Method | FPS | Notes |
|--------|-----|-------|
| Cython | ~17 | Optional `RGBtoBGR.pyx` module, auto-compiles if cython installed |
| Numpy | ~7 | Uses numpy array operations (likely already installed) |
| Pure Python | ~1 | Fallback, no dependencies |

The driver auto-detects the best available method at startup and logs which is being used.

## Screenshots/Demo

[To be added after hardware testing]

## Checklist

- [x] Direct pixel manipulation using PIL/Pillow (per issue #150 requirements)
- [x] Touch recognition integration
- [x] NOT desktop mirroring - uses framebuffer directly
- [x] Auto-detection of display and touch hardware
- [x] Desktop emulator for development
- [x] Backwards compatible with GPIO buttons
- [x] All existing screens work with touch
- [x] Keyboard input works with direct key taps
- [x] Scroll functionality preserved
- [x] Screensaver touch wake support

---

**Note**: This implementation was developed using the desktop emulator. Hardware testing on actual Waveshare 2.8" DPI LCD is pending arrival of the display.

---

## Pre-Submission Checklist

Before submitting this PR, complete these steps:

### 1. Sync with upstream dev
```bash
git remote add seedsigner https://github.com/SeedSigner/seedsigner.git
git fetch seedsigner
git rebase seedsigner/dev
# Resolve any conflicts, then: git rebase --continue
```

### 2. Run tests
```bash
pytest
```

### 3. Hardware testing
- [ ] Test on actual Waveshare 2.8" DPI LCD
- [ ] Capture screenshots/video for PR

### 4. Format PR using their template
Use `.github/pull_request_template.md`:
- [ ] Description with screenshots
- [ ] Category: New feature
- [ ] pytest confirmation
- [ ] Unit tests: Yes/No/N/A
- [ ] Platform tested: Raspberry Pi OS + Emulator

### 5. Submit

```bash
git push origin touchscreen-v3
# Create PR against SeedSigner/seedsigner dev branch
```
