from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants



class TestSettingsQRDecoder:
    @classmethod
    def setup_class(cls):
        cls.settings = Settings.get_instance()


    def test_decode_settingsqr(self):
        """
        Assume the QR reader decodes the SettingsQR content correctly and begin this test
        with parsing the result.
        """
        settings_name = "Test SettingsQR"
        settings_qr_str = f"""settings::v1 name={ settings_name.replace(" ", "_") } persistent=D coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss,ms scripts=nat,nes,tr xpub_details=E passphrase=E camera=180 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E"""

        # First explicitly set settings that differ from the settings_qr_str
        self.settings.set_value(SettingsConstants.SETTING__COMPACT_SEEDQR, SettingsConstants.OPTION__DISABLED)
        self.settings.set_value(SettingsConstants.SETTING__DIRE_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self.settings.set_value(SettingsConstants.SETTING__COORDINATORS, [SettingsConstants.COORDINATOR__BLUE_WALLET, SettingsConstants.COORDINATOR__SPARROW])

        # Now parse the settings_qr_str
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.COMPLETE)

        parsed_name = decoder.get_settings_config_name()
        assert(parsed_name == settings_name)

        settings_data = decoder.get_settings_data()
        self.settings.update(new_settings=settings_data)

        # Now verify that the settings were updated correctly
        assert(self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) == SettingsConstants.OPTION__ENABLED)
        assert(self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__ENABLED)

        coordinators = self.settings.get_value(SettingsConstants.SETTING__COORDINATORS)
        assert(SettingsConstants.COORDINATOR__BLUE_WALLET not in coordinators)
        assert(SettingsConstants.COORDINATOR__SPARROW in coordinators)
        assert(SettingsConstants.COORDINATOR__SPECTER_DESKTOP in coordinators)
    

    def test_settingsqr_version(self):
        """ Should accept SettingsQR v1 and reject any others """
        settings_qr_str = "settings::v1 name=Foo"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.COMPLETE)

        settings_qr_str = "settings::v2 name=Foo"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.INVALID)

        # Should also fail if version omitted
        settings_qr_str = "settings name=Foo"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings is False)
        assert(status == DecodeQRStatus.INVALID)
    

    def test_settingsqr_ignores_unrecognized_setting(self):
        """ SettingsQR decoder should ignore unrecognized settings """
        settings_qr_str = "settings::v1 name=Foo favorite_food=bacon xpub_export=D"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.COMPLETE)

        settings_data = decoder.get_settings_data()
        assert("favorite_food" not in settings_data)
        assert("xpub_export" in settings_data)
    

    def test_settingsqr_fails_unrecognized_option(self):
        """ SettingsQR decoder should fail if an unrecognized option is provided """
        settings_qr_str = "settings::v2 name=Foo xpub_export=Yep"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.INVALID)


    def test_settingsqr_parses_line_break_separators(self):
        """ SettingsQR decoder should read line breaks as acceptable separators """
        settings_qr_str = "settings::v1\nname=Foo\nsigs=ss,ms\nscripts=nat,nes,tr\nxpub_export=E\n"
        decoder = DecodeQR()
        status = decoder.add_data(settings_qr_str)
        assert(decoder.is_settings)
        assert(status == DecodeQRStatus.COMPLETE)

        settings_data = decoder.get_settings_data()
        assert(len(settings_data.keys()) == 3)
        self.settings.update(new_settings=settings_data)
