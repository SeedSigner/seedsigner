import io

from PIL import Image
from seedsigner.hardware.pivideostream import PiVideoStream
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton



class Camera(Singleton):
    _video_stream = None
    _picamera = None
    _camera_rotation = None

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only Controller
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        cls._instance._camera_rotation = int(Settings.get_instance().get_value(SettingsConstants.SETTING__CAMERA_ROTATION))
        return cls._instance


    def start_video_stream_mode(self, resolution=(512, 384), framerate=12, format="bgr"):
        from seedsigner.hardware.pivideostream import PiVideoStream
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        self._video_stream = PiVideoStream(resolution=resolution,framerate=framerate, format=format)
        self._video_stream.start()


    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        frame = self._video_stream.read()
        if not as_image:
            return frame
        else:
            if frame is not None:
                return Image.fromarray(frame.astype('uint8'), 'RGB').convert('RGBA').rotate(90 + self._camera_rotation)
        return None


    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None


    def start_single_frame_mode(self, resolution=(720, 480)):
        from picamera import PiCamera
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._picamera is not None:
            self._picamera.close()

        self._picamera = PiCamera(resolution=resolution, framerate=24)
        self._picamera.start_preview()


    def capture_frame(self):
        if self._picamera is None:
            raise Exception("Must call start_single_frame_mode first.")

        # Set auto-exposure values
        self._picamera.shutter_speed = self._picamera.exposure_speed
        self._picamera.exposure_mode = 'off'
        g = self._picamera.awb_gains
        self._picamera.awb_mode = 'off'
        self._picamera.awb_gains = g

        stream = io.BytesIO()
        self._picamera.capture(stream, format='jpeg')

        # "Rewind" the stream to the beginning so we can read its content
        stream.seek(0)
        return Image.open(stream).rotate(90 + self._camera_rotation)


    def stop_single_frame_mode(self):
        if self._picamera is not None:
            self._picamera.close()
            self._picamera = None

