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
    An output scope claims this seed's fingerprint on a key the seed does not derive.

    This is not a psbt that merely fails to be ours. A fingerprint is
    coordinator-supplied metadata, so this is a psbt asserting that a key belongs to this
    seed when it does not. On an output that assertion is how a fake change output is
    dressed up as the user's own, so it should be treated as an attack.
    """
    pass


class PSBTInputOwnershipClaimError(PSBTVerificationError):
    """
    An input scope claims this seed's fingerprint on a key the seed does not derive.

    The same false claim as PSBTOutputOwnershipClaimError, but on an input the threat
    picture inverts. A forged input claim has no path to losing funds: it cannot produce a
    signature (embit re-derives the real key and refuses on a mismatch), and it cannot
    alter the amounts, the fee, or how outputs are classified. The likely causes are
    instead a psbt assembled for a different wallet, a corrupted entry, or a collaborative
    spend that happens to include a key whose 4-byte fingerprint collides with ours (1 in
    2^32 chance).

    The psbt still fails, deliberately, following embit's lead: sign_with raises on this
    same condition and abandons the entire signing pass, so tolerating the entry here
    would only defer the failure to a worse spot. Changing this behavior, if desired,
    should happen in embit first. Until then the trade-off is accepted: a
    collaborative-spend counterparty could grief such a transaction into unsignability.
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

        # Indexed alongside psbt.inputs / psbt.outputs. Each entry is the derivation path
        # the seed genuinely owns in each scope or None where it owns nothing. Determined
        # in _verify_claimed_derivation_paths.
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

          1. _fill_missing_fingerprints: backfills all-zero fingerprints, but only for
             scopes the seed provably derives.

          2. _verify_claimed_derivation_paths: each input and output scope that claims to
             be controlled by the seed is verified. Raises an Input/Output
             OwnershipClaimError if a claimed scope fails verification.

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
                 policy with no cosigner information pass as a match.

          5. _parse_outputs: works out which outputs come back to this seed. For
             single-sig this proves the output script derives from the seed at the
             claimed path. TODO: reject outputs at a path the user's wallet would never
             scan.

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
                        my_pubkey = PSBTParser._derive_with_cache(self.root, der, child_key_derivation_cache)

                    if self.policy["type"] == "p2pkh" and my_pubkey is not None:
                        sc = script.p2pkh(my_pubkey)

                    elif self.policy["type"] == "p2sh-p2wpkh" and my_pubkey is not None:
                        sc = script.p2sh(script.p2wpkh(my_pubkey))

                    elif self.policy["type"] == "p2wpkh" and my_pubkey is not None:
                        sc = script.p2wpkh(my_pubkey)

                elif "p2tr" in self.policy["type"]:
                    my_pubkey = None
                    # should have one or zero derivations for single-key addresses
                    if len(out.taproot_bip32_derivations.values()) > 0:
                        # TODO: Support keys in taptree leaves
                        leaf_hashes, derivation = list(out.taproot_bip32_derivations.values())[0]
                        der = derivation.derivation
                        my_pubkey = PSBTParser._derive_with_cache(self.root, der, child_key_derivation_cache)
                        sc = script.p2tr(my_pubkey)

                if sc.data == vout[i].script_pubkey.data:
                    is_change = True

            if vout[i].script_pubkey.data[0] == OPCODES.OP_RETURN:
                # The data is written as: OP_RETURN + OP_PUSHDATA1 + len(payload) + payload
                self.op_return_data = vout[i].script_pubkey.data[3:]

            elif is_change:
                addr = vout[i].script_pubkey.address(NETWORKS[SettingsConstants.map_network_to_embit(self.network)])
                claimed_fingerprints = []
                claimed_derivation_paths = []

                # extract info from non-taproot outputs
                if len(self.psbt.outputs[i].bip32_derivations) > 0:
                    for d, derivation_path in self.psbt.outputs[i].bip32_derivations.items():
                        claimed_fingerprints.append(hexlify(derivation_path.fingerprint).decode())
                        claimed_derivation_paths.append(bip32.path_to_str(derivation_path.derivation))

                # extract info from taproot outputs
                if len(self.psbt.outputs[i].taproot_bip32_derivations) > 0:
                    for d, (leaf_hashes, derivation) in self.psbt.outputs[i].taproot_bip32_derivations.items():
                        claimed_fingerprints.append(hexlify(derivation.fingerprint).decode())
                        claimed_derivation_paths.append(bip32.path_to_str(derivation.derivation))

                self.change_data.append({
                    "output_index": i,
                    "address": addr,
                    "amount": vout[i].value,
                    "claimed_fingerprints": claimed_fingerprints,
                    "claimed_derivation_paths": claimed_derivation_paths,
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
                    # not be rejected outright. The fallback policy carries no cosigner
                    # information at all, and two of those compare equal on script type
                    # and m-of-n alone. Fix pending with the multisig verification work.
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
                    raise Exception("Signing keyspends from within a taptree not yet implemented")
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
        checked. A claim that does not hold up raises
        PSBT[Output|Input]OwnershipClaimError. This includes fingerprint collisions (two
        different keys with the same 4-byte fingerprint):
        * On the output side, a collision is considered an attack.
        * On the input side it is merely disallowed because it is unsignable by embit.

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
            # TODO: Support keys in taptree leaves
            _check_claim(public_key, derivation_path_obj, is_taproot=True)

        return verified_derivation_path


    def _verify_claimed_derivation_paths(self, child_key_derivation_cache: dict):
        """
        Verifies every claimed derivation path that names this seed's fingerprint. The
        result, stored in verified_[input|output]_derivation_paths, is either the verified
        derivation path or None (the seed was not named) for each input/output scope.

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
        # An input names a key at a derivation path and _verify_claimed_derivation_paths
        # proved the seed derives it (single-sig: one such key; multisig: one per
        # cosigner, ours among them). One verified input path is enough for the psbt to
        # be signable.
        if any(path is not None for path in self.verified_input_derivation_paths):
            return

        # There's nothing for this seed to sign
        raise PSBTSeedCannotSignError()


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