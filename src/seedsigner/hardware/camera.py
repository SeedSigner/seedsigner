import io
import os
from PIL import Image
from seedsigner.hardware.pivideostream import PiVideoStream
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton

# custom adds
import array

class Camera(Singleton):
    _video_stream = None
    _camera_rotation = None

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        cls._instance._camera_rotation = int(Settings.get_instance().get_value(SettingsConstants.SETTING__CAMERA_ROTATION))
        return cls._instance

    def start_video_stream_mode(self, resolution=(240, 240), framerate=12, format="bgr"):
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        # Start the video stream with the given resolution and framerate
        self._video_stream = PiVideoStream(resolution=resolution, framerate=framerate)
        self._video_stream.start()

    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")

        frame = self._video_stream.read()
        if frame is None:
            return None

        if as_image:
            # Check if frame is already an Image object
            if isinstance(frame, Image.Image):
                img = frame
            else:
                # Convert the raw frame to an image
                img = Image.frombytes('RGB', (self._video_stream.width, self._video_stream.height), frame)

            return img.rotate(90 + self._camera_rotation)

        return frame
    
    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None

    # 240, 135?
    # 2304x1296
    def start_single_frame_mode(self, resolution=(2304, 1296)): # resolution=(720, 480)
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        # Start a new video stream for single-frame capture
        self._video_stream = PiVideoStream(resolution=resolution, framerate=1)
        self._video_stream.start()

    def capture_frame(self):
        if not self._video_stream:
            raise Exception("Must call start_single_frame_mode first.")

        # Capture a single frame
        frame = self._video_stream.read()
        if frame is None:
            raise Exception("Failed to capture frame.")

        return frame

    def stop_single_frame_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None
