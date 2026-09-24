from test_settings import SettingsQRBase
from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus




class TestSettingsQRDecoder(SettingsQRBase):
    def test_decode_settingsqr(self):
        """
        Assume the QR reader decodes the SettingsQR content correctly and begin this test
        with parsing the result.
        """
        settings_name = "Test SettingsQR"
        settings_qr_str = f"""{self.settingsqr_prefix} name={ settings_name.replace(" ", "_") } {self.settingsqr_default_attrs_str}"""

        # Now parse the settings_qr_str
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert decoder.is_settings
        assert status == DecodeQRStatus.COMPLETE

        data = decoder.get_settings_data()
        assert data == settings_qr_str


    def test_settingsqr_version(self):
        """ Should fail if the "settings" header is missing """
        settings_qr_str = "name=Foo"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert status == DecodeQRStatus.INVALID
