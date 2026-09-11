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



class PSBTVerificationError(Exception):
    """
    Base for the checks that reject a psbt outright while it is being parsed.

    A psbt that trips one of these is never shown to the user. The view layer should catch
    these exceptions and route to a warning (the severity of which and the allowed next
    steps are determined by the specific subclass error encountered).
    """
    pass


class PSBTOutputOwnershipClaimError(PSBTVerificationError):
    """
    An output claims this seed's fingerprint on a key the seed does not derive.

    This is asserting that an output belongs to this seed when it does not. We treat this
    deception as an attack.
    """
    pass


class PSBTInputOwnershipClaimError(PSBTVerificationError):
    """
    An input claims this seed's fingerprint on a key the seed does not derive.

    The same type of false claim as the output case above, but a forged input claim simply
    renders the psbt unsignable (embit re-derives the real key and will refuse to sign on
    a mismatch) so there's no point in continuing.
    """
    pass


class PSBTSurplusDerivationPathsError(PSBTVerificationError):
    """
    Raised for three similar cases:
      * single sig: output has more than one derivation path entry.
      * multisig: an output confirmed to pay this seed claims more derivation path
        entries than its committed script has keys.
      * taproot: output has more than one derivation path entry claiming to be its
        internal key (i.e. claiming no leaf hashes).

    For single sig this is clearly a structural error and is not expected to be seen in
    the real world but it's worth the sanity check.

    For multisig, this could be an attempt to deceive the user, but we do not try to
    adjudicate that.
    """
    pass


class PSBTMixedDerivationPathTypesError(PSBTVerificationError):
    """
    An input or output declares derivation paths in both the ecdsa and the taproot key
    maps (bip32_derivations and taproot_bip32_derivations).

    This is a correctness problem (not expected to be seen in the real world) or
    potentially a weak form of deception, but we do not try to adjudicate that.
    """
    pass


class PSBTOutputOwnershipContradictionError(PSBTVerificationError):
    """
    The psbt's account of who an output pays contradicts which key(s) the output
    actually commits to.

    For multisig, it's one of:
      * The output claims one of our keys, but the script the psbt supplied for it does
        not match what the output actually commits to (the output's scriptPubKey).
      * The output claims that one of our keys is part of the multisig that owns the
        output, but that key is not part of the scriptPubKey commitment.
      * Our seed owns a key that is part of the scriptPubKey commitment, but the output
        claims a different seed in our place, by fingerprint or by listed public key.

    Single sig supplies no script, so both contradictions come from the rebuild alone: the
    output claims our key but commits to another key, or it commits to our key while
    claiming a different fingerprint in our place.


    We treat any of these deceptions as an attack.
    """
    pass


class PSBTSeedCannotSignError(PSBTVerificationError):
    """
    The selected seed holds no key that could sign any input.

    This is a mismatch rather than an attack: the usual cause is the user picking the
    wrong seed. It is raised so the flow can say so up front, instead of walking the user
    through reviewing and approving a transaction that would then produce no signatures.
    """
    pass



class PSBTParser():
    """
    Reads a psbt on behalf of one seed and works out everything the signing flow shows the
    user before they approve: the wallet policy (script type, plus m-of-n and the
    cosigners for multisig), the amount coming in, what is being spent, what comes back as
    change, the fee, where the spend is going, and any OP_RETURN payload.

    Constructing it with a seed parses immediately; see parse() for what that establishes
    in what order and which psbts it turns away.

    The parse fully processes the psbt, validates what it can, then stores the organized
    results in the instance attributes (spend_amount, fee_amount, destination_addresses,
    etc.). Note that change_data and change_amount cover EVERY output coming back to this
    seed, including self-transfers to a receive address. The view layer tells the two
    apart by the branch index in the derivation path.

    A psbt is written by an untrusted coordinator. The metadata it carries about keys
    (fingerprints, derivation paths, xpubs) is a claim, not a fact. The onus is on us to
    verify by re-deriving from the signing seed. For multisig, verification depends on the
    user providing a "known good" descriptor (i.e. can be trusted) from which we can
    verify the outputs by deriving from the cosigners' xpubs.

    This class makes the difference visible in its own names:

      claimed_...   coordinator-supplied metadata (fingerprints, derivation paths, xpubs).
                    Safe to read and display; never safe to make a decision on.
      verified_...  a fact this device proved by re-deriving from the signing seed and
                    matching real key material. Only assigned by code that performed that
                    derivation.

    Invariant: no verified_ value is ever assigned from a claimed_ value without an
    intervening re-derivation from self.root or from a user-supplied "known good"
    descriptor.
    """

    # Upper bound on how many levels of derivation a single parse will cache. 1000 is
    # just slightly under a 3-of-5 multisig consolidating 200 inputs, which costs roughly
    # 650 kilobytes. A psbt that needs more levels than that still parses correctly; it
    # just stops getting cache hits once the cache is full.
    MAX_CACHED_DERIVATIONS = 1000


    def __init__(self, p: PSBT, seed: Seed, network: str = SettingsConstants.MAINNET):
        self.psbt: PSBT = p
        self.seed = seed
        self.network = network

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

        # Contains one entry per input in psbt.inputs and per output in psbt.outputs. Each
        # entry is either the derivation path the seed genuinely owns there, or it is set
        # to `None`.
        self.verified_input_derivation_paths: List[List[int] | None] = []
        self.verified_output_derivation_paths: List[List[int] | None] = []

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
        """
        Establishes, in order:

          1. _fill_missing_fingerprints: backfills all-zero fingerprints, but only where
             the seed provably derives the key.

          2. _verify_claimed_derivation_paths: each input and output that claims to be
             controlled by the seed declares a derivation path that must be verified.
             Raises an Input/Output OwnershipClaimError if a claim fails verification.

          3. _reject_if_seed_cannot_sign: raises PSBTSeedCannotSignError if none of the
             inputs can be signed by the seed. A mismatch rather than an attack, caught
             here so the flow can say so before showing a transaction.

          4. _parse_inputs: every input must resolve to the same policy otherwise a
             RuntimeError is raised. TODO: make this a PSBTVerificationError subclass so
             the view can deliberately catch this scenario and route accordingly.

             A policy is one of:
               - single-sig: the script type alone. Says nothing about keys.
               - multisig, cosigners resolved: script type, m-of-n, and the cosigner
                 xpubs that every key in the script was traced back to.
               - multisig, cosigners unresolved: script type and m-of-n only.
                 _get_policy doesn't propagate cosigner errors, so two such policies match
                 without anything having tied them to the same keys. TODO: don't let a
                 policy with no cosigner information pass as a match between inputs.
                 Outputs deliberately compare shape alone; see _policy_shape_matches.

          5. _parse_outputs: organizes the output data (amounts, destination_addresses,
             etc.) and verifies the ownership of the outputs that come back to this seed
             via:
             - single-sig: Rebuild the output script from the seed and match it against
               the committed scriptPubKey.
             - multisig: Match the seed's verified key against the pubkeys in the script
               the output commits to.
             Every change_data entry after this point will carry a derivation path that
             our seed provably owns.

        Optimization via child_key_derivation_cache:
        Parsing traverses a derivation path down to an individual address one level at a
        time, over and over, and where that traversal begins depends on the wallet.

        Single-sig traverses the full path down from our own master key, on every OUTPUT
        the PSBT claims is ours.

        Multisig instead traverses just the last two levels down from each cosigner's
        account xpub, once per cosigner, on every INPUT and on every OUTPUT carrying the
        multisig script.

        Deriving each level costs a hash and an elliptic curve operation, and these
        traversals overlap heavily: everything in one account shares the same opening
        levels, differing only in the address at the end.

        So every level derived during this parse is kept in a cache and reused. See
        _derive_with_cache.

        Note that the cache is only useful within a single parse so it is not preserved.
        """
        if self.psbt is None:
            logger.info(f"self.psbt is None!!")
            return False

        if not self.seed:
            logger.info("self.seed is None!")
            return False

        self._set_root()

        child_key_derivation_cache = {}

        # Try to fix missing fingerprints before parsing
        self._fill_missing_fingerprints(child_key_derivation_cache)

        # Work out what this seed actually owns before anything below reads the psbt's
        # claims about it.
        self._verify_claimed_derivation_paths(child_key_derivation_cache)
        self._reject_if_seed_cannot_sign()

        rt = self._parse_inputs(child_key_derivation_cache)
        if rt == False:
            return False

        rt = self._parse_outputs(child_key_derivation_cache)
        if rt == False:
            return False

        return True


    def _parse_inputs(self, child_key_derivation_cache: dict):
        """
        Totals the input amounts and determines the wallet policy. Every input must
        resolve to the same policy, otherwise a RuntimeError is raised.
        """
        self.input_amount = 0
        self.num_inputs = len(self.psbt.inputs)
        for inp in self.psbt.inputs:
            if inp.witness_utxo:
                self.input_amount += inp.witness_utxo.value
                script_pubkey = inp.witness_utxo.script_pubkey
            elif inp.non_witness_utxo:
                self.input_amount += inp.utxo.value
                script_pubkey = inp.script_pubkey

            inp_policy = PSBTParser._get_policy(inp, script_pubkey, self.psbt.xpubs, child_key_derivation_cache)
            if self.policy == None:
                self.policy = inp_policy
            else:
                if self.policy != inp_policy:
                    raise RuntimeError("Mixed inputs in the transaction")


    def _parse_outputs(self, child_key_derivation_cache: dict):
        """
        Sorts each output into change coming back to this seed, an external spend, or
        OP_RETURN data, and totals the amounts for each. Note that self-transfer/receive
        outputs are also considered "change".

        Most of the work here is determining which, if any, outputs are verifiably being
        paid to our seed.
        """

        """****************** How outputs are verified as change ************************
        Many outputs are obviously NOT change. An output is only considered possible
        change if its policy matches the inputs' policy "shape" (script type, plus m-of-n
        for multisig; see parse()); anything else is recorded as an external spend.

        The psbt will usually annotate which key(s) own a change output (see embit's
        bip32_derivations and taproot_bip32_derivations), but this is just a claim
        supplied by the coordinator. These annotations are not authoritative. But such
        claims are significant; if our checks prove that the claim is false, we consider
        the deception an attack.

        -- Proving the claim --
        The output's scriptPubKey determines where the value ACTUALLY goes. But the
        scriptPubKey only contains a hash of the spending conditions (note: taproot uses a
        tweaked key instead), so we can't simply inspect the scriptPubKey to determine if
        the output is ours.

        We must build our own version of the scriptPubKey via:
          * single sig: derive a key from our seed using the claimed derivation path.
          * multisig: hash the claimed witness_script or redeem_script.

        That leaves us holding two independent answers about the same output: which key it
        commits to (our rebuild, matched against the scriptPubKey), and which key the psbt
        says it commits to (the claim). We evaluate the output on those two facts:

                                     | claims this seed     | doesn't claim this seed
            -------------------------+----------------------+-------------------------
            commits to our key       | confirmed: is change | contradiction
            commits to another key   | contradiction        | presumed external spend

        If our two answers contradict each other, the psbt has been caught in a deception.
        We raise an exception and reject the psbt.

        (note one exception: no taproot mismatch is rejected. A script tree tweaks our
        internal key, so an honest taproot change output fails to match too, and we cannot
        yet tell that apart from an output that claims our key but pays someone else. All
        taproot mismatches pass as EXTERNAL spends and are never considered "change".)
        ******************************************************************************"""
        self.spend_amount = 0
        self.change_amount = 0
        self.change_data = []
        self.fee_amount = 0
        self.destination_addresses = []
        self.destination_amounts = []

        # Asking the PSBT for its transaction rebuilds that entire transaction from
        # scratch on every single request. The outputs are consulted a dozen times
        # over the course of the loop below, so grab them once now.
        vout = self.psbt.tx.vout

        for i, out in enumerate(self.psbt.outputs):
            out_policy = PSBTParser._get_policy(out, vout[i].script_pubkey, self.psbt.xpubs, child_key_derivation_cache)
            is_change = False

            # Is this output change? If this output's policy is superficially similar to
            # the spending wallet's policy (e.g. they're both 2-of-3 p2wsh), then it's a
            # candidate for being change.
            if PSBTParser._policy_shape_matches(out_policy, self.policy):
                # Begin the extensive work to fully verify whether this output is indeed
                # change.

                # Each of these is a claim we build our proof from, then keep for the
                # follow-up check its signature type needs:
                #   * Single sig: the derivation path the seed derives a key at.
                #   * Multisig: the witness or redeem script the coordinator supplied.
                #     Only one of these will be needed, depending on the output type.
                singlesig_derivation_path = None
                multisig_script = None

                # Compared against the output's real scriptPubKey below
                rebuilt_script_pubkey = script.Script(b"")

                # multisig, we know witness script
                if self.policy["type"] == "p2wsh":
                    multisig_script = out.witness_script
                    rebuilt_script_pubkey = script.p2wsh(multisig_script)

                elif self.policy["type"] == "p2sh-p2wsh":
                    multisig_script = out.witness_script
                    rebuilt_script_pubkey = script.p2sh(script.p2wsh(multisig_script))

                # Arbitrary p2sh; includes pre-segwit multisig (m/45')
                elif self.policy["type"] == "p2sh":
                    multisig_script = out.redeem_script
                    rebuilt_script_pubkey = script.p2sh(multisig_script)

                # single-sig; taproot handled separately below.
                elif self.policy["type"] in ("p2pkh", "p2sh-p2wpkh", "p2wpkh"):
                    # Sanity check; a single sig output shouldn't have multiple derivation
                    # paths.
                    if len(out.bip32_derivations) > 1:
                        raise PSBTSurplusDerivationPathsError("Single-key output claims more than one derivation path")

                    # Rebuild the scriptPubKey from the key at the claimed derivation path
                    if len(out.bip32_derivations.values()) == 1:
                        singlesig_derivation_path = list(out.bip32_derivations.values())[0].derivation
                        seed_public_key = PSBTParser._derive_with_cache(self.root, singlesig_derivation_path, child_key_derivation_cache).get_public_key()
                        rebuilt_script_pubkey = PSBTParser._build_singlesig_script(self.policy["type"], seed_public_key)
                    else:
                        # There's nothing for us to verify against so this output will be
                        # considered an external spend.
                        pass

                elif self.policy["type"] == "p2tr":
                    taproot_entries = list(out.taproot_bip32_derivations.values())

                    if len(taproot_entries) == 0:
                        # There's nothing for us to verify against so this output will be
                        # considered an external spend.
                        pass
                    else:
                        # A taproot output has exactly one internal key. So an output
                        # should not claim multiple derivation path entries for the
                        # internal key. However, taproot outputs can have additional
                        # entries for keys in script tree leaves. So we count just the
                        # internal key claims:
                        internal_key_claims = sum(1 for leaf_hashes, _ in taproot_entries if not leaf_hashes)
                        if internal_key_claims > 1:
                            raise PSBTSurplusDerivationPathsError("Taproot output claims more than one internal key")

                        if len(taproot_entries) == 1 and internal_key_claims == 1:
                            leaf_hashes, derivation = taproot_entries[0]
                            singlesig_derivation_path = derivation.derivation
                            seed_public_key = PSBTParser._derive_with_cache(self.root, singlesig_derivation_path, child_key_derivation_cache).get_public_key()
                            rebuilt_script_pubkey = PSBTParser._build_singlesig_script(self.policy["type"], seed_public_key)
                        else:
                            # This output has at least one derivation path entry for a key
                            # in a script tree leaf. But since we don't yet parse the
                            # script tree, we can't reconstruct the output's correct
                            # scriptPubKey. So this output will fail to match its
                            # scriptPubKey below, at which point it will be considered an
                            # external spend. This is the best we can do when we cannot
                            # verify ownership.
                            # TODO: Support keys in script tree leaves
                            pass

                else:
                    # Safety catch-all: any new script types will need explicit handling
                    # above. Note that embit reports unrecognized script types as `None`,
                    # which is also caught here.
                    raise RuntimeError(f"Unsupported policy type: {self.policy['type']}")

                verified_derivation_path = self.verified_output_derivation_paths[i]

                if rebuilt_script_pubkey.data == vout[i].script_pubkey.data:
                    # The scriptPubKey we created using our own seed matched what this
                    # output is actually committing to.

                    if singlesig_derivation_path is not None:
                        if verified_derivation_path is None:
                            # The output pays this seed but the psbt claimed a different
                            # fingerprint here. We treat this deception as an attack.
                            raise PSBTOutputOwnershipContradictionError(f"Output pays this seed at {bip32.path_to_str(singlesig_derivation_path)} but does not claim it there")

                        if verified_derivation_path != singlesig_derivation_path:
                            # Shouldn't be able to reach here: the surplus check above
                            # allows only one entry, and the ownership scan refuses a
                            # scope populating both derivation path maps, so the scan can
                            # only have verified this same path.
                            raise RuntimeError(f"Output {i} verified at a path it does not pay")

                        # We've now verified that the key we derived from our seed at the
                        # claimed path is the key this output pays. This output is
                        # provably ours.
                        is_change = True

                    elif multisig_script is not None:
                        if verified_derivation_path is None:
                            # No entry claimed this seed's fingerprint, but we already
                            # have everything we need to see if our seed is actually in
                            # the output script.
                            for derivation_path_obj in out.bip32_derivations.values():
                                # Each entry pairs a derivation path with the public key
                                # the coordinator says sits there. Both are its own
                                # claims, so we read only the path and derive the key
                                # ourselves.
                                seed_public_key = PSBTParser._derive_with_cache(self.root, derivation_path_obj.derivation, child_key_derivation_cache).get_public_key()

                                if PSBTParser._multisig_script_contains_key(multisig_script, seed_public_key):
                                    # The output pays a multisig this seed is part
                                    # of, but the psbt did not claim our key there.
                                    # We treat this deception as an attack.
                                    raise PSBTOutputOwnershipContradictionError(f"Output's committed script holds this seed's key at {bip32.path_to_str(derivation_path_obj.derivation)} but the psbt claims another fingerprint and/or public key there")

                            # We have derived a key from our seed for every derivation
                            # path this output supplies, but none of our keys match any
                            # of the keys in this output's script. So we consider this
                            # output an external spend.
                            pass

                        else:
                            # This output claimed that our seed is part of the receiving
                            # multisig, at a specific path. So now we verify that the key
                            # at that path is in the committed script.
                            seed_public_key = PSBTParser._derive_with_cache(self.root, verified_derivation_path, child_key_derivation_cache).get_public_key()
                            if not PSBTParser._multisig_script_contains_key(multisig_script, seed_public_key):
                                # The psbt said this output was coming back to our seed
                                # at that path, but the key there is not in the committed
                                # script. We treat this deception as an attack.
                                raise PSBTOutputOwnershipContradictionError(f"Output claims this seed at {bip32.path_to_str(verified_derivation_path)} but its committed script does not hold that key")

                            # The output should not describe more keys than are actually
                            # used in its script. We check for the more serious deceptions
                            # before this so they can be surfaced first.
                            if len(out.bip32_derivations) > self.policy["n"]:
                                # We don't try to decide if this is an attack or a
                                # mistake. We just abort the parse.
                                raise PSBTSurplusDerivationPathsError("Multisig output claims more derivation paths than its script has keys")

                            # We now know that our key is in the committed script; this
                            # output does pay to a multisig that our seed is part of. But
                            # note that we do not know yet if this is truly change coming
                            # back to our wallet or if it is paying out to a different
                            # multisig that happens to include our seed. Final change
                            # verification can only happen if and when the user loads
                            # their "known-good" multisig descriptor.
                            is_change = True

                elif verified_derivation_path is not None and self.policy["type"] != "p2tr":
                    # The psbt claims one of this seed's keys on this output, yet the
                    # output does NOT pay what that claim describes. We treat this
                    # deception as an attack.
                    #   * single sig: verified that this output is not paying our seed at
                    #     the claimed derivation path.
                    #   * multisig: verified that the output's claimed script is not the
                    #     one the output commits to. Note that we haven't verified our
                    #     seed's participation in the claimed script; it's irrelevant if
                    #     that script isn't committed to in the scriptPubKey.
                    # Taproot is exempt: an output paying our internal key tweaked by
                    # a script tree fails the rebuild above even when the psbt claimed
                    # the seed truthfully, and from here that is indistinguishable
                    # from an output that claims our key and pays someone else.
                    # TODO: Parse PSBT_OUT_TAP_TREE, which embit leaves unparsed in
                    # the scope's `unknown` map. Its merkle root is what separates the
                    # two: a tree that tweaks our key to the committed key makes the
                    # output verifiable change, one that does not is a contradiction to
                    # refuse here, and an output supplying no tree stays exempt, since
                    # an omitted optional field is not a contradiction.
                    raise PSBTOutputOwnershipContradictionError(f"Output claims this seed at {bip32.path_to_str(verified_derivation_path)} but its committed script contradicts that")

            if vout[i].script_pubkey.data[0] == OPCODES.OP_RETURN:
                # The data is written as: OP_RETURN + OP_PUSHDATA1 + len(payload) + payload
                self.op_return_data = vout[i].script_pubkey.data[3:]

            elif is_change:
                # Remember that "change" in this function is ANY output coming back to our
                # seed, receive addresses included. It is up to the View layer to use the
                # derivation path to determine if it should be displayed as change or
                # receive.
                addr = vout[i].script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                self.change_data.append({
                    "output_index": i,
                    "address": addr,
                    "amount": vout[i].value,
                    "verified_derivation_path": self.verified_output_derivation_paths[i],
                })
                self.change_amount += vout[i].value

            else:
                addr = vout[i].script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                self.destination_addresses.append(addr)
                self.destination_amounts.append(vout[i].value)
                self.spend_amount += vout[i].value

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
    def _get_policy(scope, scriptpubkey, xpubs, child_key_derivation_cache: dict | None):
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
        # TODO: rename this local. It shadows the embit `script` module for the rest of
        # this function, so script.p2wsh() and the other constructors are unreachable.
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
                    cosigners = PSBTParser._get_cosigners(pubkeys, scope.bip32_derivations, xpubs, child_key_derivation_cache)
                    policy.update({"m": m, "n": n, "cosigners": cosigners})
                except:
                    # TODO: stop swallowing everything here. This also catches bugs in the
                    # cosigner check itself, and cannot tell those apart from the psbt
                    # simply not supplying xpubs to check against, which is valid and must
                    # not be rejected outright.
                    policy.update({"m": m, "n": n})

        return policy


    @staticmethod
    def _policy_shape_matches(policy_a: dict, policy_b: dict) -> bool:
        """
        Compares two policies on the shape of the script they describe: the script type,
        plus m-of-n for multisig.

        A policy can also carry the cosigners resolved from the coordinator's global
        xpubs. Those are never authoritative here, and comparing them would let a psbt
        decide which of its own outputs get verified: one misannotated fingerprint makes
        that output's cosigners fail to resolve, and the output then stops matching the
        inputs' policy. Shape comes from the scriptPubKey and the supplied script, and the
        caller proves ownership rather than assuming it.
        """
        for field in ("type", "m", "n"):
            if policy_a.get(field) != policy_b.get(field):
                return False

        return True


    @staticmethod
    def _build_singlesig_script(policy_type: str, public_key: PublicKey) -> script.Script:
        """
        Builds the scriptPubKey that pays public_key under the given single-sig
        policy_type.
        """
        if policy_type == "p2pkh":
            return script.p2pkh(public_key)

        if policy_type == "p2sh-p2wpkh":
            return script.p2sh(script.p2wpkh(public_key))

        if policy_type == "p2wpkh":
            return script.p2wpkh(public_key)

        if policy_type == "p2tr":
            return script.p2tr(public_key)

        # Shouldn't be able to reach here. Just a guard against a future developer calling
        # this with invalid args.
        raise RuntimeError(f"Not a single-sig script type: {policy_type}")


    @staticmethod
    def _parse_multisig(multisig_script):
        """Takes a script and extracts m,n and pubkeys from it"""
        # OP_m <len:pubkey> ... <len:pubkey> OP_n OP_CHECKMULTISIG
        # check min size
        if len(multisig_script.data) < 37 or multisig_script.data[-1] != 0xAE:
            raise ValueError("Not a multisig script")
        m = multisig_script.data[0] - 0x50
        if m < 1 or m > 16:
            raise ValueError("Invalid multisig script")
        n = multisig_script.data[-2] - 0x50
        if n < m or n > 16:
            raise ValueError("Invalid multisig script")
        s = BytesIO(multisig_script.data)
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
        if s.read() != multisig_script.data[-2:]:
            raise ValueError("Invalid multisig script")
        return m, n, pubkeys


    @staticmethod
    def _multisig_script_contains_key(multisig_script: script.Script, public_key: PublicKey) -> bool:
        """
        Determines whether multisig_script includes the provided public_key.
        """
        m, n, pubkeys = PSBTParser._parse_multisig(multisig_script)
        return any(pubkey.sec() == public_key.sec() for pubkey in pubkeys)


    @staticmethod
    def _derive_with_cache(parent_key: bip32.HDKey, derivation_path: List[int], child_key_derivation_cache: dict | None = None) -> bip32.HDKey:
        """
        Derives the key that sits at the given derivation path below parent_key, reusing
        any levels along the way that have already been derived during this parse.

        A derivation path is traversed one level at a time, and two derivation paths that
        begin the same way share those opening levels. Each level reached is stored in the
        cache, so a later derivation running through that level picks it up instead of
        deriving it a second time.

        Entries are keyed on (id(parent_key), derivation_path_so_far), the path traversed
        down from that parent to reach this point. id() is the Python built-in for an
        object's identity; the parent belongs in the key because a multisig parse runs
        these same derivations below each cosigner's xpub in turn.

        Each entry also holds on to the parent it was derived from. id() is only the
        object's address, which Python is free to hand to a new object once the original
        is released. Keeping the parent means its address cannot be reused for as long as
        the entry it belongs to is alive.

        Keying on the parent's fingerprint was rejected: four bytes is small enough for a
        malicious coordinator to grind a deliberate collision, and the cosigner xpubs come
        from the psbt.

        The cache stops accepting new levels at MAX_CACHED_DERIVATIONS.
        """
        if child_key_derivation_cache is None:
            return parent_key.derive(derivation_path)

        derived_key = parent_key
        derivation_path_so_far = ()

        # Traverse the derivation path...
        for index in derivation_path:
            derivation_path_so_far += (index,)
            cache_key = (id(parent_key), derivation_path_so_far)
            cached_entry = child_key_derivation_cache.get(cache_key)
            if cached_entry is None:
                # First time deriving this level. Do the work to derive this level's child
                # and store it in the cache.
                already_derived = derived_key.child(index)
                if len(child_key_derivation_cache) < PSBTParser.MAX_CACHED_DERIVATIONS:
                    # Parent must also be stored to keep its id() from being reused
                    child_key_derivation_cache[cache_key] = (parent_key, already_derived)
            else:
                cached_parent, already_derived = cached_entry
            derived_key = already_derived
        return derived_key


    @staticmethod
    def _get_cosigners(pubkeys, derivations, xpubs, child_key_derivation_cache: dict | None):
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
                        derived_key = PSBTParser._derive_with_cache(
                            xpub, der.derivation[-2:], child_key_derivation_cache)
                        if derived_key.key == pubkey:
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
                    raise Exception("Signing script path spends is not yet implemented")
                fingerprints.add(hexlify(derivation_path.fingerprint).decode())
        return list(fingerprints)


    @staticmethod
    def has_matching_input_fingerprint(psbt: PSBT, seed: Seed, network: str = SettingsConstants.MAINNET):
        """
            Extracts the claimed fingerprint from each psbt input. Returns True if any
            match the provided seed.

            This is merely a routing hint to help the user select a seed that looks like
            it should be able to sign the psbt; it verifies nothing. Actual verification
            only begins once a seed has been selected and passed into a PSBTParser
            instance.
        """
        seed_fingerprint = seed.get_fingerprint(network)

        def check_fingerprint_match(public_key: PublicKey, derivation_path_obj: DerivationPath, is_taproot: bool):
            """Check fingerprint match with missing fingerprint fallback"""

            # If exact fingerprint match
            if hexlify(derivation_path_obj.fingerprint).decode() == seed_fingerprint:
                return True

            # Missing fingerprint fallback
            if derivation_path_obj.fingerprint == b"\x00\x00\x00\x00":
                root = bip32.HDKey.from_seed(seed.seed_bytes, version=NETWORKS[SettingsConstants.map_network_to_embit(network)]["xprv"])
                try:
                    return PSBTParser.seed_owns_pubkey(root, derivation_path_obj.derivation, public_key, child_key_derivation_cache=None, is_taproot=is_taproot)
                except Exception as e:
                    logger.debug("Fingerprint fallback derive failed: %s", e, exc_info=True)
            return False

        # Check all derivations in all inputs
        for input in psbt.inputs:
            # Check regular BIP32 derivations
            for public_key, derivation_path_obj in input.bip32_derivations.items():
                if check_fingerprint_match(public_key, derivation_path_obj, is_taproot=False):
                    return True

            # Check Taproot derivations
            for public_key, (leaf_hashes, derivation_path_obj) in input.taproot_bip32_derivations.items():
                if check_fingerprint_match(public_key, derivation_path_obj, is_taproot=True):
                    return True

        return False


    @staticmethod
    def seed_owns_pubkey(root: bip32.HDKey, claimed_derivation_path: List[int], public_key: PublicKey, child_key_derivation_cache: dict | None, is_taproot: bool = False) -> bool:
        """
        Returns True if the signing seed (root) really does derive public_key at
        claimed_derivation_path.

        This is the canonical ownership check. The fingerprint a psbt or a descriptor
        carries alongside a key is metadata that whoever wrote the file chose, so it can
        say anything. Ownership is established here and only here, by deriving the key
        again from the seed and comparing the actual key material.
        """
        derived_public_key = PSBTParser._derive_with_cache(root, claimed_derivation_path, child_key_derivation_cache).get_public_key()

        if is_taproot:
            # A psbt carries a taproot key as its bare 32-byte x coordinate, but embit
            # rebuilds a full key from it by just assuming even parity. The key derived
            # from the seed carries its real parity, so a naive full-key comparison
            # succeeds only when that real parity happens to be even, wrongly rejecting
            # roughly half of the keys this seed genuinely owns. Only the x coordinate is
            # real information: compare x-only.
            return derived_public_key.xonly() == public_key.xonly()

        # For ecdsa the parity byte IS part of the identity, so compare the full key.
        # This is deliberately stricter than embit, whose sign_with compares x-only even
        # for ecdsa. embit would sign a psbt whose entry names the parity-flipped twin of
        # our real key. The flipped key is still one this seed does NOT derive, and the
        # signature embit produces under it is one no standard finalizer can use. So this
        # extra strictness only rejects transactions that could never actually complete.
        return derived_public_key == public_key


    @staticmethod
    def _get_seed_derivation_path(scope: InputScope | OutputScope, root: bip32.HDKey, child_key_derivation_cache: dict) -> List[int] | None:
        """
        Scans the derivation path(s) in the provided input or output scope to determine
        which, if any, are provably derived from the signing seed (for multisig a path is
        provided per key; if the seed is part of the multisig, one of the n paths will
        match). Returns the verified derivation path (as a list of ints) or None.

        Every key in the scope that claims this seed's fingerprint is re-derived and
        checked. A false claim raises PSBT[Output|Input]OwnershipClaimError.

        A further check is then enforced: a scope carrying entries in the
        bip32_derivations AND taproot_bip32_derivations maps raises
        PSBTMixedDerivationPathTypesError. Taproot keys are exclusively x-only while
        non-taproot keys always carry their parity byte; there is no script type that can
        make use of both types of keys so it is nonsensical for a scope to provide both.

        Note that neither BIP-174 nor BIP-371 forbids the combination. And embit will
        parse and even sign such a psbt. We disallow it by opinionated choice.

        One edge case:
        * A multisig could use this seed in more than one cosigner slot, each
          at its own derivation path. The scope then carries several entries that all
          verify against this seed; we return the first but still check the rest.

        The path itself is still whatever the psbt supplied: it can be any length or
        shape, since any path that derives from the seed will pass. Whether the path is
        one the user's wallet would ever look at is a separate question, answered
        elsewhere.
        """
        seed_fingerprint = root.my_fingerprint
        verified_derivation_path = None

        def _check_claim(public_key: PublicKey, derivation_path_obj: DerivationPath, is_taproot: bool):
            nonlocal verified_derivation_path

            if derivation_path_obj.fingerprint != seed_fingerprint:
                # Claims to belong to some other key. Nothing to prove or disprove here.
                return

            if not PSBTParser.seed_owns_pubkey(root, derivation_path_obj.derivation, public_key, child_key_derivation_cache, is_taproot=is_taproot):
                error_class = (PSBTInputOwnershipClaimError if isinstance(scope, InputScope) else PSBTOutputOwnershipClaimError)
                raise error_class(f"Key at {bip32.path_to_str(derivation_path_obj.derivation)} claims this seed's fingerprint but does not derive from it")

            # Store only the first verified path
            if verified_derivation_path is None:
                verified_derivation_path = derivation_path_obj.derivation

        # Note that both loops check EVERY claim
        for public_key, derivation_path_obj in scope.bip32_derivations.items():
            _check_claim(public_key, derivation_path_obj, is_taproot=False)

        for public_key, (leaf_hashes, derivation_path_obj) in scope.taproot_bip32_derivations.items():
            # TODO: Support keys in script tree leaves
            _check_claim(public_key, derivation_path_obj, is_taproot=True)

        # The derivation path maps cannot both be populated in the same scope. Checked
        # after the loops so that a false ownership claim, the more serious finding, is
        # still the one reported.
        if scope.bip32_derivations and scope.taproot_bip32_derivations:
            raise PSBTMixedDerivationPathTypesError("Scope declares both ecdsa and taproot derivation paths")

        return verified_derivation_path


    def _verify_claimed_derivation_paths(self, child_key_derivation_cache: dict):
        """
        Verifies every derivation path entry that claims this seed's fingerprint. The
        result, stored in verified_[input|output]_derivation_paths, is either the verified
        derivation path or None (no entry claimed this seed) for each input/output scope.

        The coordinator-supplied fingerprints cannot be trusted as-is. We must derive and
        verify the ownership of each one that claims to belong to this seed.

        Outputs are verified before inputs; a false claim on an output (e.g. fake-change
        forgery) is likely an attack whereas a false claim on an input is merely
        unsignable.

        Raises PSBT[Output|Input]OwnershipClaimError on the first false claim detected.
        """
        self.verified_output_derivation_paths = [
            PSBTParser._get_seed_derivation_path(out, self.root, child_key_derivation_cache)
            for out in self.psbt.outputs
        ]

        self.verified_input_derivation_paths = [
            PSBTParser._get_seed_derivation_path(inp, self.root, child_key_derivation_cache)
            for inp in self.psbt.inputs
        ]


    def _reject_if_seed_cannot_sign(self):
        """
        Rejects the psbt when none of its inputs rely on a key derived by this seed.

        We detect it here, early, so the psbt can be rejected without sending the user
        through the full verification flow only for signing to fail at the end anyway.

        (embit's sign_with is marginally more permissive: it also signs an input whose
        script names the master key directly, with no derivation. That runs against how HD
        wallets are built. The master key is a derivation root, not a spending key, so no
        standard wallet produces such a psbt. We deliberately ignore this case.

        Similarly, it's not worth the effort to verify that each key is included in its
        input's script. A psbt that excludes a key in that way would be nonsensical but
        harmless: the excluded key cannot spend the input, so nothing of this seed's is
        at risk.)
        """
        # An input claims a key at a derivation path and _verify_claimed_derivation_paths
        # proved the seed derives it (single-sig: one such key; multisig: one per
        # cosigner, ours among them). One verified input path is enough for the psbt to
        # be signable.
        if any(path is not None for path in self.verified_input_derivation_paths):
            return

        # There's nothing for this seed to sign
        raise PSBTSeedCannotSignError()


    @staticmethod
    def is_change_branch(derivation_path: List[int]) -> bool:
        """
        Returns True if the next-to-last element of the derivation path is the change
        branch (1).
        """
        return len(derivation_path) >= 2 and derivation_path[-2] == 1


    def verify_multisig_output(self, descriptor: Descriptor, change_num: int) -> bool:
        change_data = self.get_change_data(change_num)
        i = change_data["output_index"]
        output = self.psbt.outputs[i]
        is_owner = descriptor.owns(output)
        # print(f"{self.psbt.tx.vout[i].script_pubkey.address()} | {output.value} | {is_owner}")
        return is_owner


    def _fill_missing_fingerprints(self, child_key_derivation_cache: dict):
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

            # Helper function to check and fix fingerprint
            def _get_updated_fingerprint(public_key: PublicKey, derivation_path_obj: DerivationPath, is_taproot: bool) -> DerivationPath | None:
                if derivation_path_obj.fingerprint != b"\x00\x00\x00\x00":
                    return None

                # If the signing seed really derives the psbt-provided public key at the
                # claimed derivation path, this input/output is owned by the signing seed.
                # In that case we populate the missing (zero) fingerprint with the signing
                # seed's master fingerprint so downstream parsing/signing can treat it as
                # owned by this seed.
                if PSBTParser.seed_owns_pubkey(self.root, derivation_path_obj.derivation, public_key, child_key_derivation_cache, is_taproot=is_taproot):
                    return DerivationPath(self.root.my_fingerprint, derivation_path_obj.derivation)
                return None

            # Handle regular BIP32 derivations
            for public_key, derivation_path_obj in list(scope.bip32_derivations.items()):
                new_derivation = _get_updated_fingerprint(public_key, derivation_path_obj, is_taproot=False)
                if new_derivation:
                    scope.bip32_derivations[public_key] = new_derivation
                    logger.debug(f"Filled missing fingerprint for pubkey {public_key.sec().hex()} derivation {bip32.path_to_str(derivation_path_obj.derivation)}")

            # Handle Taproot derivations
            for public_key, (leaf_hashes, derivation_path_obj) in list(scope.taproot_bip32_derivations.items()):
                new_derivation = _get_updated_fingerprint(public_key, derivation_path_obj, is_taproot=True)
                if new_derivation:
                    scope.taproot_bip32_derivations[public_key] = (leaf_hashes, new_derivation)
                    logger.debug(f"Filled missing fingerprint for pubkey {public_key.sec().hex()} derivation {bip32.path_to_str(derivation_path_obj.derivation)}")

        for inp in self.psbt.inputs:
            _fill_scope(inp)

        for out in self.psbt.outputs:
            _fill_scope(out)