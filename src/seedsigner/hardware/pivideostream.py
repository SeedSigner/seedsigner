# import the necessary packages
import logging
import subprocess
import threading
import time
import os
from PIL import Image
import cv2
import numpy as np

from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants

logger = logging.getLogger(__name__)

class PiVideoStream:
    def __init__(self, device='/dev/video12', resolution=(2304,1296), pixelformat='NV12', framerate=10):


        hardware_config = Settings.get_instance().get_value(SettingsConstants.SETTING__HARDWARE_CONFIG)
        pin_mapping = SettingsConstants.ALL_HARDWARE_PIN_CONFIGS__PIN_DEFINITIONS[hardware_config]["camera"]

        self.device = pin_mapping["device"]
        self.width, self.height = pin_mapping["resolution"]
        self.pixelformat = pin_mapping["pixelformat"]
        self.framerate = pin_mapping["framerate"]

        if pixelformat == "NV12":
            self.frame_size = self.width * self.height * 3 // 2  # NV12 format size calculation
        else:
            self.frame_size = self.width * self.height # GreyScale format size calculation
        self.frame = None
        self.should_stop = False
        self.is_stopped = True
        self.lock = threading.Lock()  # Thread-safe frame handling
        self.save_path = './saved_frames'  # Directory to save images (both pre and post conversion)
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)  # Ensure the save directory exists
        logger.debug(f"Initialized PiVideoStream with device={device}, resolution={resolution}, "
              f"pixelformat={pixelformat}, framerate={framerate}")

    def start(self):
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        self.is_stopped = False
        return self

    def update(self):
        cmd = [
            'v4l2-ctl',
            f'--device={self.device}',
            f'--set-fmt-video=width={self.width},height={self.height},pixelformat={self.pixelformat}',
            '--stream-mmap',
            '--stream-to=-',
            '--stream-count=0'  # Infinite stream
        ]
        
        logger.debug(f"Running command: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10 * self.frame_size
        )



        while not self.should_stop:
            try:
                start_time = time.time()

                # Read frame data
                frame_data = process.stdout.read(self.frame_size)
                read_time = time.time() - start_time

                if len(frame_data) < self.frame_size:
                    logger.error(f"Incomplete frame data received: {len(frame_data)} bytes")
                    break

                logger.debug(f"Frame read time: {read_time:.6f} seconds")
                start_processing = time.time()

                with self.lock:
                    # DEBUG: Save NV12 frame TO DISK (Optional)
                    # WILL QUICKLY FILL UP SPACE
                    # self.save_pre_rgb(frame_data)

                    # Record time for conversion
                    start_conversion = time.time()
                    if self.pixelformat == "NV12":
                        # Python Implementation
                        # self.frame = self.nv12_to_rgb(frame_data)
                        # C Implementation
                        # self.frame = self.nv12_to_rgb_subprocess(frame_data, self.width, self.height)
                        # OpenCV Implementation
                        self.frame = self.nv12_to_rgb_opencv(frame_data, self.width, self.height)
                    elif self.pixelformat == "GREY":
                        self.frame = self.grey_to_pil(frame_data, self.width, self.height)
                    else:
                        self.frame = None
                        raise Exception("Unable to read from camera")

                    conversion_time = time.time() - start_conversion
                    logger.debug(f"{self.pixelformat} to PIL Image conversion time: {conversion_time:.6f} seconds")

                processing_time = time.time() - start_processing
                logger.debug(f"Frame processing time (read+conversion): {processing_time:.6f} seconds")

            except Exception as e:
                logger.error(f"Error while reading frame: {e}")
                break

        process.terminate()
        process.wait()
        self.is_stopped = True
        logger.debug("Video stream stopped.")

    def read(self):
        with self.lock:
            if self.frame is not None:
                pass
                # logger.debug(f"Reading frame: {self.frame.size}")
            else:
                #logger.debug("No frame available to read.")
                iii =0 
            return self.frame

    def stop(self):
        self.should_stop = True
        while not self.is_stopped:
            time.sleep(0.01)


    def nv12_to_rgb_opencv(self, frame_data, width, height):
        """
        Converts NV12 format to a PIL RGB Image using a C subprocess.

        Args:
            frame_data (bytes): NV12 frame data.

        Returns:
            Image: PIL Image in RGB format.
        """

        # Convert NV12 to RGB using OpenCV
        nv12_array = np.frombuffer(frame_data, dtype=np.uint8)
        nv12_frame = nv12_array.reshape((height * 3 // 2, width))
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(nv12_frame, cv2.COLOR_YUV2RGB_NV12)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_frame)
        return pil_image


    def nv12_to_rgb_subprocess(self, frame_data, width, height):
        """
        Converts NV12 format to a PIL RGB Image using a C subprocess.

        Args:
            frame_data (bytes): NV12 frame data.

        Returns:
            Image: PIL Image in RGB format.
        """
        WIDTH = width
        HEIGHT = height

        # Declare Temporary Files
        rgb_file = "/tmp/rgb_frame.bin"
        nv12_file = "/tmp/nv12_frame.bin"

        # Save NV12 frame data to a temporary file
        with open(nv12_file, "wb") as f:
            f.write(frame_data)

        # Run the C converter subprocess
        cmd = [
            "/nv12_converter",
            nv12_file,
            rgb_file,
            str(WIDTH),
            str(HEIGHT),
        ]
        subprocess.run(cmd, check=True)

        # Load the RGB data from the output file
        with open(rgb_file, "rb") as f:
            rgb_data = f.read()

        # Create a PIL image from the RGB data
        img = Image.frombytes("RGB", (WIDTH, HEIGHT), rgb_data)

        # Resize if necessary (e.g., for a display resolution of 240x240)
        # Should I instead crop, then resize to minimize the distortion?
        if WIDTH != 240 or HEIGHT != 240:
            # img = self.crop_to_square(img)
            img = img.resize((240, 240))

        # Clean up temporary files
        os.remove(nv12_file)
        os.remove(rgb_file)

        return img

    def grey_to_pil(self, frame_data, width, height):
        """
        Converts grayscale bytes to a PIL Image.

        Args:
            frame_data (bytes): Grayscale frame data.
            width (int): Width of the frame.
            height (int): Height of the frame.

        Returns:
            Image: PIL Image in Grayscale format.
        """
        # Create a PIL image from the grayscale data
        img = Image.frombytes("L", (width, height), frame_data)

        # Resize if necessary (e.g., for a display resolution of 240x240)
        if width != 240 or height != 240:
            # img = self.crop_to_square(img)
            img = img.resize((240, 240))

        return img

    def crop_to_square(self, image):
        width, height = image.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        return image.crop((left, top, right, bottom))