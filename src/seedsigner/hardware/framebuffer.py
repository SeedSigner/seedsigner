from PIL import Image
import mmap
import pyximport; pyximport.install()
from seedsigner.hardware.RGBtoBGR import rgbtobgr

class Framebuffer(object):
    def __init__(self, device_no: int):
        self.path = "/dev/fb%d" % device_no
        config_dir = "/sys/class/graphics/fb%d/" % device_no
        self.size = tuple(_read_config(config_dir + "virtual_size"))
        self.width = self.size[0]
        self.height = self.size[1]
        self.stride = _read_config(config_dir + "stride")[0]
        self.bits_per_pixel = _read_config(config_dir + "bits_per_pixel")[0]
        assert self.stride == self.bits_per_pixel // 8 * self.size[0]
        fp = open(self.path, "wb+")
        self.length = self.size[0] * self.size[1] * (self.bits_per_pixel >> 3)
        self.fb = mmap.mmap(fp.fileno(), length=self.length, access=mmap.ACCESS_WRITE)
        print(self)

    def __str__(self):
        args = (self.path, self.size, self.stride, self.bits_per_pixel)
        return "%s  size:%s  stride:%s  bits_per_pixel:%s" % args

    def show(self, image: Image):
        assert image.size == self.size

        rgbtobgr(image.tobytes(), self.fb, self.length)

    def on(self):
        pass

    def off(self):
        pass


def _read_config(filename):
    with open(filename, "r") as fp:
        content = fp.readline()
        tokens = content.strip().split(",")
        return [int(t) for t in tokens if t]
