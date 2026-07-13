import itertools
import logging
import mmap
import selectors
import threading
import time

import libcamera

from PIL import Image

logger = logging.getLogger(__name__)

MICROSECONDS_PER_SECOND = 1_000_000


class LibcameraError(Exception):
    pass



def mmap_buffer(framebuffer) -> list:
    """
    mmap each plane of a libcamera FrameBuffer for read access.

    The libcamera python bindings we build (v0.3.x, pybind11) do not ship the
    optional `libcamera.utils.MappedFrameBuffer` helper, so map the dmabuf fds
    directly. Returns a list of (mmap, offset, length) tuples, one per plane.
    """
    maps = []
    for plane in framebuffer.planes:
        mapped_plane = mmap.mmap(plane.fd, plane.offset + plane.length, mmap.MAP_SHARED, mmap.PROT_READ)
        maps.append((mapped_plane, plane.offset, plane.length))
    return maps


def strip_stride(data: bytes, stride: int, width_bytes: int, height: int) -> bytes:
    """
    Remove per-row alignment padding from a raw frame buffer.

    libcamera buffers may have stride > row width (e.g. YUV420 at 480px wide
    reports a 512-byte stride on the RPi ISP). No-op (no copy) when the rows
    are already contiguous.
    """
    if stride == width_bytes:
        return data
    return b"".join(data[row * stride: row * stride + width_bytes] for row in range(height))


def rgba_buffer_to_image(data: bytes, stride: int, width: int, height: int) -> Image.Image:
    """Wrap a raw XBGR8888 frame (memory order R,G,B,X) as a PIL RGBA image."""
    return Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", stride, 1)



class BaseLibcameraSession:
    """
    Shared camera acquisition / configuration / buffer plumbing for the video
    stream and still capture classes below.
    """
    # CameraManager.get_ready_requests() is global to the process, so completed
    # or cancelled requests from an already-stopped session can surface while a
    # new session is draining events. Unique request cookies let each session
    # recognize (and ignore) requests that aren't its own.
    _request_cookies = itertools.count(1)

    def __init__(self):
        self._camera_manager = libcamera.CameraManager.singleton()
        if not self._camera_manager.cameras:
            # Most often a loose camera ribbon cable
            raise LibcameraError("No camera detected")
        self._camera = self._camera_manager.cameras[0]
        try:
            # Note: the python bindings raise on failure (and return None), so
            # errors surface as exceptions rather than C-style return codes.
            self._camera.acquire()
        except Exception as e:
            raise LibcameraError(f"Could not acquire camera: {e}")

        self._allocator = None
        self._mapped = {}    # FrameBuffer -> list of (mmap, offset, length)
        self._requests = []
        self._cookies = set()


    def _configure_streams(self, stream_configs: list):
        """
        stream_configs: list of (StreamRole, PixelFormat, (width, height)) tuples.
        Returns the validated libcamera CameraConfiguration.
        """
        try:
            config = self._camera.generate_configuration([role for role, _, _ in stream_configs])
            for i, (_, pixel_format, (width, height)) in enumerate(stream_configs):
                stream_config = config.at(i)
                stream_config.pixel_format = pixel_format
                stream_config.size = libcamera.Size(width, height)
                stream_config.buffer_count = 3
            if config.validate() == libcamera.CameraConfiguration.Status.Invalid:
                raise LibcameraError("Invalid camera configuration")
            self._camera.configure(config)
        except LibcameraError:
            self._release()
            raise
        except Exception as e:
            self._release()
            raise LibcameraError(f"Camera configuration failed: {e}")
        return config


    def _allocate_and_map(self, streams: list):
        """Allocate framebuffers for each stream and build one Request per buffer index."""
        try:
            self._allocator = libcamera.FrameBufferAllocator(self._camera)
            for stream in streams:
                if self._allocator.allocate(stream) < 1:
                    raise LibcameraError("Camera buffer allocation failed")

            num_buffers = len(self._allocator.buffers(streams[0]))
            for i in range(num_buffers):
                cookie = next(BaseLibcameraSession._request_cookies)
                request = self._camera.create_request(cookie)
                for stream in streams:
                    framebuffer = self._allocator.buffers(stream)[i]
                    request.add_buffer(stream, framebuffer)
                    self._mapped[framebuffer] = mmap_buffer(framebuffer)
                self._requests.append(request)
                self._cookies.add(cookie)
        except LibcameraError:
            self._release()
            raise
        except Exception as e:
            self._release()
            raise LibcameraError(f"Camera buffer setup failed: {e}")


    def _plane_bytes(self, framebuffer, plane_index: int = 0, length: int = None) -> bytes:
        """
        Copy a plane's current contents out of its dmabuf. Copying (rather than
        holding a view) lets the request be requeued immediately without the ISP
        overwriting data a consumer is still reading.
        """
        mapped_plane, offset, plane_length = self._mapped[framebuffer][plane_index]
        return bytes(mapped_plane[offset: offset + (length if length is not None else plane_length)])


    def _release(self):
        for maps in self._mapped.values():
            for mapped_plane, _, _ in maps:
                mapped_plane.close()
        self._mapped.clear()
        self._requests.clear()
        try:
            self._camera.release()
        except Exception as e:
            logger.warning(f"Error releasing camera: {e}")



class LibcameraVideoStream(BaseLibcameraSession):
    """
    Threaded video stream on the native libcamera python bindings; replaces the
    picamera-based PiVideoStream.

    Configures two ISP output streams in the same capture session:
      - main:  XBGR8888 (memory order R,G,B,X) for the live preview; PIL reads
               it directly as RGBA with zero conversion
      - lores: YUV420, whose Y plane is exactly the (pixels, width, height)
               grayscale tuple our pyzbar fork decodes; no numpy anywhere

    read()      -> (y_bytes, width, height) | None   # pyzbar-ready
    read_rgba() -> (rgba_bytes, stride, width, height) | None
    """
    def __init__(self, resolution=(512, 384), framerate=12):
        super().__init__()
        self.framerate = framerate
        self._lock = threading.Lock()
        self._latest_rgba = None   # (bytes, stride)
        self._latest_y = None      # stride-stripped bytes
        self._stop_event = threading.Event()
        self._stopped_event = threading.Event()
        self._thread = None

        config = self._configure_streams([
            (libcamera.StreamRole.Viewfinder, libcamera.formats.XBGR8888, resolution),
            (libcamera.StreamRole.Viewfinder, libcamera.formats.YUV420, resolution),
        ])
        main, lores = config.at(0), config.at(1)
        self._main_stream, self._lores_stream = main.stream, lores.stream
        self._main_stride, self._lores_stride = main.stride, lores.stride
        # validate() may adjust the requested size; use the actuals
        self.width, self.height = main.size.width, main.size.height

        self._allocate_and_map([self._main_stream, self._lores_stream])


    def start(self):
        frame_time = MICROSECONDS_PER_SECOND // self.framerate
        try:
            self._camera.start({libcamera.controls.FrameDurationLimits: (frame_time, frame_time)})
        except Exception as e:
            self._release()
            raise LibcameraError(f"Camera failed to start: {e}")
        for request in self._requests:
            self._camera.queue_request(request)
        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()
        return self


    def _event_loop(self):
        selector = selectors.DefaultSelector()
        selector.register(self._camera_manager.event_fd, selectors.EVENT_READ)
        while not self._stop_event.is_set():
            if not selector.select(timeout=0.2):
                continue
            for request in self._camera_manager.get_ready_requests():
                if request.cookie not in self._cookies:
                    # Straggler from a previous (stopped) capture session
                    continue
                if request.status == libcamera.Request.Status.Complete:
                    rgba = self._plane_bytes(request.buffers[self._main_stream])
                    y = strip_stride(
                        self._plane_bytes(request.buffers[self._lores_stream],
                                          length=self._lores_stride * self.height),
                        self._lores_stride, self.width, self.height)
                    with self._lock:
                        self._latest_rgba = (rgba, self._main_stride)
                        self._latest_y = y
                if not self._stop_event.is_set():
                    request.reuse()  # python bindings take no args; buffers are kept
                    self._camera.queue_request(request)
        selector.close()
        try:
            self._camera.stop()
        except Exception as e:
            logger.warning(f"Error stopping camera: {e}")
        self._release()
        self._stopped_event.set()


    def read(self):
        """Latest frame's Y plane as the (pixels, width, height) tuple pyzbar accepts."""
        with self._lock:
            if self._latest_y is None:
                return None
            return (self._latest_y, self.width, self.height)


    def read_rgba(self):
        """Latest frame's raw RGBA bytes as (data, stride, width, height)."""
        with self._lock:
            if self._latest_rgba is None:
                return None
            return (*self._latest_rgba, self.width, self.height)


    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            if not self._stopped_event.wait(timeout=2.0):
                logger.warning("LibcameraVideoStream: capture thread did not stop within 2s")
        else:
            # start() was never called; tear down directly
            self._release()



class LibcameraStillCapture(BaseLibcameraSession):
    """
    Single-frame capture; replaces the PiCamera single frame mode used for
    image entropy and QR brightness calibration.

    start() begins a free-running capture so auto-exposure and auto-white-balance
    can converge (callers already sleep briefly before capturing, as they did
    with picamera). capture_locked_frame() then locks AE/AWB at their converged
    values (the same semantics as picamera's shutter_speed/awb_gains freeze)
    and returns the frame as a PIL RGB image (no JPEG round trip needed).
    """
    def __init__(self, resolution=(720, 480)):
        super().__init__()
        config = self._configure_streams([
            (libcamera.StreamRole.StillCapture, libcamera.formats.XBGR8888, resolution),
        ])
        still = config.at(0)
        self._stream = still.stream
        self._stride = still.stride
        self.width, self.height = still.size.width, still.size.height

        self._allocate_and_map([self._stream])
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._camera_manager.event_fd, selectors.EVENT_READ)


    def start(self):
        try:
            self._camera.start()
        except Exception as e:
            self._release()
            raise LibcameraError(f"Camera failed to start: {e}")
        for request in self._requests:
            self._camera.queue_request(request)
        return self


    def _wait_for_frame(self, timeout: float = 2.0):
        """Block until a request completes; returns it without requeueing."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._selector.select(timeout=0.2):
                continue
            completed = None
            for request in self._camera_manager.get_ready_requests():
                if request.cookie not in self._cookies:
                    # Straggler from a previous (stopped) capture session
                    continue
                if request.status == libcamera.Request.Status.Complete and completed is None:
                    completed = request
                else:
                    request.reuse()
                    self._camera.queue_request(request)
            if completed is not None:
                return completed
        raise LibcameraError("Timed out waiting for camera frame")


    def capture_locked_frame(self) -> Image.Image:
        # Read the converged auto-exposure/AWB values off a live frame...
        request = self._wait_for_frame()
        metadata = dict(request.metadata)
        exposure_time = metadata.get(libcamera.controls.ExposureTime)
        analogue_gain = metadata.get(libcamera.controls.AnalogueGain)
        colour_gains = metadata.get(libcamera.controls.ColourGains)
        request.reuse()

        # ...then lock them in for the real capture. Setting explicit
        # ExposureTime/AnalogueGain disables AE on the RPi pipeline; AeEnable is
        # guarded because libcamera >= 0.5 deprecates it.
        if hasattr(libcamera.controls, "AeEnable"):
            request.set_control(libcamera.controls.AeEnable, False)
        if exposure_time is not None:
            request.set_control(libcamera.controls.ExposureTime, exposure_time)
        if analogue_gain is not None:
            request.set_control(libcamera.controls.AnalogueGain, analogue_gain)
        if colour_gains is not None:
            request.set_control(libcamera.controls.AwbEnable, False)
            request.set_control(libcamera.controls.ColourGains, colour_gains)
        self._camera.queue_request(request)

        request = self._wait_for_frame()
        frame = self._plane_bytes(request.buffers[self._stream])
        request.reuse()
        self._camera.queue_request(request)

        return rgba_buffer_to_image(frame, self._stride, self.width, self.height).convert("RGB")


    def stop(self):
        self._selector.close()
        try:
            self._camera.stop()
        except Exception as e:
            logger.warning(f"Error stopping camera: {e}")
        self._release()
