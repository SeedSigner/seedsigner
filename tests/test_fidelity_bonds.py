import pytest
from embit import bip39

from seedsigner.helpers import fidelity_bonds
from seedsigner.models.settings_definition import SettingsConstants


MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
SEED_BYTES = bip39.mnemonic_to_seed(MNEMONIC)


@pytest.mark.parametrize(
    "index, locktime, expected_script, expected_address",
    [
        (
            0,
            1577836800,
            "0400e10b5eb1752102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ac",
            "bc1qhhhf29f4nlyalyfrrpfrknxj9uwqk4qsyvkujsa7w0ulfur78xkspsqn84",
        ),
        (
            1,
            1580515200,
            "0480bf345eb1752102599f6db8b33265a44200fef0be79c927398ed0b46c6a82fa6ddaa5be2714002dac",
            "bc1qhrufsepej9sg2f8dqnsvvaulvv490u0l5w36xpkds9pjc4fnaxhq7pcm4h",
        ),
        (
            240,
            2208988800,
            "05807eaa8300b1752103ec8067418537bbb52d5d3e64e2868e67635c33cfeadeb9a46199f89ebfaab226ac",
            "bc1qul0q45njptsadnymdtv34at7karyva3v7k2vj8qc7m2702rnvddq0z20u5",
        ),
        (
            959,
            4099766400,
            "0580785df400b175210308c5751121b1ae5c973cdc7071312f6fc10ab864262f0cbd8134f056166e50f3ac",
            "bc1qsqex3czzqzrn0n6rjayvhddygj0rz8df4fj2uwk9dkzdqkt9f7zs5c493u",
        ),
    ],
)
def test_bip46_vectors(index, locktime, expected_script, expected_address):
    assert fidelity_bonds.derivation_path(index) == f"m/84'/0'/0'/2/{index}"
    assert fidelity_bonds.index_to_locktime(index) == locktime
    witness = fidelity_bonds.derive_witness_script(SEED_BYTES, index)
    assert witness.data.hex() == expected_script
    assert fidelity_bonds.derive_address(SEED_BYTES, index) == expected_address


def test_index_and_year_month_conversion():
    assert fidelity_bonds.index_to_year_month(0) == (2020, 1)
    assert fidelity_bonds.index_to_year_month(959) == (2099, 12)
    assert fidelity_bonds.year_month_to_index(2040, 1) == 240
    assert fidelity_bonds.year_month_to_index(2099, 12) == 959


@pytest.mark.parametrize("index", [-1, 960, True, "0"])
def test_invalid_index(index):
    with pytest.raises(ValueError):
        fidelity_bonds.index_to_locktime(index)


@pytest.mark.parametrize(
    "year, month", [(2019, 1), (2100, 1), (2020, 0), (2020, 13), (2020, True)]
)
def test_invalid_year_month(year, month):
    with pytest.raises(ValueError):
        fidelity_bonds.year_month_to_index(year, month)


def test_canonical_derivation_path_parsing():
    parsed = fidelity_bonds.parse_derivation_path(
        "m/84'/0'/0'/2/240", SettingsConstants.MAINNET
    )
    assert parsed == fidelity_bonds.FidelityBondPath(coin_type=0, index=240)
    assert (
        fidelity_bonds.parse_derivation_path(
            "m/84h/1h/0h/2/0", SettingsConstants.TESTNET
        ).coin_type
        == 1
    )


@pytest.mark.parametrize(
    "path",
    [
        "m/84'/0'/0'/2/00",
        "m/84'/0'/0'/1/0",
        "m/84'/0'/0'/2/960",
        "m/84'/0'/0'/2/-1",
        "m/84h/0'/0h/2/0",
        "m/84'/0'/0'/2/0/",
    ],
)
def test_invalid_derivation_paths(path):
    with pytest.raises(ValueError):
        fidelity_bonds.parse_derivation_path(path)


def test_parse_witness_script():
    witness = fidelity_bonds.derive_witness_script(SEED_BYTES, 240)
    parsed = fidelity_bonds.parse_witness_script(witness)
    assert parsed.locktime == 2208988800
    assert parsed.index == 240
    assert (
        parsed.pubkey.sec().hex()
        == "03ec8067418537bbb52d5d3e64e2868e67635c33cfeadeb9a46199f89ebfaab226"
    )


@pytest.mark.parametrize(
    "witness",
    [
        bytes.fromhex(
            "4c0400e10b5eb1752102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ac"
        ),
        bytes.fromhex(
            "0500e10b5e00b1752102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ac"
        ),
        bytes.fromhex(
            "0400e10b5eb1754102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ac"
        ),
        bytes.fromhex(
            "0400e10b5eb1752102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ad"
        ),
        bytes.fromhex(
            "0401000000b1752102a1b09f93073c63f205086440898141c0c3c6d24f69a18db608224bcf143fa011ac"
        ),
    ],
)
def test_rejects_noncanonical_witness_scripts(witness):
    with pytest.raises(ValueError):
        fidelity_bonds.parse_witness_script(witness)


def test_testnet_and_regtest_derivation():
    assert (
        fidelity_bonds.derivation_path(0, SettingsConstants.TESTNET)
        == "m/84'/1'/0'/2/0"
    )
    assert (
        fidelity_bonds.derive_pubkey(SEED_BYTES, 0, SettingsConstants.TESTNET)
        .sec()
        .hex()
        == "02d45176146a71dbe2623747898759c2dd1eaf5a6c6a7d9139ffed0a20e54bff22"
    )
    assert (
        fidelity_bonds.derive_address(SEED_BYTES, 0, SettingsConstants.TESTNET)
        == "tb1q7war3lusq3ez633rzzfkp75unfcgrqqcu80sgp0ellhrdvkzxh5srftzav"
    )
    assert (
        fidelity_bonds.derive_address(SEED_BYTES, 0, SettingsConstants.REGTEST)
        == "bcrt1q7war3lusq3ez633rzzfkp75unfcgrqqcu80sgp0ellhrdvkzxh5swspygk"
    )


def test_signet_derivation_and_registration_payload():
    assert (
        fidelity_bonds.derivation_path(0, SettingsConstants.SIGNET)
        == "m/84'/1'/0'/2/0"
    )
    assert (
        fidelity_bonds.derive_address(SEED_BYTES, 0, SettingsConstants.SIGNET)
        == "tb1q7war3lusq3ez633rzzfkp75unfcgrqqcu80sgp0ellhrdvkzxh5srftzav"
    )
    assert fidelity_bonds.parse_derivation_path(
        "m/84'/1'/0'/2/0", SettingsConstants.SIGNET
    ) == fidelity_bonds.FidelityBondPath(coin_type=1, index=0)

    assert fidelity_bonds.registration_payload(
        SEED_BYTES, 240, SettingsConstants.SIGNET
    ) == (
        '{"type":"seedsigner-bip46","version":1,"network":"signet",'
        '"master_fingerprint":"73c5da0a","origin_path":"m/84\'/1\'/0\'/2",'
        '"xpub":"tpubDFd87GgwwqSRQWvuBRuqEFnoWjJDHDnDUqu7c8DXoALBU9Kbwuom5U1KrGmYEgiCQoNtSvqdjkysKgrQZVAvU7NcVfPf1j9CRMpD1hwSpwq",'
        '"locktime_date":"2040-01",'
        '"address":"tb1qnkuzv3jckcxd9xdnvse36x2m6ylcg4aqgam2gd4tt689k44ft6eq526xlk"}'
    )


def test_mainnet_registration_payload_uses_standard_xpub():
    payload = fidelity_bonds.registration_payload(
        SEED_BYTES, 240, SettingsConstants.MAINNET
    )
    assert '"network":"mainnet"' in payload
    assert '"origin_path":"m/84\'/0\'/0\'/2"' in payload
    assert '"xpub":"xpub' in payload
    assert '"locktime_date":"2040-01"' in payload


def test_parse_certificate():
    certificate = "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|375"
    parsed = fidelity_bonds.parse_certificate(certificate)
    assert (
        parsed.pubkey_hex
        == "0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c"
    )
    assert parsed.pubkey.sec().hex() == parsed.pubkey_hex
    assert parsed.expiry == 375
    assert fidelity_bonds.is_valid_certificate(certificate)


@pytest.mark.parametrize(
    "certificate",
    [
        "fidelity-bond-cert|0330D54FD0DD420A6E5F8D3624F5F3482CAE350F79D5F0753BF5BEEF9C2D91AF3C|375",
        "fidelity-bond-cert|0430d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|375",
        "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|0375",
        "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|65536",
        "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|-1",
        "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|375|extra",
        "fidelity-bond-cert|0330d54fd0dd420a6e5f8d3624f5f3482cae350f79d5f0753bf5beef9c2d91af3c|375\u00e9",
    ],
)
def test_rejects_invalid_certificates(certificate):
    with pytest.raises(ValueError):
        fidelity_bonds.parse_certificate(certificate)
    assert not fidelity_bonds.is_valid_certificate(certificate)
