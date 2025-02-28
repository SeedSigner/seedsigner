import time

from dataclasses import dataclass
from gettext import gettext as _
from PIL import Image, ImageDraw

from seedsigner.gui import renderer
from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.threads import BaseThread, ThreadsafeCounter

from .screen import BaseScreen




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

    FRAME__ADDED_PART = 1
    FRAME__REPEATED_PART = 2
    FRAME__MISS = 3

    def __post_init__(self):
        from seedsigner.hardware.camera import Camera
        # Initialize the base class
        super().__post_init__()

        # TODO: Arrange this with UI elements rather than text
        self.instructions_text = "< " + _("back") + "  |  " + _(self.instructions_text)

        self.camera = Camera.get_instance()
        self.camera.start_video_stream_mode(resolution=self.resolution, framerate=self.framerate, format="rgb")

        self.frames_decode_status = ThreadsafeCounter()
        self.frames_decoded_counter = ThreadsafeCounter()

        self.threads.append(ScanScreen.LivePreviewThread(
            decoder=self.decoder,
            renderer=self.renderer,
            instructions_text=self.instructions_text,
            render_rect=self.render_rect,
            frame_decode_status=self.frames_decode_status,
            frames_decoded_counter=self.frames_decoded_counter,
        ))


    class LivePreviewThread(BaseThread):
        def __init__(self, decoder: DecodeQR, renderer: renderer.Renderer, instructions_text: str, render_rect: tuple[int,int,int,int], frame_decode_status: ThreadsafeCounter, frames_decoded_counter: ThreadsafeCounter):
            from seedsigner.hardware.camera import Camera

            self.camera = Camera.get_instance()
            self.decoder = decoder
            self.renderer = renderer
            self.instructions_text = instructions_text
            if render_rect:
                self.render_rect = render_rect            
            else:
                self.render_rect = (0, 0, self.renderer.canvas_width, self.renderer.canvas_height)
            self.frame_decode_status = frame_decode_status
            self.frames_decoded_counter = frames_decoded_counter
            self.last_frame_decoded_count = self.frames_decoded_counter.cur_count
            self.render_width = self.render_rect[2] - self.render_rect[0]
            self.render_height = self.render_rect[3] - self.render_rect[1]
            self.decoder_fps = "0.0"

            super().__init__()


        def run(self):
            from timeit import default_timer as timer

            instructions_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_button_font_size())

            # pre-calculate how big the animated QR percent display can be
            left, top, right, bottom = instructions_font.getbbox("100%")
            progress_text_width = right - left

            start_time = time.time()
            num_frames = 0
            debug = False
            show_framerate = False  # enable for debugging / testing
            while self.keep_running:
                frame = self.camera.read_video_stream(as_image=True)
                if frame is not None:
                    num_frames += 1
                    cur_time = time.time()
                    cur_fps = num_frames / (cur_time - start_time)
                    
                    scan_text = None
                    progress_percentage = self.decoder.get_percent_complete()
                    if progress_percentage == 0:
                        # We've just started scanning, no results yet
                        if show_framerate:
                            scan_text = f"{cur_fps:0.2f} | {self.decoder_fps}"
                        else:
                            scan_text = self.instructions_text

                    elif debug:
                        # Special debugging output for animated QRs
                        scan_text = f"{self.decoder.get_percent_complete()}% | {self.decoder.get_percent_complete(weight_mixed_frames=True)}% (new)"
                        if show_framerate:
                            scan_text += f" {cur_fps:0.2f} | {self.decoder_fps}"

                    with self.renderer.lock:
                        if frame.width > self.render_width or frame.height > self.render_height:
                            frame = frame.resize(
                                (self.render_width, self.render_height),
                                resample=Image.NEAREST  # Use nearest neighbor for max speed
                            )

                        if scan_text:
                            # Note: shadowed text (adding a 'stroke' outline) can
                            # significantly slow down the rendering.
                            # Temp solution: render a slight 1px shadow behind the text
                            # TODO: Replace the instructions_text with a disappearing
                            # toast/popup (see: QR Brightness UI)?
                            draw = ImageDraw.Draw(frame)
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

                        else:
                            # Render the progress bar
                            rectangle = Image.new('RGBA', (self.renderer.canvas_width - 2*GUIConstants.EDGE_PADDING, GUIConstants.BUTTON_HEIGHT), (0, 0, 0, 0))
                            draw = ImageDraw.Draw(rectangle)

                            # Start with a background rounded rectangle, same dims as the buttons
                            overlay_color = (0, 0, 0, 191)  # opacity ranges from 0-255
                            draw.rounded_rectangle(
                                (
                                    (0, 0),
                                    (rectangle.width, rectangle.height)
                                ),
                                fill=overlay_color,
                                radius=8,
                                outline=overlay_color,
                                width=2,
                            )

                            progress_bar_thickness = 4
                            progress_bar_width = rectangle.width - 2*GUIConstants.EDGE_PADDING - progress_text_width - int(GUIConstants.EDGE_PADDING/2)
                            progress_bar_xy = (
                                    (GUIConstants.EDGE_PADDING, int((rectangle.height - progress_bar_thickness) / 2)),
                                    (GUIConstants.EDGE_PADDING + progress_bar_width, int(rectangle.height + progress_bar_thickness) / 2)
                                )
                            draw.rounded_rectangle(
                                progress_bar_xy,
                                fill=GUIConstants.INACTIVE_COLOR,
                                radius=8
                            )

                            progress_percentage = self.decoder.get_percent_complete(weight_mixed_frames=True)
                            draw.rounded_rectangle(
                                (
                                    progress_bar_xy[0],
                                    (GUIConstants.EDGE_PADDING + int(progress_percentage * progress_bar_width / 100.0), progress_bar_xy[1][1])
                                ),
                                fill=GUIConstants.GREEN_INDICATOR_COLOR,
                                radius=8
                            )

                            # TRANSLATOR_NOTE: Inserts the percentage value of the animated QR scan progress
                            text = _("{}%").format(progress_percentage)

                            draw.text(
                                xy=(rectangle.width - GUIConstants.EDGE_PADDING, int(rectangle.height / 2)),
                                text=text,
                                fill=GUIConstants.BODY_FONT_COLOR,
                                font=instructions_font,
                                anchor="rm",  # right-justified, middle
                            )

                            frame.paste(rectangle, (GUIConstants.EDGE_PADDING, self.renderer.canvas_height - GUIConstants.EDGE_PADDING - rectangle.height), rectangle)

                            # Render the dot to indicate successful QR frame read
                            indicator_size = 10
                            self.last_frame_decoded_count = self.frames_decoded_counter.cur_count
                            status_color_map = {
                                ScanScreen.FRAME__ADDED_PART: GUIConstants.SUCCESS_COLOR,
                                ScanScreen.FRAME__REPEATED_PART: GUIConstants.INACTIVE_COLOR,
                                ScanScreen.FRAME__MISS: None,
                            }
                            status_color = status_color_map.get(self.frame_decode_status.cur_count)
                            if status_color:
                                # Good! Most recent frame successfully decoded.
                                # Draw the onscreen indicator dot
                                draw = ImageDraw.Draw(frame)
                                draw.ellipse(
                                    (
                                        (self.renderer.canvas_width - GUIConstants.EDGE_PADDING - indicator_size, self.renderer.canvas_height - GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT - GUIConstants.COMPONENT_PADDING - indicator_size),
                                        (self.renderer.canvas_width - GUIConstants.EDGE_PADDING, self.renderer.canvas_height - GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT - GUIConstants.COMPONENT_PADDING)
                                    ),
                                    fill=status_color,
                                    outline="black",
                                    width=1,
                                )

                        self.renderer.show_image(frame, show_direct=True)

                if self.camera._video_stream is None:
                    break


    def _run(self):
        """
            _render() is mostly meant to be a one-time initial drawing call to set up the
            Screen. Once interaction starts, the display updates have to be managed in
            _run(). The live preview is an extra-complex case.
        """
        from seedsigner.hardware.buttons import HardwareButtonsConstants
        from seedsigner.models.decode_qr import DecodeQRStatus

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

                self.frames_decoded_counter.increment()
                # Notify the live preview thread how our most recent decode went
                if status == DecodeQRStatus.FALSE:
                    # Did not find anything to decode in the current frame
                    self.frames_decode_status.set_value(self.FRAME__MISS)

                else:
                    if status == DecodeQRStatus.PART_COMPLETE:
                        # We received a valid frame that added new data
                        self.frames_decode_status.set_value(self.FRAME__ADDED_PART)

                    elif status == DecodeQRStatus.PART_EXISTING:
                        # We received a valid frame, but we've already seen in
                        self.frames_decode_status.set_value(self.FRAME__REPEATED_PART)
                
                if self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_RIGHT) or self.hw_inputs.check_for_low(HardwareButtonsConstants.KEY_LEFT):
                    self.camera.stop_video_stream_mode()
                    break

