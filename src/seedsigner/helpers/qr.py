import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import CircleModuleDrawer, GappedSquareModuleDrawer
from PIL import Image
import subprocess

class QR:
    STYLE__DEFAULT = 1
    STYLE__ROUNDED = 2
    STYLE__GRID = 3

    def __init__(self) -> None:
        return

    def qrimage(self, data, width=240, height=240, border=3, style=None, background_color="#444"):
        qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=border )
        qr.add_data(data)
        qr.make(fit=True)
        if not style or style == QR.STYLE__DEFAULT:
            return qr.make_image(fill_color="black", back_color=background_color).resize((width,height)).convert('RGBA')
        else:
            if style == QR.STYLE__ROUNDED:
                return qr.make_image(
                    fill_color="black",
                    back_color=background_color,
                    image_factory=StyledPilImage,
                    module_drawer=CircleModuleDrawer()
                ).resize((width,height)).convert('RGBA')

            elif style == QR.STYLE__GRID:
                return qr.make_image(
                    fill_color="black",
                    back_color=background_color,
                    image_factory=StyledPilImage,
                    module_drawer=GappedSquareModuleDrawer()
                ).resize((width,height)).convert('RGBA')


    def qrimage_io(self, data, width=240, height=240, border=3, background_color="808080"):
        if 1 <= border <= 10:
            border_str = str(border)
        else:
            border_str = "3"

        cmd = f"""qrencode -m {border_str} -s 3 -l L --foreground=000000 --background={background_color} -t PNG -o "/tmp/qrcode.png" "{str(data)}" """
        rv = subprocess.call(cmd, shell=True)

        # if qrencode fails, fall back to only encoder
        if rv != 0:
            return self.qrimage(data,width,height,border)
        img = Image.open("/tmp/qrcode.png").resize((width,height), Image.NEAREST).convert("RGBA")

        return img
