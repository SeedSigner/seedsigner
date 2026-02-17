import sys
import os
import signal
import time
import multiprocessing
from unittest.mock import Mock, patch
import time
import numpy as np

# Add the emulator directory to sys.path to enable imports
emulator_dir = os.path.dirname(os.path.abspath(__file__))
if emulator_dir not in sys.path:
    sys.path.insert(0, emulator_dir)

from patches.camera import MockCamera
from patches.gpio import MockGPIO
from patches.window import Window


class MockST7789:
    def __init__(self, width=240, height=240):
        self.width = width
        self.height = height

    def show_image(self, image, x=0, y=0):
        # Save image for the GUI to display
        with open("display.bmp", "wb") as f:
            f.write(image.tobytes())

    def invert(self, enabled: bool = True):
        pass


class MockVideoStream:
    def __init__(self):
        self.frame = np.random.randint(0, 255, (240, 240, 3), dtype=np.uint8)

    def start(self):
        pass

    def read(self):
        return self.frame

    def stop(self):
        pass


# Mock patches to apply
MOCK_PATCHES = [
    ("seedsigner.hardware.displays.ST7789.ST7789", MockST7789),
    ("seedsigner.hardware.displays.st7789_mpy.ST7789", MockST7789),
    ("seedsigner.extras.local_display.ST7789", MockST7789),
    ("seedsigner.hardware.pivideostream.PiVideoStream", MockVideoStream),
    ("seedsigner.hardware.camera.Camera", MockCamera),
]


def setup_mocks():
    """Apply all mock patches"""
    patches = []

    import sys

    # Mock the entire picamera module before anything imports it
    picamera_mock = Mock()
    picamera_mock.PiCamera = Mock()
    picamera_mock.array = Mock()
    picamera_mock.array.PiRGBArray = Mock()
    picamera_mock.PiCameraError = Exception
    sys.modules["picamera"] = Mock()
    sys.modules["picamera.array"] = picamera_mock.array

    # Mock the RPi module and its components
    rpi_mock = Mock()
    rpi_mock.GPIO = MockGPIO()
    sys.modules["RPi"] = rpi_mock
    sys.modules["RPi.GPIO"] = rpi_mock.GPIO

    # Mock spidev module
    spidev_mock = Mock()
    spidev_mock.SpiDev = Mock()
    sys.modules["spidev"] = spidev_mock

    for module_path, mock_obj in MOCK_PATCHES:
        try:
            patcher = patch(module_path, mock_obj)
            patches.append(patcher)
            patcher.start()
        except (ImportError, AttributeError):
            # Module doesn't exist or can't be patched, skip
            continue

    return patches


def run_gui():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Setup mocks and import HardwareButtons after environment is set
    setup_mocks()
    from seedsigner.hardware.buttons import HardwareButtons

    Window(HardwareButtons)


def run_main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Setup mocks before importing the main module
    setup_mocks()

    from main import main

    # Give GUI a moment to start up and create socket
    time.sleep(0.5)

    main()


def signal_handler(sig, frame):
    sys.exit(0)


if __name__ == "__main__":
    # Handle Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    shutdown_event = multiprocessing.Event()

    gui_process = multiprocessing.Process(target=run_gui, name="GUI")
    main_process = multiprocessing.Process(target=run_main, name="Main")

    try:
        print("Starting GUI simulator...")
        gui_process.start()

        print("Starting SeedSigner main application...")
        main_process.start()

        while gui_process.is_alive() and main_process.is_alive():
            try:
                gui_process.join(timeout=0.1)
                main_process.join(timeout=0.1)
            except KeyboardInterrupt:
                break

    except KeyboardInterrupt:
        pass

    if main_process.is_alive():
        main_process.terminate()
        main_process.join(timeout=2)
        if main_process.is_alive():
            main_process.kill()

    if gui_process.is_alive():
        gui_process.terminate()
        gui_process.join(timeout=2)
        if gui_process.is_alive():
            gui_process.kill()
