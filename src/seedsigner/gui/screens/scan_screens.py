import time

from dataclasses import dataclass
from PIL import Image, ImageDraw

from seedsigner.gui import renderer
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.hardware.camera import Camera
from seedsigner.models import DecodeQR, DecodeQRStatus
from seedsigner.models.threads import BaseThread

from .screen import BaseScreen, ButtonListScreen
from ..components import GUIConstants, Fonts, TextArea




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
    set a modest fps target for the camera: 4fps. At this pace, the decoder and the live
    display can more or less keep up with the flow of frames without much wasted effort
    in any of the threads.

    The resolution (480x480) has not been tweaked in order to guarantee that our
    decoding abilities remain as-is. It's possible that more optimizations could be made
    here (e.g. higher res w/no performance impact? Lower res w/same decoding but faster
    performance? etc).

    Note: This is quite a lot of important tasks for a Screen to be managing; much of
    this should probably be refactored into the Controller.
    """
    decoder: DecodeQR = None
    instructions_text: str = "< back  |  Scan a QR code"
    resolution: tuple[int,int] = (480, 480)
    framerate: int = 4  # TODO: alternate optimization for Pi Zero 2W
    render_rect: tuple[int,int,int,int] = None


    def __post_init__(self):
        from seedsigner.hardware.camera import Camera
        # Initialize the base class
        super().__post_init__()

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

            super().__init__()


        def run(self):
            from timeit import default_timer as timer

            instructions_font = Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BUTTON_FONT_SIZE)

            start_time = time.time()
            num_frames = 0
            show_framerate = True  # enable for debugging / testing
            while self.keep_running:
                start = timer()
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    num_frames += 1
                    cur_time = time.time()
                    cur_fps = num_frames / (cur_time - start_time)
                    if self.decoder and self.decoder.get_percent_complete() > 0 and self.decoder.is_psbt:
                        scan_text = str(self.decoder.get_percent_complete()) + "% Complete"
                        if show_framerate:
                            scan_text += f" {cur_fps:0.2f} fps"
                    else:
                        if show_framerate:
                            scan_text = f"{cur_fps:0.2f} fps"
                        else:
                            scan_text = self.instructions_text

                    with self.renderer.lock:
                        if frame.width > self.render_width or frame.height > self.render_height:
                            frame = frame.resize(
                                (self.render_width, self.render_height),
                                resample=Image.NEAREST
                            )
                        # self.renderer.canvas.paste(
                        #     frame,
                        #     (self.render_rect[0], self.render_rect[1])
                        # )

                        draw = ImageDraw.Draw(frame)

                        if scan_text:
                            draw.text(
                                xy=(
                                    int(self.renderer.canvas_width/2),
                                    self.renderer.canvas_height - GUIConstants.EDGE_PADDING
                                ),
                                text=scan_text,
                                fill=GUIConstants.BODY_FONT_COLOR,
                                font=instructions_font,
                                stroke_width=4,
                                stroke_fill=GUIConstants.BACKGROUND_COLOR,
                                anchor="ms"
                            )

                        self.renderer.disp.ShowImage(frame, 0, 0)

                        end = timer()
                        framerate = 1.0/(end - start)
                        # print(f"{framerate:0.2f} fps")

                if self.camera._video_stream is None:
                    break


    def _run(self):
        """
            _render() is mostly meant to be a one-time initial drawing call to set up the
            Screen. Once interaction starts, the display updates have to be managed in
            _run(). The live preview is an extra-complex case.
        """
        from timeit import default_timer as timer
        while True:
            start = timer()
            frame = self.camera.read_video_stream()
            if frame is not None:
                # print("Decoder checking next frame")
                status = self.decoder.add_image(frame)

                if status in (DecodeQRStatus.COMPLETE, DecodeQRStatus.INVALID):
                    self.camera.stop_video_stream_mode()
                    break
                
                # TODO: KEY_UP gives control to NavBar; use its back arrow to cancel
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break

            # Have the decoder thread sleep until (roughly) the next frame is ready in
            # order to avoid wasting CPU cycles re-checking the same frame.
            elapsed = (timer() - start)
            if elapsed < 1.0/float(self.framerate):
                time.sleep(1.0/float(self.framerate) - elapsed)



@dataclass
class SettingsUpdatedScreen(ButtonListScreen):
    config_name: str = None
    title: str = "Settings QR"
    is_bottom_list: bool = True

    def __post_init__(self):
        # Customize defaults
        self.button_data = ["Home"]

        super().__post_init__()

        start_y = self.top_nav.height + 20
        if self.config_name:
            self.config_name_textarea = TextArea(
                text=f'"{self.config_name}"',
                is_text_centered=True,
                auto_line_break=True,
                screen_y=start_y
            )
            self.components.append(self.config_name_textarea)
            start_y = self.config_name_textarea.screen_y + 50
        
        self.components.append(TextArea(
            text="Settings imported successfully!",
            is_text_centered=True,
            auto_line_break=True,
            screen_y=start_y
        ))

