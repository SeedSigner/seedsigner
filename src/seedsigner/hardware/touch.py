"""
Touch input handler for capacitive touchscreen.

On Raspberry Pi: Reads raw Linux input events from /dev/input/
On PC/Emulator: Uses injected mock that translates pygame mouse events
"""

import logging
import struct
import select
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Linux input event codes (from linux/input-event-codes.h)
EV_SYN = 0x00
EV_ABS = 0x03
ABS_MT_TRACKING_ID = 0x39
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36

# Touch panel native resolution (Waveshare 2.8" DPI LCD)
TOUCH_WIDTH = 640
TOUCH_HEIGHT = 480


class TouchInput:
    """
    Handles touch input from capacitive touchscreen.
    Reads raw Linux input events - no external dependencies required.
    """

    def __init__(self, device_path: str = None,
                 screen_width: int = 480, screen_height: int = 640,
                 swap_xy: bool = False, invert_x: bool = False, invert_y: bool = False):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.swap_xy = swap_xy
        self.invert_x = invert_x
        self.invert_y = invert_y

        self.x = 0
        self.y = 0
        self.touching = False
        self.fd = None

        self._init_device(device_path)

    def _find_touch_device(self) -> Optional[str]:
        """Find touch input device by scanning /dev/input/"""
        for i in range(10):
            name_path = f"/sys/class/input/event{i}/device/name"
            if os.path.exists(name_path):
                try:
                    with open(name_path, "r") as f:
                        name = f.read().strip()
                        if "Goodix" in name or "touch" in name.lower():
                            return f"/dev/input/event{i}"
                except Exception:
                    pass
        return None

    def _init_device(self, device_path: str = None):
        """Initialize raw input device access"""
        path = device_path or self._find_touch_device()

        if path and os.path.exists(path):
            try:
                self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                logger.info(f"Opened touch device: {path}")
            except Exception as e:
                logger.warning(f"Failed to open {path}: {e}")
                self.fd = None
        else:
            logger.info("No touch device found")

    def poll(self) -> Optional[Tuple[str, int, int]]:
        """Poll for touch events (non-blocking)."""
        if self.fd is None:
            return None

        try:
            r, _, _ = select.select([self.fd], [], [], 0)
            if not r:
                return None

            # input_event struct on 32-bit ARM (Pi Zero):
            # tv_sec(4) + tv_usec(4) + type(2) + code(2) + value(4) = 16 bytes
            EVENT_SIZE = 16

            result = None
            pending_down = False
            pending_up = False

            while True:
                try:
                    data = os.read(self.fd, EVENT_SIZE)
                    if len(data) < EVENT_SIZE:
                        break

                    ev_type, ev_code, ev_value = struct.unpack("HHi", data[8:16])

                    if ev_type == EV_ABS:
                        if ev_code == ABS_MT_POSITION_X:
                            self.x = ev_value
                        elif ev_code == ABS_MT_POSITION_Y:
                            self.y = ev_value
                        elif ev_code == ABS_MT_TRACKING_ID:
                            if ev_value >= 0:
                                self.touching = True
                                pending_down = True
                            else:
                                self.touching = False
                                pending_up = True

                    elif ev_type == EV_SYN:
                        # SYN marks end of event packet - coordinates now complete
                        x, y = self._transform(self.x, self.y)
                        if pending_down:
                            result = ("down", x, y)
                            pending_down = False
                        elif pending_up:
                            result = ("up", x, y)
                            pending_up = False
                        elif self.touching:
                            result = ("move", x, y)

                except BlockingIOError:
                    break
                except Exception:
                    break

            return result

        except Exception:
            return None

    def _transform(self, raw_x: int, raw_y: int) -> Tuple[int, int]:
        """Transform raw touch coordinates to screen coordinates."""
        # Scale from touch panel resolution to screen resolution
        screen_x = raw_x * self.screen_width // TOUCH_WIDTH
        screen_y = raw_y * self.screen_height // TOUCH_HEIGHT

        if self.swap_xy:
            screen_x, screen_y = screen_y, screen_x

        if self.invert_x:
            screen_x = self.screen_width - 1 - screen_x

        if self.invert_y:
            screen_y = self.screen_height - 1 - screen_y

        # Clamp to screen bounds
        screen_x = max(0, min(self.screen_width - 1, screen_x))
        screen_y = max(0, min(self.screen_height - 1, screen_y))

        return screen_x, screen_y

    def close(self):
        """Close the device"""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
