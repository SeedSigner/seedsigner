import io

#from picamera import PiCamera
from PIL import Image
#from seedsigner.hardware.pivideostream import PiVideoStream
from seedsigner.emulator.webcamvideostream import WebcamVideoStream

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
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        #self._video_stream = PiVideoStream(resolution=resolution,framerate=framerate, format=format)
        self._video_stream = WebcamVideoStream(resolution=resolution,framerate=framerate, format=format)        
        self._video_stream.start()


    def read_video_stream(self, as_image=False):
        if not self._video_stream:
            raise Exception("Must call start_video_stream first.")

        if not self._video_stream.hasCamera(): 
            raise Exception("Can not open Webcam")

        frame = self._video_stream.read()
        if not as_image:
            return frame
        else:
            if frame is not None:
                return Image.fromarray(frame.astype('uint8'), 'RGB').rotate(90 + self._camera_rotation)
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
        return Image.fromarray(frame ).rotate(90 + self._camera_rotation)



    def stop_single_frame_mode(self):
        if self._picamera is not None:
            self._picamera.close()
            self._picamera = None

