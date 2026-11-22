import embit

from binascii import b2a_base64
from hashlib import sha256

from embit import bip32, compact, ec
from embit.bip32 import HDKey
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.util import secp256k1


from seedsigner.models.derivation_path_validator import DerivationPathValidator
from seedsigner.models.settings_definition import SettingsConstants


"""
    Collection of generic embit-powered util methods.
"""
# TODO: PR these directly into `embit`? Or replace with new/existing methods already in `embit`?


# Each embit policy type as SeedSigner's script type and sig type settings. There is one
# Legacy script type setting, so legacy multisig (p2sh) uses LEGACY_P2PKH too.
POLICY_TYPE_SETTINGS = {
    "p2pkh":       (SettingsConstants.LEGACY_P2PKH,  SettingsConstants.SINGLE_SIG),
    "p2sh-p2wpkh": (SettingsConstants.NESTED_SEGWIT, SettingsConstants.SINGLE_SIG),
    "p2wpkh":      (SettingsConstants.NATIVE_SEGWIT, SettingsConstants.SINGLE_SIG),
    "p2tr":        (SettingsConstants.TAPROOT,       SettingsConstants.SINGLE_SIG),
    "p2sh":        (SettingsConstants.LEGACY_P2PKH,  SettingsConstants.MULTISIG),
    "p2sh-p2wsh":  (SettingsConstants.NESTED_SEGWIT, SettingsConstants.MULTISIG),
    "p2wsh":       (SettingsConstants.NATIVE_SEGWIT, SettingsConstants.MULTISIG),
}



def get_policy_type(script_type: str, sig_type: str) -> str | None:
    """
    Returns the embit policy type for a script type and sig type setting, or None if
    there isn't one (taproot multisig, for example).
    """
    for policy_type, settings in POLICY_TYPE_SETTINGS.items():
        if settings == (script_type, sig_type):
            return policy_type
    return None



# TODO: Refactor `wallet_type` to conform to our `sig_type` naming convention
def get_standard_derivation_path(network: str = SettingsConstants.MAINNET, wallet_type: str = SettingsConstants.SINGLE_SIG, script_type: str = SettingsConstants.NATIVE_SEGWIT) -> str:
    """
    Returns the standard base path for the network, wallet type, and script type, at
    account 0.

    The path comes from DerivationPathValidator's registry, so the base paths SeedSigner
    exports and the ones the validator accepts as standard are defined in one place.
    """
    if network not in (SettingsConstants.MAINNET, SettingsConstants.TESTNET, SettingsConstants.REGTEST):
        raise Exception("Unexpected network")

    if wallet_type not in (SettingsConstants.SINGLE_SIG, SettingsConstants.MULTISIG):
        raise Exception("Unexpected wallet type")

    if wallet_type == SettingsConstants.MULTISIG and script_type == SettingsConstants.TAPROOT:
        raise Exception("Taproot multisig not yet supported")

    policy_type = get_policy_type(script_type=script_type, sig_type=wallet_type)
    if policy_type is None:
        raise Exception("Unexpected script type")

    base_path = DerivationPathValidator().build_base_path(policy_type, network, account=0)
    return bip32.path_to_str(base_path).replace("h", "'")



def get_display_derivation_path(derivation_path: list[int], offending_level_index: int = 0, max_chars: int = 22) -> str:
    """
    Returns derivation_path in the ' notation shown on screen (m/84'/0'/0'/0/5),
    shortened if needed to fit one line of a warning screen's body text.

    A path longer than max_chars keeps "m", the level before the offending one, the
    offending level, and as many of the levels after it as fit. Each run of dropped levels
    shows as "…". Those kept levels are shown even if they don't fit.

    22 characters fit on one line for the paths these screens show. A path made almost
    entirely of digits can run slightly into the margins.
    """
    levels = bip32.path_to_str(derivation_path).replace("h", "'").split("/")
    if len("/".join(levels)) <= max_chars:
        return "/".join(levels)

    # levels[0] is the root "m", so the offending level is one further along
    first = max(offending_level_index, 1)
    last = offending_level_index + 1

    def join(first: int, last: int) -> str:
        shown = ["m"] + (["…"] if first > 1 else []) + levels[first:last + 1]
        if last < len(levels) - 1:
            shown.append("…")
        return "/".join(shown)

    while last + 1 < len(levels) and len(join(first, last + 1)) <= max_chars:
        last += 1
    return join(first, last)



def get_xpub(seed_bytes, derivation_path: str, embit_network: str = "main") -> HDKey:
    root = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    xprv = root.derive(derivation_path)
    xpub = xprv.to_public()
    return xpub



def get_single_sig_address(xpub: HDKey, script_type: str = SettingsConstants.NATIVE_SEGWIT, index: int = 0, is_change: bool = False, embit_network: str = "main") -> str:
    if is_change:
        pubkey = xpub.derive([1,index]).key
    else:
        pubkey = xpub.derive([0,index]).key

    if script_type == SettingsConstants.LEGACY_P2PKH:
        return embit.script.p2pkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NESTED_SEGWIT:
        return embit.script.p2sh(embit.script.p2wpkh(pubkey)).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NATIVE_SEGWIT:
        return embit.script.p2wpkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.TAPROOT:
        return embit.script.p2tr(pubkey).address(network=NETWORKS[embit_network])



def get_multisig_address(descriptor: Descriptor, index: int = 0, is_change: bool = False, embit_network: str = "main"):
    if is_change:
        branch_index = 1
    else:
        branch_index = 0

    # Can derive p2wsh, p2sh-p2wsh, and legacy (non-segwit) p2sh
    if descriptor.is_segwit or (descriptor.is_legacy and descriptor.is_basic_multisig):
        return descriptor.derive(index, branch_index=branch_index).script_pubkey().address(network=NETWORKS[embit_network])

    elif descriptor.is_taproot:
        # TODO: Not yet implemented!
        raise Exception("Taproot verification not yet implemented!")

    raise Exception(f"{descriptor.script_pubkey().script_type()} address verification not yet implemented!")



def get_multisig_policy(descriptor: Descriptor) -> tuple:
    """Extract (threshold, n) from a basic multisig descriptor."""
    if not descriptor.is_basic_multisig:
        raise ValueError(f"Expected a basic multisig descriptor, got: {descriptor.brief_policy}")
    return (str(descriptor.miniscript.args[0]), str(len(descriptor.keys)))



def get_embit_network_name(settings_name):
    """ Convert SeedSigner SettingsConstants for `network` to embit's NETWORK key """
    lookup = {
        SettingsConstants.MAINNET: "main",
        SettingsConstants.TESTNET: "test",
        SettingsConstants.REGTEST: "regtest",
    }
    return lookup.get(settings_name)



def parse_derivation_path(derivation_path: str) -> dict:
    """
    Parses a derivation path into its related SettingsConstants equivalents.

    Primarily only supports single sig derivation paths.

    May return None for fields it cannot parse.
    """
    # Support either m/44'/... or m/44h/... style
    derivation_path = derivation_path.replace("'", "h")

    sections = derivation_path.split("/")

    if sections[1] == "48h":
        # So far this helper is only meant for single sig message signing
        raise Exception("Not implemented")

    lookups = {
        "script_types": {
            "44h": SettingsConstants.LEGACY_P2PKH,
            "49h": SettingsConstants.NESTED_SEGWIT,
            "84h": SettingsConstants.NATIVE_SEGWIT,
            "86h": SettingsConstants.TAPROOT,
        },
        "networks": {
            "0h": SettingsConstants.MAINNET,
            "1h": [SettingsConstants.TESTNET, SettingsConstants.REGTEST],
        }
    }

    details = dict()
    details["script_type"] = lookups["script_types"].get(sections[1])
    if not details["script_type"]:
        details["script_type"] = SettingsConstants.CUSTOM_DERIVATION
    details["network"] = lookups["networks"].get(sections[2])

    # Check if there's a standard change path
    if sections[-2] in ["0", "1"]:
        details["is_change"] = sections[-2] == "1"
    else:
        details["is_change"] = None

    # Check if there's a standard address index
    if sections[-1].isdigit():
        details["index"] = int(sections[-1])
    else:
        details["index"] = None

    if details["is_change"] is not None and details["index"] is not None:
        # standard change and addr index; safe to truncate to the wallet level
        details["wallet_derivation_path"] = "/".join(sections[:-2])
    else:
        details["wallet_derivation_path"] = None

    details["clean_match"] = True
    for k, v in details.items():
        if v is None:
            # At least one field couldn't be parsed
            details["clean_match"] = False
            break

    return details



def sign_message(seed_bytes: bytes, derivation: str, msg: bytes, compressed: bool = True, embit_network: str = "main") -> bytes:
    """
        from: https://github.com/cryptoadvance/specter-diy/blob/b58a819ef09b2bca880a82c7e122618944355118/src/apps/signmessage/signmessage.py
    """
    """Sign message with private key"""
    msghash = sha256(
        sha256(
            b"\x18Bitcoin Signed Message:\n" + compact.to_bytes(len(msg)) + msg
        ).digest()
    ).digest()

    root = bip32.HDKey.from_seed(seed_bytes, version=NETWORKS[embit_network]["xprv"])
    prv = root.derive(derivation).key
    sig = secp256k1.ecdsa_sign_recoverable(msghash, prv._secret)
    flag = sig[64]
    sig = ec.Signature(sig[:64])
    c = 4 if compressed else 0
    flag = bytes([27 + flag + c])
    ser = flag + secp256k1.ecdsa_signature_serialize_compact(sig._sig)
    return b2a_base64(ser).strip().decode()
