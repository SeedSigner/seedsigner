import pytest
import subprocess
import base64

from seedsigner.helpers.aes_decrypt import decrypt_openssl_aes256cbc, DecryptionError


def _get_test_vector(mnemonic: str, passphrase: str) -> str:
    """Generate exact OpenSSL-compatible encrypted string using system openssl."""
    cmd = [
        'openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-iter', '100000',
        '-base64', '-pass', f'pass:{passphrase}'
    ]
    try:
        result = subprocess.run(cmd, input=mnemonic.encode('utf-8'), capture_output=True, check=True)
        return result.stdout.decode('utf-8').strip()
    except FileNotFoundError:
        pytest.skip("openssl command not found. Install with: brew install openssl")
    except subprocess.CalledProcessError:
        pytest.fail("Failed to generate test vector with openssl")


def test_decrypt_success():
    """Test successful decryption with 12-word BIP39 mnemonic"""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    passphrase = "TestPass123!"

    encrypted_b64 = _get_test_vector(mnemonic, passphrase)
    result = decrypt_openssl_aes256cbc(encrypted_b64, passphrase)
    assert result.strip() == mnemonic


def test_decrypt_24_word_success():
    """Test successful decryption with 24-word BIP39 mnemonic"""
    mnemonic = ("abandon " * 23 + "art").strip()
    passphrase = "MySuperSecretPassphrase2025"

    encrypted_b64 = _get_test_vector(mnemonic, passphrase)
    result = decrypt_openssl_aes256cbc(encrypted_b64, passphrase)
    assert result.strip() == mnemonic


def test_decrypt_wrong_passphrase():
    """Wrong passphrase must raise DecryptionError"""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
    passphrase = "TestPass123!"
    encrypted_b64 = _get_test_vector(mnemonic, passphrase)

    with pytest.raises(DecryptionError):
        decrypt_openssl_aes256cbc(encrypted_b64, "WrongPassphrase!!!")


def test_decrypt_corrupt_data():
    """Corrupted data raises DecryptionError"""
    with pytest.raises(DecryptionError):
        decrypt_openssl_aes256cbc("U2FsdGVkX1thisisnotvalidbase64garbage", "pass")


def test_decrypt_missing_header():
    """Missing 'Salted__' header raises DecryptionError"""
    data = base64.b64encode(b"not_salted_data_here").decode()
    with pytest.raises(DecryptionError, match="Invalid OpenSSL magic header"):
        decrypt_openssl_aes256cbc(data, "pass")


def test_decrypt_invalid_padding():
    """Invalid padding raises DecryptionError"""
    salt = b"12345678"
    bad_data = b'Salted__' + salt + b'\x00' * 48   # guaranteed bad padding
    bad_b64 = base64.b64encode(bad_data).decode()

    with pytest.raises(DecryptionError):
        decrypt_openssl_aes256cbc(bad_b64, "pass")


def test_decrypt_short_input():
    """Very short/invalid input raises DecryptionError"""
    with pytest.raises(DecryptionError):
        decrypt_openssl_aes256cbc("U2FsdGVkX1short", "pass")
