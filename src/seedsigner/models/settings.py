from seedsigner.helpers import Singleton
from .qr_type import QRType
from .encode_qr_density import EncodeQRDensity

import configparser
from embit import bip39

class Settings(Singleton):

    @classmethod
    def configure_instance(cls, config=None):
        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")

        # Instantiate the one and only instance
        settings = cls.__new__(cls)
        cls._instance = settings

        # default internal data structure for settings
        settings._data = {
            'system': {
                'debug': False,
                'default_language': "en",
                'persistent_settings': False,
                'wordlist': bip39.WORDLIST
            },
            'display': {
                'text_color': "ORANGE",
                'qr_background_color': "FFFFFF",
                'camera_rotation': 0
            },
            'wallet': {
                'network': "main",
                'software': "Specter Desktop",
                'qr_density': EncodeQRDensity.MEDIUM,
                'custom_derivation': 'm/0/0',
                'compact_seedqr_enabled': False,
            }
        }

        settings.init_complete = False

        if config is not None:
            # read settings.ini typically
            settings.__config_to_data(config)

        settings.init_complete = True

    def __config_to_data(self, config):
        # TODO: Make each get resilient to the possibility of the field being missing in
        # the `settings.ini`
        self.persistent = config.getboolean("system", "persistent_settings")
        self._data["system"]["debug"] = config.getboolean("system", "debug")
        self._data["system"]["default_language"] = config["system"]["default_language"]
        self._data["display"]["text_color"] = config["display"]["text_color"]
        self.qr_background_color = config["display"]["qr_background_color"]
        self._data["display"]["camera_rotation"] = int(config["display"]["camera_rotation"])
        self.network = config["wallet"]["network"]
        self.software = config["wallet"]["software"]
        self.qr_density = int(config["wallet"]["qr_density"])
        self.custom_derivation = config["wallet"]["custom_derivation"]

        if "compact_seedqr_enabled"in config["wallet"]:
            self.compact_seedqr_enabled = config.getboolean("wallet", "compact_seedqr_enabled")

    ### persistent settings handling

    @property
    def persistent(self):
        return self._data["system"]["persistent_settings"]

    @persistent.setter
    def persistent(self, value):
        if type(value) == bool:
            if value == False and value != self._data["system"]["persistent_settings"]:
                # persistence is changed to false, restore defaults
                self._data["system"]["persistent_settings"] = value
                self.init_complete == False
                self.restoreDefault()
                self.init_complete == True
            else:
                self._data["system"]["persistent_settings"] = value
                self.__writeConfig()
        else:
            raise Exception("Unexpected system.persistent_settings settings.ini value")

    def restoreDefault(self):
        config = configparser.ConfigParser()
        config.read("default_settings.ini")
        self.__config_to_data(config)
        self.__writeSettingsIni(config)

    def __writeSettingsIni(self, config):
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)
            configfile.close()

    def __generateConfig(self):
        config = configparser.ConfigParser()
        config['system'] = self._data['system']
        config['display'] = self._data['display']
        config['wallet'] = self._data['wallet']
        return config

    def __writeConfig(self):
        if self._data["system"]["persistent_settings"] == True and self.init_complete == True:
            config = self.__generateConfig()
            self.__writeSettingsIni(config)

    @property
    def persistent_display(self):
        if self.persistent:
            return "Yes"
        else:
            return "No"

    ### system

    @property
    def debug(self):
        return self._data["system"]["debug"]

    @property
    def language(self):
        return self._data["system"]["default_language"]
        
    @property
    def wordlist(self):
        return self._data["system"]["wordlist"]

    ### display

    @property
    def text_color(self):
        return self._data["display"]["text_color"]
    
    @property
    def qr_background_color(self):
        return self._data["display"]["qr_background_color"]
        
    @qr_background_color.setter
    def qr_background_color(self, value):
        self._data["display"]["qr_background_color"] = value
        self.__writeConfig()

    @property
    def camera_rotation(self):
        return self._data["display"]["camera_rotation"]

    @camera_rotation.setter
    def camera_rotation(self, value):
        if value in [0, 90, 180, 270]:
            self._data["display"]["camera_rotation"] = value
            self.__writeConfig()
        else:
            raise Exception("Unexpected display.camera_rotation settings.ini value")

    ### wallet

    @property
    def network(self):
        return self._data["wallet"]["network"]

    @network.setter
    def network(self, value):
        if value in ("main", "test"):
            self._data["wallet"]["network"] = value
            self.__writeConfig()
        else:
            raise Exception("Unexpected wallet.network settings.ini value")

    @property
    def software(self):
        return self._data["wallet"]["software"]

    @software.setter
    def software(self, value):
        if value in ("Specter Desktop", "Blue Wallet", "Sparrow", "Prompt"):
            self._data["wallet"]["software"] = value
            self.__writeConfig()
        else:
            raise Exception("Unexpected wallet.software settings.ini value")

    @property
    def qr_density(self):
        return self._data["wallet"]["qr_density"]

    @qr_density.setter
    def qr_density(self, value):
        if value in (EncodeQRDensity.LOW, EncodeQRDensity.MEDIUM, EncodeQRDensity.HIGH, int(EncodeQRDensity.LOW), int(EncodeQRDensity.MEDIUM), int(EncodeQRDensity.HIGH)):
            self._data["wallet"]["qr_density"] = int(value)
            self.__writeConfig()
        else:
            raise Exception("Unexpected wallet.qr_density settings.ini value")

    @property
    def qr_psbt_type(self):
        if self.software in ("Specter Desktop"):
            return QRType.PSBTSPECTER
        else:
            return QRType.PSBTUR2

    @property
    def qr_xpub_type(self):
        return Settings.getXPubType(self.software)

    @staticmethod
    def getXPubType(software):
        if software == "Specter Desktop":
            return QRType.SPECTERXPUBQR
        else:
            return QRType.XPUBQR

    @property
    def qr_density_name(self):
        if self.qr_density == EncodeQRDensity.LOW:
            return "Low"
        elif self.qr_density == EncodeQRDensity.MEDIUM:
            return "Medium"
        elif self.qr_density == EncodeQRDensity.HIGH:
            return "High"
        else:
            return "Unknown"

    @property
    def custom_derivation(self):
        return self._data["wallet"]["custom_derivation"]

    @custom_derivation.setter
    def custom_derivation(self, value):
        # TODO: parse and validate custom derivation path
        self._data["wallet"]["custom_derivation"] = value
        self.__writeConfig()

    @property
    def compact_seedqr_enabled(self):
        return self._data["wallet"]["compact_seedqr_enabled"]

    @compact_seedqr_enabled.setter
    def compact_seedqr_enabled(self, value):
        self._data["wallet"]["compact_seedqr_enabled"] = value
        self.__writeConfig()

    @staticmethod
    def calc_derivation(network, wallet_type, script_type):
        if network == "main":
            if wallet_type.lower() == "single sig":
                if script_type.lower() == "native segwit":
                    return "m/84'/0'/0'"
                elif script_type.lower() == "nested segwit":
                    return "m/49'/0'/0'"
                else:
                    raise Exception("Unexpected script type")
            elif wallet_type.lower() == "multisig":
                if script_type.lower() == "native segwit":
                    return "m/48'/0'/0'/2'"
                elif script_type.lower() == "nested segwit":
                    return "m/48'/0'/0'/1'"
                else:
                    raise Exception("Unexpected script type")
            else:
                raise Exception("Unexpected wallet type")
        elif network == "test":
            if wallet_type.lower() == "single sig":
                if script_type.lower() == "native segwit":
                    return "m/84'/1'/0'"
                elif script_type.lower() == "nested segwit":
                    return "m/49'/1'/0'"
                else:
                    raise Exception("Unexpected script type")
            elif wallet_type.lower() == "multisig":
                if script_type.lower() == "native segwit":
                    return "m/48'/1'/0'/2'"
                elif script_type.lower() == "nested segwit":
                    return "m/48'/1'/0'/1'"
                else:
                    raise Exception("Unexpected script type")
            else:
                raise Exception("Unexpected wallet type")
        else:
            raise Exception("Unexpected network type")