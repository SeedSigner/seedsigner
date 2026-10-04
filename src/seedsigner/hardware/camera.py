import io
import logging
import time

from gettext import gettext as _
from PIL import Image

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.singleton import Singleton

_log = logging.getLogger(__name__)



class CameraConnectionError(Exception):
    pass



class Camera(Singleton):
    _video_stream = None
    _parked_stream = None   # stream kept alive between scans; avoids second PiCamera() open
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
        from picamera import PiCameraError
        from seedsigner.hardware.pivideostream import PiVideoStream
        if self._video_stream is not None:
            self.stop_video_stream_mode()

        # Reuse the parked stream from the previous scan if it is still alive.
        #
        # On Pi Zero, opening PiCamera() a second time while MMAL is still
        # releasing from the first session blocks the PiCamera() constructor
        # indefinitely — this happens in the main thread, freezing the UI before
        # the 5 s watchdog below even gets a chance to run. The only reliable fix
        # is to never call PiCamera() a second time within a session.
        #
        # stop_video_stream_mode() parks rather than destroys the stream: it sets
        # _video_stream = None (so LivePreviewThread stops drawing) but leaves the
        # PiVideoStream background thread running at 1 fps with nobody reading.
        # Here we reattach to it — frames are already flowing, no MMAL re-init.
        _WATCHDOG = 10.0  # seconds without a frame → treat stream as dead
        if self._parked_stream is not None:
            ps = self._parked_stream
            stale = (time.time() - ps.last_capture_time) > _WATCHDOG
            if stale or ps.is_stopped:
                _log.warning(
                    "start_video_stream_mode: parked stream %s, rebuilding",
                    "stopped" if ps.is_stopped else "stale",
                )
                self._force_close_stream(ps)
                self._parked_stream = None
        if self._parked_stream is not None:
            if not self._parked_stream.is_stopped:
                _log.info("start_video_stream_mode: reusing parked stream, flushing 500ms")
                # Restore scan framerate — parked stream was throttled to 1 fps.
                try:
                    self._parked_stream.camera.framerate = framerate
                except Exception:
                    pass
                # Flush stale frames from the hardware pipeline. PiCamera's internal
                # ring buffer holds 3-4 frames; after a framerate transition the
                # sensor takes several cycles to deliver genuinely new pixels. We
                # keep discarding frames for 500 ms so the full pipeline depth is
                # drained before ScanScreen gets control.
                flush_end = time.time() + 0.5
                self._parked_stream.frame = None
                while time.time() < flush_end:
                    if self._parked_stream.frame is not None:
                        self._parked_stream.frame = None
                    time.sleep(0.05)
                # Final wait: get one clean post-flush frame.
                deadline = time.time() + 2.0
                while self._parked_stream.frame is None and time.time() < deadline:
                    time.sleep(0.05)
                if self._parked_stream.frame is not None:
                    self._video_stream = self._parked_stream
                    self._parked_stream = None
                    return
            # Parked stream is dead or stalled — clean it up and open fresh.
            _log.warning("start_video_stream_mode: parked stream dead, opening fresh")
            self._force_close_stream(self._parked_stream)
            self._parked_stream = None

        try:
            self._video_stream = PiVideoStream(resolution=resolution, framerate=framerate, format=format)
            self._video_stream.start()
        except PiCameraError:
            # This error most often occurs because the camera connection is loose
            raise CameraConnectionError()

        # Wait up to 5 s for the first frame. Guards against the rare case where
        # PiCamera() opens but capture_continuous silently stalls, keeping
        # self.frame = None forever so the ScanScreen button check is never reached.
        deadline = time.time() + 5.0
        while self._video_stream.read() is None and time.time() < deadline:
            time.sleep(0.05)

        if self._video_stream.read() is None:
            _log.error("start_video_stream_mode: no frames in 5s, camera failed")
            self._force_close_stream(self._video_stream)
            self._video_stream = None
            raise CameraConnectionError()


    def read_video_stream(self, as_image=False):
        # Use a local ref so a concurrent stop_video_stream_mode() setting
        # _video_stream = None mid-call doesn't cause an AttributeError.
        vs = self._video_stream
        if not vs:
            return None
        frame = vs.read()
        if not as_image:
            return frame
        else:
            if frame is not None:
                return Image.fromarray(frame.astype('uint8'), 'RGB').convert('RGBA').rotate(90 + self._camera_rotation)
        return None


    def stop_video_stream_mode(self):
        if self._video_stream is not None:
            # Park the stream instead of stopping it. The PiVideoStream background
            # thread keeps running (capturing frames at 1 fps with nobody reading
            # them). LivePreviewThread checks _video_stream and exits when it sees
            # None. The next start_video_stream_mode() reuses the parked stream
            # directly, so PiCamera() is never opened a second time.
            if self._parked_stream is not None:
                # Shouldn't happen in normal flow — a previous park was never reused.
                # Truly stop it before replacing so we don't orphan a camera instance.
                self._force_close_stream(self._parked_stream)
            self._parked_stream = self._video_stream
            self._video_stream = None
            # Drop to 1 fps. The parked thread keeps the camera sensor running at
            # whatever framerate was configured, firing that many DMA interrupts/sec.
            # On Pi Zero's single core, 12 interrupts/sec during PBKDF2 or UI
            # navigation starves the main thread and causes random UI freezes on
            # any screen — menu, confirm, seed words. 1 fps cuts that to negligible.
            try:
                self._parked_stream.camera.framerate = 1
            except Exception:
                pass


    def _force_close_stream(self, vs):
        """Signal the stream to stop, wait up to 3 s, then force-close on timeout."""
        vs.should_stop = True
        deadline = time.time() + 3.0
        while not vs.is_stopped and time.time() < deadline:
            time.sleep(0.05)
        if not vs.is_stopped:
            # MMAL stalled — close the PiCamera directly to unblock capture_continuous.
            try:
                vs.camera.close()
            except Exception:
                pass
        time.sleep(1.0)  # give MMAL time to fully release hardware before the next open


    def start_single_frame_mode(self, resolution=(720, 480)):
        from picamera import PiCamera, PiCameraError
        if self._video_stream is not None:
            self.stop_video_stream_mode()
        # Single-frame mode opens its own PiCamera instance. A parked video stream
        # also holds an open PiCamera — two instances can't coexist on MMAL, so
        # truly stop the parked stream before proceeding.
        if self._parked_stream is not None:
            self._force_close_stream(self._parked_stream)
            self._parked_stream = None
        if self._picamera is not None:
            self._picamera.close()

        try:
            self._picamera = PiCamera(resolution=resolution, framerate=24)
            self._picamera.start_preview()
        except PiCameraError:
            # This error most often occurs because the camera connection is loose
            raise CameraConnectionError()


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
