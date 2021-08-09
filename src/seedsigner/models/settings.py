from seedsigner.helpers import Singleton
from .encode_qr import EncodeQRDensity
from .qr_type import QRType

import configparser

class Settings(Singleton):

    @classmethod
    def configure_instance(cls, config=None):
        # Must be called before the first get_instance() call
        if cls._instance:
            raise Exception("Instance already configured")

        # Instantiate the one and only Controller instance
        settings = cls.__new__(cls)
        cls._instance = settings

        # default internal data structure for settings
        settings._data = {
            'system': {
                'debug': False,
                'default_language': "en",
                'persistent_settings': False
            },
            'display': {
                'text_color': "ORANGE",
            },
            'wallet': {
                'network': "main",
                'software': "Specter Desktop",
                'qr_density': EncodeQRDensity.MEDIUM,
                'script_policy': "PKWSH",
                'custom_derivation_enabled': False,
                'custom_derivation': 'm/0/0'
            }
        }

        settings.init_complete = False

        if config is not None:
            # read settings.ini typically
            settings.__config_to_data(config)

        settings.init_complete = True

    def __config_to_data(self, config):
        self.persistent = config.getboolean("system", "persistent_settings")
        self._data["system"]["debug"] = config.getboolean("system", "debug")
        self._data["system"]["default_language"] = config["system"]["default_language"]
        self._data["display"]["text_color"] = config["display"]["text_color"]
        self.network = config["wallet"]["network"]
        self.software = config["wallet"]["software"]
        self.qr_density = int(config["wallet"]["qr_density"])
        self.script_policy = config["wallet"]["script_policy"]
        self.custom_derivation_enabled = config.getboolean("wallet", "custom_derivation_enabled")
        self.custom_derivation = config["wallet"]["custom_derivation"]

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

    ### display

    @property
    def text_color(self):
        return self._data["display"]["text_color"]

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
    def script_policy(self):
        return self._data["wallet"]["script_policy"]

    @script_policy.setter
    def script_policy(self, value):
        if value in ("PKWSH", "PKWPKH"):
            self._data["wallet"]["script_policy"] = value
            self.__writeConfig()
        else:
            raise Exception("Unexpected wallet.script_policy settings.ini value")

    @property
    def policy_name(self):
        if self.script_policy == "PKWSH":
            return "Multi Sig"
        elif self.script_policy == "PKWPKH":
            return "Single Sig"
        else:
            raise Exception("Unexpected Wallet policy value")

    @property
    def custom_derivation(self):
        if self._data["wallet"]["custom_derivation_enabled"]:
            return self._data["wallet"]["custom_derivation"]
        else:
            return None

    @property
    def derivation(self):
        if self.script_policy == "PKWSH" and self.network == "main":
            return "m/48'/0'/0'/2'"
        elif self.script_policy == "PKWSH" and self.network == "test":
            return "m/48'/1'/0'/2'"
        elif self.script_policy == "PKWPKH" and self.network == "main":
            return "m/84'/0'/0'"
        elif self.script_policy == "PKWPKH" and self.network == "test":
            return "m/84'/1'/0'"
        else:
            raise Exception("Unsupported Derivation Path or Policy")

    @custom_derivation.setter
    def custom_derivation(self, value):
        # TODO: parse and validate custom derivation path
        self._data["wallet"]["custom_derivation"] = value

    @property
    def custom_derivation_enabled(self):
        return self._data["wallet"]["custom_derivation_enabled"]

    @custom_derivation_enabled.setter
    def custom_derivation_enabled(self, value):
        if type(value) == bool:
            self._data["wallet"]["custom_derivation_enabled"] = value
        else:
            raise Exception("Unexpected wallet.custom_derivation_enabled settings.ini value")