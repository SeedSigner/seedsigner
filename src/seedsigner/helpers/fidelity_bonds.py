"""BIP 46 timelocked fidelity bond helpers."""

import json
import re
from dataclasses import dataclass

from embit import bip32, ec, script
from embit.networks import NETWORKS

from seedsigner.models.settings_definition import SettingsConstants


MIN_INDEX = 0
MAX_INDEX = 959
MIN_YEAR = 2020
MAX_YEAR = 2099
_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


@dataclass(frozen=True)
class FidelityBondPath:
    coin_type: int
    index: int


@dataclass(frozen=True)
class ParsedWitnessScript:
    locktime: int
    index: int
    pubkey: ec.PublicKey


@dataclass(frozen=True)
class FidelityBondCertificate:
    pubkey: ec.PublicKey
    pubkey_hex: str
    expiry: int


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _leap_years_before(year: int) -> int:
    year -= 1
    return year // 4 - year // 100 + year // 400


def _require_index(index: int) -> None:
    if type(index) is not int or not MIN_INDEX <= index <= MAX_INDEX:
        raise ValueError("BIP 46 index must be between 0 and 959")


def _coin_type(network: str) -> int:
    if network == SettingsConstants.MAINNET:
        return 0
    if network in (
        SettingsConstants.TESTNET,
        SettingsConstants.SIGNET,
        SettingsConstants.REGTEST,
    ):
        return 1
    raise ValueError("unsupported network")


def index_to_year_month(index: int) -> tuple[int, int]:
    """Return the BIP 46 year and month for an address index."""
    _require_index(index)
    return MIN_YEAR + index // 12, 1 + index % 12


def year_month_to_index(year: int, month: int) -> int:
    """Return the BIP 46 index for a year and month."""
    if type(year) is not int or not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError("BIP 46 year must be between 2020 and 2099")
    if type(month) is not int or not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    return (year - MIN_YEAR) * 12 + month - 1


def index_to_locktime(index: int) -> int:
    """Return the first-second UTC Unix locktime for a BIP 46 index."""
    year, month = index_to_year_month(index)
    days = (year - 1970) * 365
    days += _leap_years_before(year) - _leap_years_before(1970)
    days += sum(_MONTH_DAYS[: month - 1])
    if month > 2 and _is_leap_year(year):
        days += 1
    return days * 24 * 60 * 60


def derivation_path(index: int, network: str = SettingsConstants.MAINNET) -> str:
    """Return the canonical BIP 46 derivation path for an index and network."""
    _require_index(index)
    return f"m/84'/{_coin_type(network)}'/0'/2/{index}"


def parse_derivation_path(path: str, network: str | None = None) -> FidelityBondPath:
    """Parse an exact BIP 46 path, accepting either apostrophes or h markers."""
    if not isinstance(path, str):
        raise ValueError("derivation path must be a string")
    match = re.fullmatch(r"m/84(['h])/([01])\1/0\1/2/([0-9]+)", path)
    if match is None:
        raise ValueError("not a canonical BIP 46 derivation path")
    coin_type, index_text = int(match.group(2)), match.group(3)
    index = int(index_text)
    _require_index(index)
    if index_text != str(index):
        raise ValueError("BIP 46 index must be canonical decimal")
    if network is not None and coin_type != _coin_type(network):
        raise ValueError("derivation path does not match network")
    return FidelityBondPath(coin_type=coin_type, index=index)


def _script_num(value: int) -> bytes:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("locktime must be an unsigned 32-bit integer")
    if value == 0:
        return b""
    result = bytearray()
    while value:
        result.append(value & 0xFF)
        value >>= 8
    if result[-1] & 0x80:
        result.append(0)
    return bytes(result)


def _compressed_pubkey(pubkey: ec.PublicKey | bytes) -> tuple[ec.PublicKey, bytes]:
    if isinstance(pubkey, ec.PublicKey):
        encoded = pubkey.sec()
    elif isinstance(pubkey, bytes):
        encoded = pubkey
    else:
        raise ValueError("pubkey must be a compressed public key")
    if len(encoded) != 33 or encoded[0] not in (2, 3):
        raise ValueError("pubkey must be a compressed public key")
    try:
        parsed = ec.PublicKey.parse(encoded)
    except Exception as error:
        raise ValueError("invalid compressed public key") from error
    if parsed.sec() != encoded:
        raise ValueError("pubkey must use canonical compressed encoding")
    return parsed, encoded


def witness_script(locktime: int, pubkey: ec.PublicKey | bytes) -> script.Script:
    """Construct the canonical BIP 46 witness script."""
    _, encoded_pubkey = _compressed_pubkey(pubkey)
    encoded_locktime = _script_num(locktime)
    return script.Script(
        bytes((len(encoded_locktime),))
        + encoded_locktime
        + b"\xb1\x75\x21"
        + encoded_pubkey
        + b"\xac"
    )


def _parse_script_num(encoded: bytes) -> int:
    if not encoded:
        return 0
    value = sum(byte << (8 * position) for position, byte in enumerate(encoded))
    if encoded[-1] & 0x80:
        value &= ~(0x80 << (8 * (len(encoded) - 1)))
        value = -value
    return value


def _index_from_locktime(locktime: int) -> int:
    for index in range(MIN_INDEX, MAX_INDEX + 1):
        if index_to_locktime(index) == locktime:
            return index
    raise ValueError("locktime is not a BIP 46 monthly locktime")


def parse_witness_script(witness: script.Script | bytes) -> ParsedWitnessScript:
    """Parse only the canonical BIP 46 witness script template."""
    if isinstance(witness, script.Script):
        data = witness.data
    elif isinstance(witness, bytes):
        data = witness
    else:
        raise ValueError("witness script must be Script or bytes")
    if not data or data[0] not in (4, 5) or len(data) != data[0] + 38:
        raise ValueError("not a canonical BIP 46 witness script")
    locktime_length = data[0]
    locktime_bytes = data[1 : 1 + locktime_length]
    if data[1 + locktime_length : 3 + locktime_length] != b"\xb1\x75":
        raise ValueError("not a canonical BIP 46 witness script")
    if data[3 + locktime_length] != 0x21 or data[-1] != 0xAC:
        raise ValueError("not a canonical BIP 46 witness script")
    locktime = _parse_script_num(locktime_bytes)
    if locktime < 0 or _script_num(locktime) != locktime_bytes:
        raise ValueError("locktime is not minimally encoded")
    pubkey, _ = _compressed_pubkey(data[4 + locktime_length : -1])
    return ParsedWitnessScript(
        locktime=locktime, index=_index_from_locktime(locktime), pubkey=pubkey
    )


def derive_pubkey(
    seed_bytes: bytes, index: int, network: str = SettingsConstants.MAINNET
) -> ec.PublicKey:
    """Derive a BIP 46 compressed public key from seed bytes."""
    if not isinstance(seed_bytes, bytes):
        raise ValueError("seed_bytes must be bytes")
    embit_network = SettingsConstants.map_network_to_embit(network)
    if embit_network is None:
        raise ValueError("unsupported network")
    key = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    return key.derive(derivation_path(index, network)).to_public().key


def derive_witness_script(
    seed_bytes: bytes, index: int, network: str = SettingsConstants.MAINNET
) -> script.Script:
    """Derive a BIP 46 witness script from seed bytes."""
    return witness_script(
        index_to_locktime(index), derive_pubkey(seed_bytes, index, network)
    )


def derive_address(
    seed_bytes: bytes, index: int, network: str = SettingsConstants.MAINNET
) -> str:
    """Derive a BIP 46 P2WSH address from seed bytes."""
    embit_network = SettingsConstants.map_network_to_embit(network)
    if embit_network is None:
        raise ValueError("unsupported network")
    return script.p2wsh(derive_witness_script(seed_bytes, index, network)).address(
        NETWORKS[embit_network]
    )


def registration_payload(seed_bytes: bytes, index: int, network: str) -> str:
    """Return the canonical single-QR BIP 46 registration payload."""
    if not isinstance(seed_bytes, bytes):
        raise ValueError("seed_bytes must be bytes")
    embit_network = SettingsConstants.map_network_to_embit(network)
    network_name = SettingsConstants.map_network_to_name(network)
    if embit_network is None or network_name is None:
        raise ValueError("unsupported network")

    origin_path = f"m/84'/{_coin_type(network)}'/0'/2"
    root = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    xpub = root.derive(origin_path).to_public().to_string(
        version=NETWORKS[embit_network]["xpub"]
    )
    year, month = index_to_year_month(index)
    payload = {
        "type": "seedsigner-bip46",
        "version": 1,
        "network": network_name,
        "master_fingerprint": root.my_fingerprint.hex(),
        "origin_path": origin_path,
        "xpub": xpub,
        "locktime_date": f"{year:04d}-{month:02d}",
        "address": derive_address(seed_bytes, index, network),
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def parse_certificate(certificate: str) -> FidelityBondCertificate:
    """Parse a strict ASCII BIP 46 fidelity bond certificate message."""
    if not isinstance(certificate, str) or not certificate.isascii():
        raise ValueError("certificate must be an ASCII string")
    parts = certificate.split("|")
    if len(parts) != 3 or parts[0] != "fidelity-bond-cert":
        raise ValueError("invalid fidelity bond certificate")
    pubkey_hex, expiry_text = parts[1], parts[2]
    if re.fullmatch(r"0|[1-9][0-9]*", expiry_text) is None:
        raise ValueError("certificate expiry must be canonical decimal")
    expiry = int(expiry_text)
    if expiry > 0xFFFF:
        raise ValueError("certificate expiry must be a uint16")
    if re.fullmatch(r"0[23][0-9a-f]{64}", pubkey_hex) is None:
        raise ValueError("certificate pubkey must be lowercase compressed hex")
    pubkey, _ = _compressed_pubkey(bytes.fromhex(pubkey_hex))
    return FidelityBondCertificate(pubkey=pubkey, pubkey_hex=pubkey_hex, expiry=expiry)


def is_valid_certificate(certificate: str) -> bool:
    """Return whether a certificate has the strict BIP 46 message form."""
    try:
        parse_certificate(certificate)
    except ValueError:
        return False
    return True
