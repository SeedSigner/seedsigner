from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus, SignMessageQrDecoder
from seedsigner.models.qr_type import QRType



class TestSignMessageQrDecoder:
    """
    Expected QR data format:

        signmessage {derivation_path} ascii:{message}
    """
    derivation_path = "m/84h/0h/0h/0/0"


    def test_decode_sign_message_request(self):
        message = "I attest that I control this bitcoin address"
        data = f"signmessage {self.derivation_path} ascii:{message}"

        decoder = DecodeQR()
        assert decoder.add_data(data) == DecodeQRStatus.COMPLETE
        assert decoder.is_sign_message

        qr_data = decoder.get_qr_data()
        assert qr_data["derivation_path"] == self.derivation_path.replace("h", "'")
        assert qr_data["message"] == message


    def test_message_may_contain_spaces_and_colons(self):
        """ Only the first colon separates the format from the payload """
        message = "notice: the times 03/Jan/2009 ascii:not a separator"
        data = f"signmessage {self.derivation_path} ascii:{message}"

        decoder = SignMessageQrDecoder()
        assert decoder.add(data) == DecodeQRStatus.COMPLETE
        assert decoder.get_qr_data()["message"] == message


    def test_malformed_data_is_rejected_without_raising(self):
        """
            Should return INVALID rather than raise on malformed data.

            An uncaught exception here propagates out of `ScanScreen._run()` and routes
            the user to the generic "System Error" screen instead of the "Unknown QR
            Type" warning. The scanner is the device's primary untrusted input, so no
            QR payload should be able to raise from the decoder.
        """
        for data in [
            "signmessage",                                  # no derivation path, no message
            f"signmessage {self.derivation_path}",          # no message
            f"signmessage {self.derivation_path} nocolon",  # no format separator
        ]:
            decoder = SignMessageQrDecoder()
            assert decoder.add(data) == DecodeQRStatus.INVALID, f"should have rejected {data!r}"

            # Same via the top-level DecodeQR entry point used by the scanner
            decoder = DecodeQR()
            assert decoder.detect_segment_type(data) == QRType.SIGN_MESSAGE
            assert decoder.add_data(data) == DecodeQRStatus.INVALID


    def test_unsupported_format_is_rejected(self):
        data = f"signmessage {self.derivation_path} utf8:¡hola!"
        decoder = SignMessageQrDecoder()
        assert decoder.add(data) == DecodeQRStatus.INVALID
