import qrcode

class QR:

    def __init__(self) -> None:
        return

    def qrimage(self, data, width=240, height=240, border=3):
        qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=border )
        qr.add_data(data)
        qr.make(fit=True)
        return(qr.make_image(fill_color="black", back_color="white").resize((width,height)).convert('RGB'))
