import io

from picamera import PiCamera
from PIL import Image
from seedsigner.helpers import PiVideoStream, Singleton



class Camera(Singleton):
    _video_stream = None
    _picamera = None


    def start_video_stream_mode(self, resolution=(512, 384), framerate=12):
        if self._video_stream is not None:
            # Shut down the video stream
            pass

        self._video_stream = PiVideoStream(resolution=resolution,framerate=framerate)
        self._video_stream.start()


    def read_video_stream(self):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")
        return video_stream.read()


    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            self._video_stream.stop()
            self._video_stream = None


    def start_single_frame_mode(self, resolution=(720, 480)):
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        if self._picamera is not None:
            self._picamera.close()

        self._picamera = PiCamera(resolution=resolution, framerate=8)


    def capture_frame(self, resolution=(720, 480)):
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

        return Image.open(stream)


    def stop_single_frame_mode(self):
        if self._picamera is not None:
            self._picamera.close()
            self._picamera = None

