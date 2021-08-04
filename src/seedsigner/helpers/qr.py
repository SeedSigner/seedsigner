import qrcode
from PIL import Image
import subprocess

class QR:

    def __init__(self) -> None:
        return

    def qrimage(self, data, width=240, height=240, border=3):
        qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=border )
        qr.add_data(data)
        qr.make(fit=True)
        return(qr.make_image(fill_color="black", back_color="white").resize((width,height)).convert('RGB'))

    def qrimage_io(self, data, width=240, height=240, border=3):
        if 1 <= border <= 10:
            border_str = str(border)
        else:
            border_str = "3"

        cmd = 'qrencode -m '+border_str+' -s 3 -l L --foreground=000000 --background=FFFFFF -t PNG -o "/dev/shm/qrcode.png" "' + str(data) + '"'
        rv = subprocess.call(cmd, shell=True)

        # if qrencode fails, fall back to only encoder
        if rv != 0:
            return self.qrimage(data,width,height,border)
        img = Image.open("/dev/shm/qrcode.png").resize((width,height), Image.NEAREST).convert("RGBA")

        return img