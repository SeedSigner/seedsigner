import qrcode

class QR:

    def __init__(self) -> None:
        self.qrsize = 120 # Default

    def qrimage(self, data, qrsize = 0):
        if qrsize != 0:
            self.qrsize = qrsize

        qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=2 )
        qr.add_data(data)
        qr.make(fit=True)
        return(qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB'))

    def makeqrcodes(self, data, format, qrsize = 0, callback = None) -> []:
        if qrsize != 0:
            self.qrsize = qrsize

        cnt = 0
        qr_cnt = 0
        start = 0
        stop = self.qrsize
        data_parts = []
        images = []

        if format == "Specter Desktop":

            qr_cnt = (len(data) // self.qrsize) + 1

            if qr_cnt == 1:
                return [self.qrimage(data)]
            else:
                while cnt < qr_cnt:

                    data_parts.append("p" + str(cnt+1) + "of" + str(qr_cnt) + " " + data[start:stop])
                    images.append(self.qrimage(data_parts[-1], qrsize))
                    print(data_parts[-1])
                    start = start + self.qrsize
                    stop = stop + self.qrsize
                    if stop > len(data):
                        stop = len(data)
                    cnt += 1

                    if callback != None:
                        callback((cnt * 100.0) / qr_cnt)

                return images