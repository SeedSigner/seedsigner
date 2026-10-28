from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus, SignMessageQrDecoder


class TestSignMessageQrDecoder:
    def test_decode_sign_message_valid(self):
        """
        Should successfully decode a valid single-frame signmessage QR payload.
        """
        qr_str = "signmessage m/84h/0h/0h/0/0 ascii:Hello Bitcoin!"
        decoder = DecodeQR()
        status = decoder.add_data(qr_str)

        assert decoder.is_sign_message
        assert status == DecodeQRStatus.COMPLETE

        qr_data = decoder.get_qr_data()
        assert qr_data["derivation_path"] == "m/84'/0'/0'/0/0"
        assert qr_data["message"] == "Hello Bitcoin!"


    def test_decode_sign_message_with_spaces_in_message(self):
        """
        Should preserve multi-word messages with spaces.
        """
        msg = "Verify ownership of Bitcoin address for exchange audit 2026."
        qr_str = f"signmessage m/84h/0h/0h/0/0 ascii:{msg}"
        decoder = DecodeQR()
        status = decoder.add_data(qr_str)

        assert status == DecodeQRStatus.COMPLETE
        qr_data = decoder.get_qr_data()
        assert qr_data["message"] == msg


    def test_decode_sign_message_insufficient_parts(self):
        """
        Should return DecodeQRStatus.INVALID instead of raising IndexError when payload is missing required parts.
        """
        # Only 'signmessage' token
        decoder = DecodeQR()
        status = decoder.add_data("signmessage")
        assert status == DecodeQRStatus.INVALID

        # 'signmessage' with only derivation path, missing message part
        decoder = DecodeQR()
        status = decoder.add_data("signmessage m/84h/0h/0h")
        assert status == DecodeQRStatus.INVALID


    def test_decode_sign_message_missing_colon_format_prefix(self):
        """
        Should return DecodeQRStatus.INVALID when the message part lacks the format colon separator.
        """
        decoder = DecodeQR()
        status = decoder.add_data("signmessage m/84h/0h/0h asciimessage")
        assert status == DecodeQRStatus.INVALID


    def test_decode_sign_message_unsupported_format(self):
        """
        Should return DecodeQRStatus.INVALID when format is not 'ascii'.
        """
        decoder = DecodeQR()
        status = decoder.add_data("signmessage m/84h/0h/0h hex:123456")
        assert status == DecodeQRStatus.INVALID


    def test_direct_sign_message_decoder_instance(self):
        """
        Directly test SignMessageQrDecoder unit methods and edge cases.
        """
        decoder = SignMessageQrDecoder()
        assert decoder.get_qr_data() == dict(derivation_path=None, message=None)

        # Incomplete / empty payload
        assert decoder.add("") == DecodeQRStatus.INVALID
        assert decoder.add("signmessage") == DecodeQRStatus.INVALID
        assert decoder.add("signmessage m/84h/0h/0h") == DecodeQRStatus.INVALID


    def test_decode_sign_message_invalid_command_token(self):
        """
        Should return DecodeQRStatus.INVALID when command token is not strictly 'signmessage'.
        """
        for bad_cmd in ["signmessage_v2", "signmessage:foo", "SIGNMESSAGE"]:
            decoder = DecodeQR()
            status = decoder.add_data(f"{bad_cmd} m/84h/0h/0h ascii:test")
            assert status == DecodeQRStatus.INVALID


    def test_decode_sign_message_path_contains_format_prefix_substring(self):
        """
        Should not split prematurely when the derivation path contains 'ascii:'.
        """
        qr_str = "signmessage m/84h/0h/ascii:test/0/0 ascii:Real message content"
        decoder = DecodeQR()
        status = decoder.add_data(qr_str)
        assert status == DecodeQRStatus.COMPLETE
        qr_data = decoder.get_qr_data()
        assert qr_data["message"] == "Real message content"


    def test_decode_sign_message_empty_message(self):
        """
        Should safely handle an empty message without raising exceptions.
        """
        qr_str = "signmessage m/84h/0h/0h/0/0 ascii:"
        decoder = DecodeQR()
        status = decoder.add_data(qr_str)
        assert status == DecodeQRStatus.COMPLETE
        qr_data = decoder.get_qr_data()
        assert qr_data["message"] == ""


    def test_decode_sign_message_multiple_colons_in_message(self):
        """
        Should preserve message content containing multiple colons.
        """
        msg = "Time: 12:00:00 - Status: OK: Verified"
        qr_str = f"signmessage m/84h/0h/0h/0/0 ascii:{msg}"
        decoder = DecodeQR()
        status = decoder.add_data(qr_str)
        assert status == DecodeQRStatus.COMPLETE
        qr_data = decoder.get_qr_data()
        assert qr_data["message"] == msg
