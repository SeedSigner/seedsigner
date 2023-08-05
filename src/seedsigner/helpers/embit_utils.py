import embit
from embit import bip32
from embit.bip32 import HDKey
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.networks import NETWORKS

from seedsigner.models.settings_definition import SettingsConstants


"""
    Collection of generic embit-powered util methods.
"""
# TODO: PR these directly into `embit`? Or replace with new/existing methods already in `embit`?


def get_standard_derivation_path(network: str = SettingsConstants.MAINNET, wallet_type: str = SettingsConstants.SINGLE_SIG, script_type: str = SettingsConstants.NATIVE_SEGWIT) -> str:
    if network == SettingsConstants.MAINNET:
        network_path = "0'"
    elif network == SettingsConstants.TESTNET:
        network_path = "1'"
    elif network == SettingsConstants.REGTEST:
        network_path = "1'"
    else:
        raise Exception("Unexpected network")

    if wallet_type == SettingsConstants.SINGLE_SIG:
        if script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/84'/{network_path}/0'"
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/49'/{network_path}/0'"
        elif script_type == SettingsConstants.TAPROOT:
            return f"m/86'/{network_path}/0'"
        else:
            raise Exception("Unexpected script type")

    elif wallet_type == SettingsConstants.MULTISIG:
        if script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/48'/{network_path}/0'/2'"
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/48'/{network_path}/0'/1'"
        elif script_type == SettingsConstants.TAPROOT:
            raise Exception("Taproot multisig/musig not yet supported")
        else:
            raise Exception("Unexpected script type")
    else:
        raise Exception("Unexpected wallet type")    # checks that all inputs are from the same wallet



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

    if script_type == SettingsConstants.NATIVE_SEGWIT:
        return embit.script.p2wpkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NESTED_SEGWIT:
        return embit.script.p2sh(embit.script.p2wpkh(pubkey)).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.LEGACY_P2PKH:
        return embit.script.p2pkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.TAPROOT:
        return embit.script.p2tr(pubkey).address(network=NETWORKS[embit_network])



def get_multisig_address(descriptor: Descriptor, index: int = 0, is_change: bool = False, embit_network: str = "main"):
    if is_change:
        branch_index = 1
    else:
        branch_index = 0

    if descriptor.is_segwit:
        # Could be native segwit or nested segwit (descriptor.is_wrapped)
        return descriptor.derive(index, branch_index=branch_index).script_pubkey().address(network=NETWORKS[embit_network])

    elif descriptor.is_legacy:
        # TODO: Not yet implemented!
        raise Exception("Legacy P2PKH verification not yet implemented!")

    elif descriptor.is_taproot:
        # TODO: Not yet implemented!
        raise Exception("Taproot verification not yet implemented!")
