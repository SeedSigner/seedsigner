import qrcode

class QR:

    def __init__(self) -> None:
        return

    def qrimage(self, data):

        qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=2 )
        qr.add_data(data)
        qr.make(fit=True)
        return(qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB'))