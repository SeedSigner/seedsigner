from PIL import Image

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton



class CameraConnectionError(Exception):
    pass



class Camera(Singleton):
    _video_stream = None
    _still_capture = None
    _camera_rotation = None

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        cls._instance._camera_rotation = int(Settings.get_instance().get_value(SettingsConstants.SETTING__CAMERA_ROTATION))
        return cls._instance


    def start_video_stream_mode(self, resolution=(512, 384), framerate=12):
        from seedsigner.hardware.camera_stream import LibcameraVideoStream, LibcameraError
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        try:
            self._video_stream = LibcameraVideoStream(resolution=resolution, framerate=framerate)
            self._video_stream.start()
        except LibcameraError:
            # This error most often occurs because the camera connection is loose
            self._video_stream = None
            raise CameraConnectionError()


    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        if not as_image:
            # (pixels, width, height) grayscale tuple, consumed by pyzbar
            return self._video_stream.read()
        else:
            from seedsigner.hardware.camera_stream import rgba_buffer_to_image
            frame = self._video_stream.read_rgba()
            if frame is not None:
                data, stride, width, height = frame
                return rgba_buffer_to_image(data, stride, width, height).rotate(90 + self._camera_rotation)
        return None


    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None


    def start_single_frame_mode(self, resolution=(720, 480)):
        from seedsigner.hardware.camera_stream import LibcameraStillCapture, LibcameraError
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._still_capture is not None:
            self.stop_single_frame_mode()

        try:
            self._still_capture = LibcameraStillCapture(resolution=resolution)
            self._still_capture.start()
        except LibcameraError:
            # This error most often occurs because the camera connection is loose
            self._still_capture = None
            raise CameraConnectionError()


    def capture_frame(self):
        if self._still_capture is None:
            raise Exception("Must call start_single_frame_mode first.")

        # Locks auto-exposure/AWB at their converged values, like the old
        # picamera shutter_speed/awb_gains freeze
        return self._still_capture.capture_locked_frame().rotate(90 + self._camera_rotation)


    def stop_single_frame_mode(self):
        if self._still_capture is not None:
            self._still_capture.stop()
            self._still_capture = None
