import logging
from binascii import hexlify
from embit import psbt, script, ec, bip32
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.psbt import PSBT, DerivationPath, InputScope, OutputScope
from embit.ec import PublicKey
from io import BytesIO
from typing import List

from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants

logger = logging.getLogger(__name__)

class OPCODES:
    OP_RETURN = 106
    OP_PUSHDATA1 = 76



class PSBTParser():
    def __init__(self, p: PSBT, seed: Seed, network: str = SettingsConstants.MAINNET, pending_sp_address: dict = None):
        self.psbt: PSBT = p
        self.seed = seed
        self.network = network
        self.pending_sp_address = pending_sp_address

        self.policy = None
        self.spend_amount = 0
        self.change_amount = 0
        self.change_data = []
        self.fee_amount = 0
        self.input_amount = 0
        self.num_inputs = 0
        self.destination_addresses = []
        self.destination_amounts = []
        self.op_return_data: bytes = None

        # BIP-352 Silent Payments: verified SP outputs
        self.sp_outputs: list = []

        self.root = None

        if self.seed is not None:
            self.parse()


    def get_change_data(self, change_num: int) -> dict:
        if change_num < len(self.change_data):
            return self.change_data[change_num]


    @property
    def num_change_outputs(self):
        return len(self.change_data)


    @property
    def is_multisig(self):
        """
            Multisig psbts will have "m" and "n" defined in policy
        """
        return "m" in self.policy


    @property
    def num_destinations(self):
        return len(self.destination_addresses)


    def _set_root(self):
        self.root = bip32.HDKey.from_seed(self.seed.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(self.network)]["xprv"])


    def parse(self):
        if self.psbt is None:
            logger.info(f"self.psbt is None!!")
            return False

        if not self.seed:
            logger.info("self.seed is None!")
            return False

        self._set_root()

        # Try to fix missing fingerprints before parsing
        self._fill_missing_fingerprints()

        rt = self._parse_inputs()
        if rt == False:
            return False

        rt = self._parse_outputs()
        if rt == False:
            return False

        # If we have a pending SP address, verify outputs
        if self.pending_sp_address:
            self._verify_sp_outputs()

        return True


    def _parse_inputs(self):
        self.input_amount = 0
        self.num_inputs = len(self.psbt.inputs)
        for inp in self.psbt.inputs:
            if inp.witness_utxo:
                self.input_amount += inp.witness_utxo.value
                script_pubkey = inp.witness_utxo.script_pubkey
            elif inp.non_witness_utxo:
                self.input_amount += inp.utxo.value
                script_pubkey = inp.script_pubkey

            inp_policy = PSBTParser._get_policy(inp, script_pubkey, self.psbt.xpubs)
            if self.policy == None:
                self.policy = inp_policy
            else:
                if self.policy != inp_policy:
                    raise RuntimeError("Mixed inputs in the transaction")

    def _parse_outputs(self):
        self.spend_amount = 0
        self.change_amount = 0
        self.change_data = []
        self.fee_amount = 0
        self.destination_addresses = []
        self.destination_amounts = []
        for i, out in enumerate(self.psbt.outputs):
            out_policy = PSBTParser._get_policy(out, self.psbt.tx.vout[i].script_pubkey, self.psbt.xpubs)
            is_change = False

            # if policy is the same - probably change
            if out_policy == self.policy:
                # double-check that it's change
                # we already checked in get_cosigners and parse_multisig
                # that pubkeys are generated from cosigners,
                # and witness script is corresponding multisig
                # so we only need to check that scriptpubkey is generated from
                # witness script

                # empty script by default
                sc = script.Script(b"")

                # if older multisig, just use existing script
                if self.policy["type"] == "p2sh":
                    sc = script.p2sh(out.redeem_script)

                # multisig, we know witness script
                if self.policy["type"] == "p2wsh":
                    sc = script.p2wsh(out.witness_script)

                elif self.policy["type"] == "p2sh-p2wsh":
                    sc = script.p2sh(script.p2wsh(out.witness_script))
                
                # Arbitrary p2sh; includes pre-segwit multisig (m/45')
                elif self.policy["type"] == "p2sh":
                    sc = script.p2sh(out.redeem_script)

                # single-sig
                elif "pkh" in self.policy["type"]:
                    my_pubkey = None

                    # should be one or zero for single-key addresses
                    if len(out.bip32_derivations.values()) > 0:
                        der = list(out.bip32_derivations.values())[0].derivation
                        my_pubkey = self.root.derive(der)

                    if self.policy["type"] == "p2pkh" and my_pubkey is not None:
                        sc = script.p2pkh(my_pubkey)

                    elif self.policy["type"] == "p2sh-p2wpkh" and my_pubkey is not None:
                        sc = script.p2sh(script.p2wpkh(my_pubkey))

                    elif self.policy["type"] == "p2wpkh" and my_pubkey is not None:
                        sc = script.p2wpkh(my_pubkey)

                    if sc.data == self.psbt.tx.vout[i].script_pubkey.data:
                        is_change = True

                elif "p2tr" in self.policy["type"]:
                    my_pubkey = None
                    # should have one or zero derivations for single-key addresses
                    if len(out.taproot_bip32_derivations.values()) > 0:
                        # TODO: Support keys in taptree leaves
                        leaf_hashes, derivation = list(out.taproot_bip32_derivations.values())[0]
                        der = derivation.derivation
                        my_pubkey = self.root.derive(der)
                        sc = script.p2tr(my_pubkey)

                    if sc.data == self.psbt.tx.vout[i].script_pubkey.data:
                        is_change = True

                if sc.data == self.psbt.tx.vout[i].script_pubkey.data:
                    is_change = True

            if self.psbt.tx.vout[i].script_pubkey.data[0] == OPCODES.OP_RETURN:
                # The data is written as: OP_RETURN + OP_PUSHDATA1 + len(payload) + payload
                self.op_return_data = self.psbt.tx.vout[i].script_pubkey.data[3:]

            elif is_change:
                addr = self.psbt.tx.vout[i].script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                fingerprints = []
                derivation_paths = []

                # extract info from non-taproot outputs
                if len(self.psbt.outputs[i].bip32_derivations) > 0:
                    for d, derivation_path in self.psbt.outputs[i].bip32_derivations.items():
                        fingerprints.append(hexlify(derivation_path.fingerprint).decode())
                        derivation_paths.append(bip32.path_to_str(derivation_path.derivation))

                # extract info from taproot outputs
                if len(self.psbt.outputs[i].taproot_bip32_derivations) > 0:
                    for d, (leaf_hashes, derivation) in self.psbt.outputs[i].taproot_bip32_derivations.items():
                        fingerprints.append(hexlify(derivation.fingerprint).decode())
                        derivation_paths.append(bip32.path_to_str(derivation.derivation))

                self.change_data.append({
                    "output_index": i,
                    "address": addr,
                    "amount": self.psbt.tx.vout[i].value,
                    "fingerprint": fingerprints,
                    "derivation_path": derivation_paths,
                })
                self.change_amount += self.psbt.tx.vout[i].value

            else:
                addr = self.psbt.tx.vout[i].script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                self.destination_addresses.append(addr)
                self.destination_amounts.append(self.psbt.tx.vout[i].value)
                self.spend_amount += self.psbt.tx.vout[i].value

        self.fee_amount = self.psbt.fee()
        return True


    @staticmethod
    def trim(tx):
        trimmed_psbt = psbt.PSBT(tx.tx)
        for i, inp in enumerate(tx.inputs):
            if inp.final_scriptwitness:
                # Taproot sign; trim to only final_scriptwitness
                # From BIP-371 and BIP-174, once final script witness is populated
                # it contains all necessary signatures
                trimmed_psbt.inputs[i].final_scriptwitness = inp.final_scriptwitness
            else:
                trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

        return trimmed_psbt


    @staticmethod
    def sig_count(tx):
        cnt = 0
        for i, inp in enumerate(tx.inputs):
            if inp.final_scriptwitness is not None:
                # Taproot sign
                cnt += 1
            else:
                cnt += len(list(inp.partial_sigs.keys()))

        return cnt


    @staticmethod
    def _get_policy(scope, scriptpubkey, xpubs):
        """Parse scope and get policy"""
        # we don't know the policy yet, let's parse it
        script_type = scriptpubkey.script_type()
        # p2sh can be either legacy multisig, or nested segwit multisig
        # or nested segwit singlesig
        if script_type == "p2sh":
            if scope.witness_script is not None:
                script_type = "p2sh-p2wsh"
            elif (
                scope.redeem_script is not None
                and scope.redeem_script.script_type() == "p2wpkh"
            ):
                script_type = "p2sh-p2wpkh"
        policy = {"type": script_type}

        # expected multisig
        script = None
        if script_type:
            if "p2wsh" in script_type and scope.witness_script is not None:
                script = scope.witness_script

            elif "p2sh" == script_type and scope.redeem_script is not None:
                script = scope.redeem_script

            if script is not None:
                m, n, pubkeys = PSBTParser._parse_multisig(script)
            
                # check pubkeys are derived from cosigners
                try:
                    cosigners = PSBTParser._get_cosigners(pubkeys, scope.bip32_derivations, xpubs)
                    policy.update({"m": m, "n": n, "cosigners": cosigners})
                except:
                    policy.update({"m": m, "n": n})
        
        return policy


    @staticmethod
    def _parse_multisig(sc):
        """Takes a script and extracts m,n and pubkeys from it"""
        # OP_m <len:pubkey> ... <len:pubkey> OP_n OP_CHECKMULTISIG
        # check min size
        if len(sc.data) < 37 or sc.data[-1] != 0xAE:
            raise ValueError("Not a multisig script")
        m = sc.data[0] - 0x50
        if m < 1 or m > 16:
            raise ValueError("Invalid multisig script")
        n = sc.data[-2] - 0x50
        if n < m or n > 16:
            raise ValueError("Invalid multisig script")
        s = BytesIO(sc.data)
        # drop first byte
        s.read(1)
        # read pubkeys
        pubkeys = []
        for i in range(n):
            char = s.read(1)
            if char != b"\x21":
                raise ValueError("Invlid pubkey")
            pubkeys.append(ec.PublicKey.parse(s.read(33)))
        # check that nothing left
        if s.read() != sc.data[-2:]:
            raise ValueError("Invalid multisig script")
        return m, n, pubkeys


    @staticmethod
    def _get_cosigners(pubkeys, derivations, xpubs):
        """Returns xpubs used to derive pubkeys using global xpub field from psbt"""
        cosigners = []
        for i, pubkey in enumerate(pubkeys):
            if pubkey not in derivations:
                raise ValueError("Missing derivation")
            der = derivations[pubkey]
            for xpub in xpubs:
                origin_der = xpubs[xpub]
                # check fingerprint
                if origin_der.fingerprint == der.fingerprint:
                    # check derivation - last two indexes give pub from xpub
                    if origin_der.derivation == der.derivation[:-2]:
                        # check that it derives to pubkey actually
                        if xpub.derive(der.derivation[-2:]).key == pubkey:
                            # append strings so they can be sorted and compared
                            cosigners.append(xpub.to_base58())
                            break
        if len(cosigners) != len(pubkeys):
            raise RuntimeError("Can't get all cosigners")
        return sorted(cosigners)


    @staticmethod
    def get_input_fingerprints(psbt: PSBT) -> List[str]:
        """
            Exctracts the fingerprint from each input's derivation path.

            TODO: It's unclear if these derivations/fingerprints would ever be missing.
            Research on PSBT standard and known wallet coordinator implementations
            needed.
        """
        fingerprints = set()
        for input in psbt.inputs:
            for pub, derivation_path in input.bip32_derivations.items():
                fingerprints.add(hexlify(derivation_path.fingerprint).decode())

            for pub, (leaf_hashes, derivation_path) in input.taproot_bip32_derivations.items():
                # TODO: Support spends from leaves; depends on support in embit
                if len(leaf_hashes) > 0:
                    raise Exception("Signing keyspends from within a taptree not yet implemented")
                fingerprints.add(hexlify(derivation_path.fingerprint).decode())
        return list(fingerprints)


    @staticmethod
    def has_matching_input_fingerprint(psbt: PSBT, seed: Seed, network: str = SettingsConstants.MAINNET):
        """
            Extracts the fingerprint from each psbt input utxo. Returns True if any match
            the current seed.
        """
        seed_fingerprint = seed.get_fingerprint(network)
        
        def check_fingerprint_match(public_key: PublicKey, derivation_path_obj: DerivationPath):
            """Check fingerprint match with missing fingerprint fallback"""

            # If exact fingerprint match
            if hexlify(derivation_path_obj.fingerprint).decode() == seed_fingerprint:
                return True
            
            # Missing fingerprint fallback
            if derivation_path_obj.fingerprint == b"\x00\x00\x00\x00":
                root = bip32.HDKey.from_seed(seed.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])
                try:
                    derived_key = root.derive(derivation_path_obj.derivation)
                    return derived_key.key.sec() == public_key.sec() # Public keys match
                except Exception as e:
                    logger.debug("Fingerprint fallback derive failed: %s", e, exc_info=True)
            return False
        
        # Check all derivations in all inputs
        for input in psbt.inputs:
            # Check regular BIP32 derivations
            for public_key, derivation_path_obj in input.bip32_derivations.items():
                if check_fingerprint_match(public_key, derivation_path_obj):
                    return True
            
            # Check Taproot derivations
            for public_key, (leaf_hashes, derivation_path_obj) in input.taproot_bip32_derivations.items():
                if check_fingerprint_match(public_key, derivation_path_obj):
                    return True
        
        return False


    def verify_multisig_output(self, descriptor: Descriptor, change_num: int) -> bool:
        change_data = self.get_change_data(change_num)
        i = change_data["output_index"]
        output = self.psbt.outputs[i]
        is_owner = descriptor.owns(output)
        # print(f"{self.psbt.tx.vout[i].script_pubkey.address()} | {output.value} | {is_owner}")
        return is_owner


    def _fill_missing_fingerprints(self):
        """
        Fix for when fingerprint is missing (defaults to all zeros). Happens when the user
        creates a new wallet in an external coordinator but only provides the xpub
        (fingerprint and derivation path are omitted).

        Filling the missing fingerprints allows SeedSigner to correctly identify inputs /
        outputs that belong to the signing seed.

        see: https://github.com/SeedSigner/seedsigner/issues/359
        """
        if not self.root:
            return 0
        
        def _fill_scope(scope: InputScope | OutputScope):
            """Helper function to fill missing fingerprints in a scope (input/output)"""
            signing_seed_fingerprint = self.root.child(0).fingerprint
            
            # Helper function to check and fix fingerprint
            def _get_updated_fingerprint(public_key: PublicKey, derivation_path_obj: DerivationPath) -> DerivationPath | None:
                if derivation_path_obj.fingerprint != b"\x00\x00\x00\x00":
                    return None
                
                # Derive the public key from the currently loaded seed using the derivation 
                # contained in the PSBT. If the derived public key exactly matches 
                # the PSBT-provided public key, we can be confident that this input/output 
                # is owned by the signing seed. In that case we populate the missing (zero) 
                # fingerprint with the signing seed's master fingerprint so downstream 
                # parsing/signing can treat it as owned by this seed.
                derived_key = self.root.derive(derivation_path_obj.derivation)
                if derived_key.key.sec() == public_key.sec():
                    return DerivationPath(signing_seed_fingerprint, derivation_path_obj.derivation)
                return None
            
            # Handle regular BIP32 derivations
            for public_key, derivation_path_obj in list(scope.bip32_derivations.items()):
                new_derivation = _get_updated_fingerprint(public_key, derivation_path_obj)
                if new_derivation:
                    scope.bip32_derivations[public_key] = new_derivation
                    logger.debug(f"Filled missing fingerprint for pubkey {public_key.sec().hex()} derivation {bip32.path_to_str(derivation_path_obj.derivation)}")
            
            # Handle Taproot derivations  
            for public_key, (leaf_hashes, derivation_path_obj) in list(scope.taproot_bip32_derivations.items()):
                new_derivation = _get_updated_fingerprint(public_key, derivation_path_obj)
                if new_derivation:
                    scope.taproot_bip32_derivations[public_key] = (leaf_hashes, new_derivation)
                    logger.debug(f"Filled missing fingerprint for pubkey {public_key.sec().hex()} derivation {bip32.path_to_str(derivation_path_obj.derivation)}")

        for inp in self.psbt.inputs:
            _fill_scope(inp)

        for out in self.psbt.outputs:
            _fill_scope(out)


    def _verify_sp_outputs(self):
        """
        Verify that PSBT outputs match the expected Silent Payment derived address.

        Verification priority:
        1. BIP-375: If PSBT contains SP fields with DLEQ proofs, verify via DLEQ
        2. Fallback: If user scanned SP address, re-derive and verify output

        Per BIP-352, we need to:
        1. Collect eligible input private keys
        2. Compute the expected SP output pubkey
        3. Match against Taproot outputs in the PSBT
        """
        from seedsigner.helpers.silent_payments import (
            compute_sp_output_pubkey,
            is_eligible_input,
            full_to_xonly_pubkey,
            # BIP-375 functions
            has_bip375_sp_fields,
            extract_sp_info_from_output,
            verify_sp_output_with_bip375,
            # PSBTv2 detection
            get_psbt_version,
            is_psbt_v2,
        )

        seed_fingerprint = hexlify(self.root.child(0).fingerprint).decode()

        # Log PSBT version for diagnostics
        psbt_version = get_psbt_version(self.psbt)
        if psbt_version >= 2:
            logger.info(f"PSBTv{psbt_version} detected - BIP-375 fields stored in unknown dict")

        # =====================================================================
        # Priority 1: Try BIP-375 verification (PSBT contains SP fields + DLEQ)
        # =====================================================================
        if has_bip375_sp_fields(self.psbt):
            logger.info("BIP-375 SP fields detected in PSBT")
            self._verify_sp_outputs_bip375(seed_fingerprint)
            if self.sp_outputs:
                return  # BIP-375 verification succeeded

        # =====================================================================
        # Priority 2: Fallback to user-scanned SP address verification
        # =====================================================================
        if not self.pending_sp_address:
            return

        B_scan = self.pending_sp_address["B_scan"]
        B_spend = self.pending_sp_address["B_spend"]
        sp_address = self.pending_sp_address["address"]

        # Collect eligible input private keys and pubkeys
        input_privkeys = []
        input_pubkeys = []
        outpoints = []

        for i, inp in enumerate(self.psbt.inputs):
            if not is_eligible_input(inp, seed_fingerprint):
                logger.debug(f"Input {i} not eligible for SP computation")
                continue

            # Get derivation path and derive private key
            derivation = None
            is_taproot = False

            if inp.taproot_bip32_derivations:
                for pub, (leaf_hashes, der) in inp.taproot_bip32_derivations.items():
                    if hexlify(der.fingerprint).decode() == seed_fingerprint:
                        derivation = der.derivation
                        is_taproot = True
                        break
            elif inp.bip32_derivations:
                for pub, der in inp.bip32_derivations.items():
                    if hexlify(der.fingerprint).decode() == seed_fingerprint:
                        derivation = der.derivation
                        break

            if derivation is None:
                logger.debug(f"Input {i}: no matching derivation found")
                continue

            # Derive the private key
            derived_key = self.root.derive(derivation)
            privkey_bytes = derived_key.key.secret

            # Get public key
            pubkey = derived_key.key.get_public_key().sec()

            input_privkeys.append((privkey_bytes, is_taproot))
            input_pubkeys.append(pubkey)

            # Get outpoint (txid || vout)
            vin = self.psbt.tx.vin[i]
            txid = vin.txid  # already little-endian bytes
            vout = vin.vout.to_bytes(4, 'little')
            outpoints.append(txid + vout)

        if not input_privkeys:
            logger.warning("No eligible inputs found for SP computation")
            return

        # Find smallest outpoint
        smallest_outpoint = min(outpoints)

        # Compute expected SP output pubkey (k=0 for first output)
        try:
            expected_pubkey = compute_sp_output_pubkey(
                input_privkeys,
                input_pubkeys,
                B_scan,
                B_spend,
                smallest_outpoint,
                output_index=0
            )
            expected_xonly, _ = full_to_xonly_pubkey(expected_pubkey)
        except Exception as e:
            logger.error(f"Failed to compute SP output pubkey: {e}")
            return

        # Check each Taproot output for a match
        for i, vout in enumerate(self.psbt.tx.vout):
            script_pubkey = vout.script_pubkey
            if script_pubkey.script_type() != "p2tr":
                continue

            # Extract x-only pubkey from p2tr script (OP_1 <32-byte-key>)
            if len(script_pubkey.data) == 34 and script_pubkey.data[0] == 0x51:
                output_xonly = script_pubkey.data[2:]

                if output_xonly == expected_xonly:
                    logger.info(f"SP output match found at index {i} (fallback verification)")
                    self.sp_outputs.append({
                        "output_index": i,
                        "address": sp_address,
                        "amount": vout.value,
                        "expected_pubkey": expected_xonly.hex(),
                        "verification_method": "fallback",
                    })

                    # Update destination to show SP address instead of derived address
                    if i < len(self.destination_addresses):
                        # Replace the destination address with the SP address (truncated)
                        self.destination_addresses[i] = sp_address


    def _verify_sp_outputs_bip375(self, seed_fingerprint: str):
        """
        Verify Silent Payment outputs using BIP-375 embedded PSBT fields.

        This method checks for PSBT_OUT_SP_V0_INFO fields in outputs and
        verifies them using DLEQ proofs from global or per-input fields.
        """
        from seedsigner.helpers.silent_payments import (
            extract_sp_info_from_output,
            verify_sp_output_with_bip375,
            full_to_xonly_pubkey,
            encode_silent_payment_address,
        )

        # Determine network for address encoding
        network = "mainnet" if self.network == SettingsConstants.MAINNET else "testnet"

        for i, out in enumerate(self.psbt.outputs):
            # Check if this output has BIP-375 SP info
            sp_info = extract_sp_info_from_output(out)
            if not sp_info:
                continue

            B_scan, B_spend = sp_info
            logger.debug(f"Output {i} has BIP-375 SP info")

            # Try to verify using DLEQ proof
            expected_xonly = verify_sp_output_with_bip375(
                self.psbt,
                i,
                B_scan,
                B_spend,
                seed_fingerprint
            )

            if expected_xonly:
                # Verify the output matches
                vout = self.psbt.tx.vout[i]
                script_pubkey = vout.script_pubkey

                if script_pubkey.script_type() == "p2tr":
                    if len(script_pubkey.data) == 34 and script_pubkey.data[0] == 0x51:
                        output_xonly = script_pubkey.data[2:]

                        if output_xonly == expected_xonly:
                            # Encode SP address from B_scan and B_spend
                            try:
                                sp_address = encode_silent_payment_address(B_scan, B_spend, network)
                            except Exception as e:
                                logger.warning(f"Failed to encode SP address: {e}")
                                sp_address = "sp1...(BIP-375 verified)"

                            logger.info(f"BIP-375 SP output verified at index {i}")
                            self.sp_outputs.append({
                                "output_index": i,
                                "address": sp_address,
                                "amount": vout.value,
                                "expected_pubkey": expected_xonly.hex(),
                                "verification_method": "bip375",
                                "B_scan": B_scan.hex(),
                                "B_spend": B_spend.hex(),
                            })

                            # Update destination address
                            if i < len(self.destination_addresses):
                                self.destination_addresses[i] = sp_address
                        else:
                            logger.warning(f"BIP-375 output {i}: pubkey mismatch!")
                else:
                    logger.warning(f"BIP-375 output {i}: not a Taproot output")