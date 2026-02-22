from unittest.mock import MagicMock, patch

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.qr_type import QRType


def test_detect_encrypted_seed_qr():
    """Strings starting with U2FsdGVkX1 are correctly detected"""
    decoder = DecodeQR()

    sample = "U2FsdGVkX1+randomstuffhere1234567890abcdef=="
    qr_type = decoder.detect_segment_type(sample)

    assert qr_type == QRType.SEED__ENCRYPTED


def test_encrypted_seed_decoder():
    """EncryptedSeedQrDecoder stores and returns data correctly"""
    from seedsigner.models.decode_qr import EncryptedSeedQrDecoder

    decoder = EncryptedSeedQrDecoder()
    encrypted_data = "U2FsdGVkX1thisisatestencryptedseeddata=="

    status = decoder.add(encrypted_data)

    assert status == DecodeQRStatus.COMPLETE
    assert decoder.complete is True
    assert decoder.get_encrypted_data() == encrypted_data


def test_decode_qr_encrypted_properties():
    """DecodeQR exposes is_encrypted_seed and get_encrypted_seed_data"""
    decode_qr = DecodeQR()
    encrypted_str = "U2FsdGVkX1testdata1234567890abcdef"

    decode_qr.add_data(encrypted_str)

    assert decode_qr.is_encrypted_seed is True
    assert decode_qr.get_encrypted_seed_data() == encrypted_str


def test_full_encrypted_seed_flow():
    """Full integration test: decrypt → validate → set pending seed → SeedFinalizeView"""
    from seedsigner.views.seed_views import EncryptedSeedDecryptView
    from seedsigner.models.settings_definition import SettingsConstants

    mock_decrypt = MagicMock(return_value="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
    mock_seed_instance = MagicMock()
    mock_seed_class = MagicMock(return_value=mock_seed_instance)
    mock_finalize_view = MagicMock()

    settings_mock = MagicMock()
    settings_mock.get_value.side_effect = lambda key: {
        SettingsConstants.SETTING__ELECTRUM_SEEDS: SettingsConstants.OPTION__DISABLED,
        SettingsConstants.SETTING__PASSPHRASE: SettingsConstants.OPTION__DISABLED,
        SettingsConstants.SETTING__WORDLIST_LANGUAGE: "en",
    }.get(key)

    with patch('seedsigner.helpers.aes_decrypt.decrypt_openssl_aes256cbc', mock_decrypt):
        with patch('seedsigner.models.seed.Seed', mock_seed_class):
            with patch('seedsigner.views.seed_views.SeedFinalizeView', mock_finalize_view):
                view = EncryptedSeedDecryptView(
                    encrypted_data="U2FsdGVkX1dummyencrypteddata",
                    passphrase="TestPass123!"
                )
                view.settings = settings_mock
                view.controller = MagicMock()
                view.controller.storage = MagicMock()

                destination = view.run()

    mock_decrypt.assert_called_once()
    mock_seed_class.assert_called_once()
    assert destination.View_cls == mock_finalize_view   # ← this is the correct attribute in SeedSigner
