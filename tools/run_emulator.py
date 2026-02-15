import os
import sys
import signal
import time
import multiprocessing
import threading
import socket
from unittest.mock import Mock, patch
import numpy as np
from tkinter import *
from PIL import Image, ImageTk

from PIL import Image

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton

from threading import Thread
import time
import cv2
import numpy as np


class MockCamera(Singleton):
    _video_stream = None
    _picamera = None
    _camera_rotation = None

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
        print("INSTANCE")
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        cls._instance._camera_rotation = int( Settings.get_instance().get_value(SettingsConstants.SETTING__CAMERA_ROTATION))
        cls._instance._camera_rotation += 90
        return cls._instance

    def start_video_stream_mode(
        self, resolution=(512, 384), framerate=12, format="bgr"
    ):
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        try:
            self._video_stream = WebcamVideoStream(
                resolution=resolution, framerate=framerate, format=format
            )
            self._video_stream.start()
        except Exception as e:
            raise e

    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        frame = self._video_stream.read()
        if not as_image:
            return frame
        else:
            if frame is not None:
                return Image.fromarray(frame.astype("uint8"), "RGB").rotate(
                    90 + self._camera_rotation
                )
        return None

    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None

    def start_single_frame_mode(self, resolution=(720, 480)):
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._picamera is not None:
            self._picamera.close()

    def capture_frame(self):
        print("CAPTURE")
        frame = WebcamVideoStream.single_frame()
        return Image.fromarray(frame).rotate(90 + self._camera_rotation)

    def stop_single_frame_mode(self):
        if self._picamera is not None:
            self._picamera.close()
            self._picamera = None


def resize_and_center_crop_240(frame_bgr: np.ndarray) -> np.ndarray:
    target = 240
    h, w = frame_bgr.shape[:2]

    # resize to 240
    if w < h:
        scale = target / w
    else:
        scale = target / h

    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # center crop
    x1 = (new_w - target) // 2
    y1 = (new_h - target) // 2

    cropped = resized[y1 : y1 + target, x1 : x1 + target]

    return cropped


class WebcamVideoStream:
    def __init__(self, resolution=(320, 240), framerate=32, format="bgr", **kwargs):
        # initialize the camera
        self.camera = cv2.VideoCapture(0)
        self.set_resolution(resolution)

        # initialize the frame and the variable used to indicate
        # if the thread should be stopped
        self.frame = None
        self.should_stop = False
        self.is_stopped = True

    def start(self):
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        self.is_stopped = False
        return self

    def update(self):
        if self.camera.isOpened():
            # keep looping infinitely until the thread is stopped
            while not self.should_stop:
                # grab the frame from the stream and clear the stream in
                # preparation for the next frame
                ret, stream = self.camera.read()
                stream = cv2.resize(stream, (240, 240))
                stream = cv2.cvtColor(stream, cv2.COLOR_BGR2RGB)
                time.sleep(0.05)
                self.frame = stream
        self.is_stopped = True
        self.should_stop = False

    def read(self):
        return self.frame

    def stop(self):
        # indicate that the thread should be stopped
        self.should_stop = True

        # Block in this thread until stopped
        while not self.is_stopped:
            pass

    def set_resolution(self, resolution):
        self.camera.set(3, resolution[0])
        self.camera.set(4, resolution[1])

    @staticmethod
    def single_frame():
        cap = cv2.VideoCapture(0)

        # Warm-up, let auto-exposure settle in
        for _ in range(30):
            cap.read()
            time.sleep(0.01)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError("Camera capture failed")

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = resize_and_center_crop_240(frame)
        return frame


class MockVideoStream:
    def __init__(self):
        self.frame = np.random.randint(0, 255, (240, 240, 3), dtype=np.uint8)

    def start(self):
        pass

    def read(self):
        return self.frame

    def stop(self):
        pass


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


class MockGPIO:
    LOW = 0
    HIGH = 1
    BOARD = 10
    IN = 1
    PUD_UP = 22
    RPI_INFO = {"P1_REVISION": 3}

    def __init__(self):
        self._states = {}
        self.lock = threading.Lock()
        self._initialized = False

    def setmode(self, mode):
        pass

    def setup(self, pin, mode, pull_up_down=None):
        if not self._initialized:
            self.init()

    def init(self, socket_path="gpio.sock"):
        if self._initialized:
            return
        self._initialized = True
        self._states = {}
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(socket_path)
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        f = self.sock.makefile("r")
        while True:
            line = f.readline()
            if not line:
                break
            try:
                pin, val = line.strip().split()
                with self.lock:
                    self._states[int(pin)] = int(val)
            except Exception:
                pass

    def input(self, pin):
        with self.lock:
            return self._states.get(pin, self.HIGH)


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


class Window:
    def __init__(self, HardwareButtons, width: int = 240, height: int = 240):
        self.width = width
        self.height = height
        self.HardwareButtons = HardwareButtons

        self.setup_sock()
        self.run()

    def run(self):
        self.root = Tk()
        self.root.title("SeedSigner")

        self.root.geometry(f"{self.width*2}x{self.height}+240+240")
        self.root.resizable(False, False)
        self.root.configure(bg="orange")
        self.root.attributes("-topmost", True)

        self.label = Label(self.root)
        self.label.pack()

        self.joystick = Frame(self.root)
        self.joystick.pack()
        self.joystick.place(x=20, y=85)
        self.joystick.configure(bg="orange")

        pixel = PhotoImage(width=1, height=1)

        self.btnL = Button(
            self.joystick,
            image=pixel,
            width=20,
            height=20,
            command=self.HardwareButtons.KEY_LEFT_PIN,
        )
        self.btnL.grid(row=1, column=0)
        self.bindButtonClick(self.btnL)

        self.btnR = Button(
            self.joystick,
            image=pixel,
            width=20,
            height=20,
            command=self.HardwareButtons.KEY_RIGHT_PIN,
        )
        self.btnR.grid(row=1, column=2)
        self.bindButtonClick(self.btnR)

        self.btnC = Button(
            self.joystick,
            image=pixel,
            width=20,
            height=20,
            command=self.HardwareButtons.KEY_PRESS_PIN,
        )
        self.btnC.grid(row=1, column=1)
        self.bindButtonClick(self.btnC)

        self.btnU = Button(
            self.joystick,
            image=pixel,
            width=20,
            height=20,
            command=self.HardwareButtons.KEY_UP_PIN,
        )
        self.btnU.grid(row=0, column=1)
        self.bindButtonClick(self.btnU)

        self.btnD = Button(
            self.joystick,
            image=pixel,
            width=20,
            height=20,
            command=self.HardwareButtons.KEY_DOWN_PIN,
        )
        self.btnD.grid(row=2, column=1)
        self.bindButtonClick(self.btnD)

        self.btn1 = Button(
            self.root,
            image=pixel,
            width=40,
            height=20,
            command=self.HardwareButtons.KEY1_PIN,
        )
        self.btn1.place(x=self.width + 160, y=60)
        self.bindButtonClick(self.btn1)

        self.btn2 = Button(
            self.root,
            image=pixel,
            width=40,
            height=20,
            command=self.HardwareButtons.KEY2_PIN,
        )
        self.btn2.place(x=self.width + 160, y=116)
        self.bindButtonClick(self.btn2)

        self.btn3 = Button(
            self.root,
            image=pixel,
            width=40,
            height=20,
            command=self.HardwareButtons.KEY3_PIN,
        )
        self.btn3.place(x=self.width + 160, y=172)
        self.bindButtonClick(self.btn3)

        def key_handler(event):
            if event.keysym == "Up":
                self.key_press(self.HardwareButtons.KEY_UP_PIN)
            if event.keysym == "Down":
                self.key_press(self.HardwareButtons.KEY_DOWN_PIN)
            if event.keysym == "Left":
                self.key_press(self.HardwareButtons.KEY_LEFT_PIN)
            if event.keysym == "Right":
                self.key_press(self.HardwareButtons.KEY_RIGHT_PIN)

            if event.keysym in ("1", "KP_1"):
                self.key_press(self.HardwareButtons.KEY1_PIN)
            if event.keysym in ("2", "KP_2"):
                self.key_press(self.HardwareButtons.KEY2_PIN)
            if event.keysym in ("3", "KP_3"):
                self.key_press(self.HardwareButtons.KEY3_PIN)

            if event.keysym == "Return":
                self.key_press(self.HardwareButtons.KEY_PRESS_PIN)

        self.root.bind("<Key>", key_handler)

        self.periodic_update()
        self.root.mainloop()

    def key_press(self, key):
        self.set_input(key, 0)
        time.sleep(0.1)
        self.set_input(key, 1)

    def bindButtonClick(self, btn):
        btn.bind("<Button>", self.buttonDown)
        btn.bind("<ButtonRelease>", self.buttonUp)

    def buttonDown(self, btn):
        key = btn.widget.config("command")[-1]
        self.set_input(key, 0)

    def buttonUp(self, btn):
        key = btn.widget.config("command")[-1]
        self.set_input(key, 1)

    def load_raw_rgb(self, filename):
        if not os.path.exists(filename):
            return None
        with open(filename, "rb") as f:
            data = f.read()
        img_array = np.frombuffer(data, dtype=np.uint8)
        try:
            img_array = img_array.reshape((self.height, self.width, 3))
        except ValueError:
            return None
        return Image.fromarray(img_array, "RGB")

    def periodic_update(self, filename="display.bmp", interval=10):
        img = self.load_raw_rgb(filename)
        if img:
            self.tkimage = ImageTk.PhotoImage(img, master=self.root)
            self.label.configure(image=self.tkimage)
            self.label.image = self.tkimage
        self.root.after(interval, lambda: self.periodic_update(filename, interval))

    def set_input(self, key, val):
        try:
            msg = f"{key} {val}\n"
            self.conn.sendall(msg.encode())
        except Exception:
            pass

    def setup_sock(self, path="gpio.sock"):
        if os.path.exists(path):
            os.remove(path)

        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(path)
        self.server.listen(1)

        threading.Thread(target=self.handle_sock, daemon=True).start()

    def handle_sock(self):
        while True:
            self.conn, _ = self.server.accept()


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
