from PIL import Image
import mmap
from seedsigner.hardware.RGBtoBGR import rgbtobgr
from io import BufferedRandom

class Framebuffer(object):
    def __init__(self, device_num: int = 0):
        self.path = f"/dev/fb{device_num}"
        config_dir = f"/sys/class/graphics/fb{device_num}/"
        self.size = tuple(_read_config(config_dir + "virtual_size"))
        self.width = self.size[0]
        self.height = self.size[1]
        self.stride = _read_config(config_dir + "stride")[0] # number of bytes per row of pixels
        self.bits_per_pixel = _read_config(config_dir + "bits_per_pixel")[0]
        if self.stride != self.width * (self.bits_per_pixel // 8):
            raise FramebufferException(f"Image stride ({self.stride}) does not match framebuffer width ({self.width}) and bits_per_pixel ({self.bits_per_pixel})")

        bufferedRandom: BufferedRandom = open(self.path, "wb+")
        self.length = self.width * self.height * (self.bits_per_pixel // 8)
        self.framebuffer = mmap.mmap(bufferedRandom.fileno(), length=self.length, access=mmap.ACCESS_WRITE)
        print(self)

    def __str__(self):
        return f"Framebuffer path: {self.path} | size: {self.size} | stride: {self.stride} | bits_per_pixel: {self.bits_per_pixel}"

    def show(self, image: Image):
        if self.size != image.size:
            raise FramebufferException(f"Image size ({image.size}) does not equal framebuffer size ({self.size})")

        rgbtobgr(image.tobytes(), self.framebuffer, self.length)

    def on(self):
        pass

    def off(self):
        pass


class FramebufferException(Exception): 
    pass


def _read_config(filename):
    with open(filename, "r") as fp:
        content = fp.readline()
        tokens = content.strip().split(",")
        return [int(t) for t in tokens if t]
