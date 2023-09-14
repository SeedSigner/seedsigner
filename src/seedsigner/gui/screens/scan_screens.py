import time

from dataclasses import dataclass
from PIL import Image, ImageDraw

from seedsigner.gui import renderer
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.hardware.camera import Camera
from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.threads import BaseThread

from .screen import BaseScreen
from ..components import GUIConstants, Fonts




@dataclass
class ScanScreen(BaseScreen):
    """
    Live preview has to balance three competing threads:
    * Camera capturing frames and making them available to read.
    * Decoder analyzing frames for QR codes.
    * Live preview display writing frames to the screen.

    All of this would ideally be rewritten as in C/C++/Rust with python bindings for
    vastly improved performance.

    Until then, we have to balance the resources the Pi Zero has to work with. Thus, we
    set a modest fps target for the camera: 5fps. At this pace, the decoder and the live
    display can more or less keep up with the flow of frames without much wasted effort
    in any of the threads.

    Note: performance tuning was targeted for the Pi Zero.

    The resolution (480x480) has not been tweaked in order to guarantee that our
    decoding abilities remain as-is. It's possible that more optimizations could be made
    here (e.g. higher res w/no performance impact? Lower res w/same decoding but faster
    performance? etc).

    Note: This is quite a lot of important tasks for a Screen to be managing; much of
    this should probably be refactored into the Controller.
    """
    decoder: DecodeQR = None
    instructions_text: str = None
    resolution: tuple[int,int] = (480, 480)
    framerate: int = 6  # TODO: alternate optimization for Pi Zero 2W?
    render_rect: tuple[int,int,int,int] = None


    def __post_init__(self):
        from seedsigner.hardware.camera import Camera
        # Initialize the base class
        super().__post_init__()

        self.instructions_text = "< back  |  " + self.instructions_text

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=self.resolution, framerate=self.framerate, format="rgb")

        self.threads.append(ScanScreen.LivePreviewThread(
            camera=self.camera,
            decoder=self.decoder,
            renderer=self.renderer,
            instructions_text=self.instructions_text,
            render_rect=self.render_rect,
        ))


    class LivePreviewThread(BaseThread):
        def __init__(self, camera: Camera, decoder: DecodeQR, renderer: renderer.Renderer, instructions_text: str, render_rect: tuple[int,int,int,int]):
            self.camera = camera
            self.decoder = decoder
            self.renderer = renderer
            self.instructions_text = instructions_text
            if render_rect:
                self.render_rect = render_rect            
            else:
                self.render_rect = (0, 0, self.renderer.canvas_width, self.renderer.canvas_height)
            self.render_width = self.render_rect[2] - self.render_rect[0]
            self.render_height = self.render_rect[3] - self.render_rect[1]
            self.decoder_fps = "0.0"

            super().__init__()


        def run(self):

            instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

            start_time = time.time()
            num_frames = 0
            show_framerate = False  # enable for debugging / testing
            while self.keep_running:
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    num_frames += 1
                    cur_time = time.time()
                    cur_fps = num_frames / (cur_time - start_time)
                    if self.decoder and self.decoder.get_percent_complete() > 0 and self.decoder.is_psbt:
                        scan_text = str(self.decoder.get_percent_complete()) + "% Complete"
                        if show_framerate:
                            scan_text += f" {cur_fps:0.2f} | {self.decoder_fps}"
                    else:
                        if show_framerate:
                            scan_text = f"{cur_fps:0.2f} | {self.decoder_fps}"
                        else:
                            scan_text = self.instructions_text

                    with self.renderer.lock:
                        if frame.width > self.render_width or frame.height > self.render_height:
                            frame = frame.resize(
                                (self.render_width, self.render_height),
                                resample=Image.NEAREST  # Use nearest neighbor for max speed
                            )

                        draw = ImageDraw.Draw(frame)

                        if scan_text:
                            # Note: shadowed text (adding a 'stroke' outline) can
                            # significantly slow down the rendering.
                            # Temp solution: render a slight 1px shadow behind the text
                            # TODO: Replace the instructions_text with a disappearing
                            # toast/popup (see: QR Brightness UI)?
                            draw.text(xy=(
                                        int(self.renderer.canvas_width/2 + 2),
                                        self.renderer.canvas_height - GUIConstants.EDGE_PADDING + 2
                                     ),
                                     text=scan_text,
                                     fill="black",
                                     font=instructions_font,
                                     anchor="ms")

                            # Render the onscreen instructions
                            draw.text(xy=(
                                        int(self.renderer.canvas_width/2),
                                        self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                                     ),
                                     text=scan_text,
                                     fill=GUIConstants.BODY_FONT_COLOR,
                                     font=instructions_font,
                                     anchor="ms")

                        self.renderer.show_image(frame, show_direct=True)
                        # print(f" {cur_fps:0.2f} | {self.decoder_fps}")

                if self.camera._video_stream is None:
                    break


    def _run(self):
        """
            _render() is mostly meant to be a one-time initial drawing call to set up the
            Screen. Once interaction starts, the display updates have to be managed in
            _run(). The live preview is an extra-complex case.
        """
        num_frames = 0
        start_time = time.time()
        while True:
            frame = self.camera.read_video_stream()
            if frame is not None:
                status = self.decoder.add_image(frame)

                num_frames += 1
                decoder_fps = f"{num_frames / (time.time() - start_time):0.2f}"
                self.threads[0].decoder_fps = decoder_fps

                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break

