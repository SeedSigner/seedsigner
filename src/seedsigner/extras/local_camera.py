from PIL import Image

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton

from threading import Thread
import time
import cv2
import numpy as np


class Camera(Singleton):
    _video_stream = None
    _picamera = None
    _camera_rotation = None

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
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
