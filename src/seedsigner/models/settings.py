import json
import os

from embit import bip39
from typing import List

from .seed import SeedConstants
from .singleton import Singleton
from .qr_type import QRType
from .encode_qr_density import EncodeQRDensity



class SettingsConstants:
    COORDINATOR__BLUE_WALLET = "BlueWallet"
    COORDINATOR__SPARROW = "Sparrow"
    COORDINATOR__SPECTER_DESKTOP = "Specter Desktop"

    ALL_COORDINATORS = [
        COORDINATOR__BLUE_WALLET,
        COORDINATOR__SPARROW,
        COORDINATOR__SPECTER_DESKTOP,
    ]

    OPTION__ENABLED = "Enabled"
    OPTION__DISABLED = "Disabled"
    OPTION__PROMPT = "Prompt"

    ALL_OPTIONS = [
        OPTION__ENABLED,
        OPTION__DISABLED,
        OPTION__PROMPT,
    ]



class Settings(Singleton):
    SETTINGS_FILENAME = "settings.json"

    @classmethod
    def get_instance(cls):
        # This is the only way to access the one and only instance
        if cls._instance is None:
            # Instantiate the one and only instance
            settings = cls.__new__(cls)
            cls._instance = settings

            # default internal data structure for settings
            settings._data = {
                "system": {
                    "debug": False,
                    "default_language": "en",
                    "persistent_settings": False,
                },
                "display": {
                    "text_color": "white",
                    "background_color": "black",
                    "camera_rotation": 0,
                },
                "wallet": {
                    "network": SeedConstants.MAINNET,
                    "coordinators": SettingsConstants.ALL_COORDINATORS,
                    "qr_density": EncodeQRDensity.MEDIUM,
                    "custom_derivation": "m/"
                },
                "features": {
                    "xpub_export": SettingsConstants.OPTION__ENABLED,        # ENABLED | DISABLED
                    "sig_types": SeedConstants.ALL_SIG_TYPES,                # [single_sig, multisig]
                    "script_types": [t["type"] for t in SeedConstants.ALL_SCRIPT_TYPES],  # [script_type1, ...]
                    "passphrase": SettingsConstants.OPTION__PROMPT,          # ENABLED | DISABLED | PROMPT
                    "privacy_warnings": SettingsConstants.OPTION__ENABLED,   # ENABLED | DISABLED
                    "dire_warnings": SettingsConstants.OPTION__ENABLED,      # ENABLED | DISABLED
                }
            }

            # Read persistent settings, if it exists
            if os.path.exists(Settings.SETTINGS_FILENAME):
                with open(Settings.SETTINGS_FILENAME) as settings_file:
                    settings._data.update(json.load(settings_file))

        return cls._instance


    def __str__(self):
        return json.dumps(self._data, indent=2)
    

    def save(self):
        if self._data["system"]["persistent_settings"] == True and self.init_complete == True:
            with open(Settings.SETTINGS_FILENAME, 'w') as settings_file:
                json.dump(self._data, settings_file)


    def update(self, new_settings: dict):
        # Can't just merge the _data dict; have to replace keys they have in common
        #   (otherwise list values will be merged instead of replaced).
        for category, category_settings in new_settings.items():
            for key, value in category_settings.items():
                self._data[category].pop(key, None)
                self._data[category][key] = value


    ### persistent settings handling

    @property
    def persistent(self):
        return self._data["system"]["persistent_settings"]

    @persistent.setter
    def persistent(self, value: bool):
        if type(value) == bool:
            self._data["system"]["persistent_settings"] = value
            if value:
                self.save()
            else:
                # persistence is changed to false, remove SETTINGS_FILE
                if os.path.exists(Settings.SETTINGS_FILENAME):
                    os.remove(Settings.SETTINGS_FILENAME)
        else:
            raise Exception("Unexpected system.persistent_settings settings.json value")

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
        # TODO: Support BIP-39 wordlists in other languages
        return bip39.WORDLIST

    ### display

    @property
    def text_color(self):
        return self._data["display"]["text_color"]

    @property
    def camera_rotation(self):
        return self._data["display"]["camera_rotation"]

    @camera_rotation.setter
    def camera_rotation(self, value: int):
        if value in [0, 90, 180, 270]:
            self._data["display"]["camera_rotation"] = value
            self.save()
        else:
            raise Exception("Unexpected display.camera_rotation settings.json value")

    ### wallet

    @property
    def network(self):
        return self._data["wallet"]["network"]

    @network.setter
    def network(self, value):
        if value in [SeedConstants.MAINNET, SeedConstants.TESTNET]:
            self._data["wallet"]["network"] = value
            self.save()
        else:
            raise Exception("Unexpected wallet.network settings.json value")

    @property
    def coordinators(self):
        return self._data["wallet"]["coordinators"]

    @property
    def software(self):
        return self._data["wallet"]["software"]

    @software.setter
    def software(self, value):
        if value in SettingsConstants.ALL_COORDINATORS:
            self._data["wallet"]["software"] = value
            self.save()
        else:
            raise Exception("Unexpected wallet.software settings.json value")

    @property
    def qr_density(self):
        return self._data["wallet"]["qr_density"]

    @qr_density.setter
    def qr_density(self, value):
        if value in (EncodeQRDensity.LOW, EncodeQRDensity.MEDIUM, EncodeQRDensity.HIGH, int(EncodeQRDensity.LOW), int(EncodeQRDensity.MEDIUM), int(EncodeQRDensity.HIGH)):
            self._data["wallet"]["qr_density"] = int(value)
            self.save()
        else:
            raise Exception("Unexpected wallet.qr_density settings.json value")

    @property
    def qr_psbt_type(self):
        if self.software in [SettingsConstants.COORDINATOR__SPECTER_DESKTOP]:
            return QRType.PSBTSPECTER
        else:
            return QRType.PSBTUR2

    @property
    def qr_xpub_type(self):
        return Settings.getXPubType(self.software)

    @staticmethod
    def getXPubType(software):
        if software == SettingsConstants.COORDINATOR__SPECTER_DESKTOP:
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
        self.save()

    @staticmethod
    def calc_derivation(network, wallet_type, script_type):
        # TODO: Move this to Seed?
        if network == SeedConstants.MAINNET:
            network_path = "0'"
        elif network == SeedConstants.TESTNET:
            network_path = "1'"
        else:
            raise Exception("Unexpected network")

        if wallet_type == SeedConstants.SINGLE_SIG:
            if script_type == SeedConstants.NATIVE_SEGWIT:
                return f"m/84'/{network_path}/0'"
            elif script_type == SeedConstants.NESTED_SEGWIT:
                return f"m/49'/{network_path}/0'"
            elif script_type == SeedConstants.TAPROOT:
                return f"m/86'/{network_path}/0'"
            else:
                raise Exception("Unexpected script type")

        elif wallet_type == SeedConstants.MULTISIG:
            if script_type == SeedConstants.NATIVE_SEGWIT:
                return f"m/48'/{network_path}/0'/2'"
            elif script_type == SeedConstants.NESTED_SEGWIT:
                return f"m/48'/{network_path}/0'/1'"
            elif script_type == SeedConstants.TAPROOT:
                raise Exception("Taproot multisig/musig not yet supported")
            else:
                raise Exception("Unexpected script type")
        else:
            raise Exception("Unexpected wallet type")

    # Features
    @property
    def xpub_export(self):
        return self._data["features"].get("xpub_export")
    
    @property
    def sig_types(self) -> List[str]:
        return self._data["features"].get("sig_types")

    @property
    def script_types(self) -> List[str]:
        return self._data["features"].get("script_types")

    @property
    def passphrase(self):
        return self._data["features"].get("passphrase")

    @property
    def privacy_warnings(self):
        return self._data["features"].get("privacy_warnings")

    @property
    def dire_warnings(self):
        return self._data["features"].get("dire_warnings")
