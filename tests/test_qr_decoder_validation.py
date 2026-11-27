import json
import pytest
from seedsigner.models.decode_qr import (
    DecodeQR,
    DecodeQRStatus,
    QRType,
    SettingsQrDecoder,
    SpecterWalletQrDecoder,
    GenericWalletQrDecoder,
    MultiSigConfigFileQRDecoder,
)


class TestSettingsQrDecoderValidation:
    def test_settings_qr_valid_payload(self):
        """
        Valid SettingsQR payload should decode to COMPLETE.
        """
        valid_qr = "settings::v1 name=Custom_Config coord=disabled"
        decoder = SettingsQrDecoder()
        status = decoder.add(valid_qr)
        assert status == DecodeQRStatus.COMPLETE
        assert decoder.complete is True
        assert decoder.data == valid_qr

    def test_settings_qr_invalid_prefix(self):
        """
        Malformed prefix should return INVALID instead of raising an unhandled exception.
        """
        decoder = SettingsQrDecoder()
        assert decoder.add("invalid::v1 name=test") == DecodeQRStatus.INVALID
        assert decoder.add("") == DecodeQRStatus.INVALID
        assert decoder.add(None) == DecodeQRStatus.INVALID

    def test_settings_qr_missing_or_malformed_version(self):
        """
        SettingsQR data with missing version should return INVALID.
        """
        decoder = SettingsQrDecoder()
        assert decoder.add("settings::") == DecodeQRStatus.INVALID
        assert decoder.add("settings::badversion name=test") == DecodeQRStatus.INVALID


class TestSpecterWalletQrDecoderValidation:
    def test_specter_wallet_valid_complete(self):
        """
        SpecterWalletQrDecoder should correctly compute is_complete without TypeError.
        """
        valid_json = json.dumps({"descriptor": "wpkh([0f889044/84h/0h/0h]tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62/0/*)"})
        decoder = SpecterWalletQrDecoder()
        decoder.segments = [valid_json]
        decoder.complete = True

        assert decoder.validate_json() is True
        assert decoder.is_valid is True
        # Prior to the fix, calling is_complete() raised TypeError: 'bool' object is not callable
        assert decoder.is_complete() is True
        assert decoder.get_wallet_descriptor() is not None

    def test_specter_wallet_non_dict_json(self):
        """
        JSON that is not an object/dict should not crash property inspection.
        """
        for non_dict in ["123", '"plain string"', "[1, 2, 3]", "true"]:
            decoder = SpecterWalletQrDecoder()
            decoder.segments = [non_dict]
            assert decoder.validate_json() is False
            assert decoder.is_valid is False
            assert decoder.get_wallet_descriptor() is None

    def test_specter_wallet_missing_descriptor_field(self):
        """
        JSON dictionary missing 'descriptor' field should be marked invalid.
        """
        decoder = SpecterWalletQrDecoder()
        decoder.segments = [json.dumps({"name": "My Wallet", "type": "multisig"})]
        assert decoder.validate_json() is True
        assert decoder.is_valid is False
        assert decoder.get_wallet_descriptor() is None


class TestMultiSigConfigFileQRDecoderValidation:
    VALID_CONFIG = """# Coldcard multisig configuration
Name: Test Multisig
Policy: 2 of 2
Derivation: m/48'/0'/0'/2'
Format: P2WSH

0F889044: tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62
03CD0A2B: tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L
"""

    def test_multisig_config_valid(self):
        """
        Valid multisig config file should parse and complete.
        """
        decoder = MultiSigConfigFileQRDecoder()
        status = decoder.add(self.VALID_CONFIG)
        assert status == DecodeQRStatus.COMPLETE
        assert decoder.complete is True
        assert decoder.get_wallet_descriptor() is not None

    def test_multisig_config_empty_or_invalid(self):
        """
        Empty or malformed config payload should return INVALID without unhandled exception.
        """
        decoder = MultiSigConfigFileQRDecoder()
        assert decoder.add("") == DecodeQRStatus.INVALID
        assert decoder.add("not a valid config text") == DecodeQRStatus.INVALID
        assert decoder.add(None) == DecodeQRStatus.INVALID

    def test_multisig_config_missing_required_fields(self):
        """
        Missing required format or derivation lines should be rejected gracefully.
        """
        # Missing format line
        no_format = """Policy: 2 of 2
Derivation: m/48'/0'/0'/2'
0F889044: tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62
03CD0A2B: tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L
"""
        decoder = MultiSigConfigFileQRDecoder()
        assert decoder.add(no_format) == DecodeQRStatus.INVALID

        # Invalid policy (m > n)
        invalid_policy = """Policy: 3 of 2
Derivation: m/48'/0'/0'/2'
Format: P2WSH
0F889044: tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62
03CD0A2B: tpubD8HkLLgkdJkVitn1i9CN4HpFKJdom48iKm9PyiXYz5hivn1cGz6H3VeS6ncmCEgamvzQA2Qofu2YSTwWzvuaYWbJDEnvTUtj5R96vACdV6L
"""
        assert decoder.add(invalid_policy) == DecodeQRStatus.INVALID

        # Insufficient xpubs (says 2 of 2, only 1 xpub provided)
        missing_xpub = """Policy: 2 of 2
Derivation: m/48'/0'/0'/2'
Format: P2WSH
0F889044: tpubD8NkS3Gngj7L4FJRYrwojKhsx2seBhrNrXVdvqaUyvtVe1YDCVcziZVa9g3KouXz7FN5CkGBkoC16nmNu2HcG9ubTdtCbSW8DEXSMHmmu62
"""
        assert decoder.add(missing_xpub) == DecodeQRStatus.INVALID


class TestGenericWalletQrDecoderValidation:
    def test_generic_wallet_empty_or_invalid(self):
        """
        GenericWalletQrDecoder should return INVALID on empty or malformed strings.
        """
        decoder = GenericWalletQrDecoder()
        assert decoder.add("") == DecodeQRStatus.INVALID
        assert decoder.add("invalid descriptor syntax") == DecodeQRStatus.INVALID
        assert decoder.add(None) == DecodeQRStatus.INVALID
