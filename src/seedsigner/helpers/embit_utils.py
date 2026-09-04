import embit

from binascii import b2a_base64
from gettext import gettext as _
from hashlib import sha256

from embit import bip32, compact, ec
from embit.bip32 import HDKey
from embit.descriptor import Descriptor
from embit.descriptor.arguments import Key, KeyHash
from embit.descriptor.miniscript import Wrapper
from embit.descriptor.taptree import TapLeaf, TapTree
from embit.networks import NETWORKS
from embit.util import secp256k1


from seedsigner.models.settings_definition import SettingsConstants


"""
    Collection of generic embit-powered util methods.
"""
# TODO: PR these directly into `embit`? Or replace with new/existing methods already in `embit`?


# TODO: Refactor `wallet_type` to conform to our `sig_type` naming convention
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
        if script_type == SettingsConstants.LEGACY_P2PKH:
            return f"m/44'/{network_path}/0'"
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/49'/{network_path}/0'"
        elif script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/84'/{network_path}/0'"
        elif script_type == SettingsConstants.TAPROOT:
            return f"m/86'/{network_path}/0'"
        else:
            raise Exception("Unexpected script type")

    elif wallet_type == SettingsConstants.MULTISIG:
        if script_type == SettingsConstants.LEGACY_P2PKH:
            return f"m/45'" #BIP-45
        elif script_type == SettingsConstants.NESTED_SEGWIT:
            return f"m/48'/{network_path}/0'/1'"
        elif script_type == SettingsConstants.NATIVE_SEGWIT:
            return f"m/48'/{network_path}/0'/2'"
        elif script_type == SettingsConstants.TAPROOT:
            raise Exception("Taproot multisig not yet supported")
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

    if script_type == SettingsConstants.LEGACY_P2PKH:
        return embit.script.p2pkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NESTED_SEGWIT:
        return embit.script.p2sh(embit.script.p2wpkh(pubkey)).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.NATIVE_SEGWIT:
        return embit.script.p2wpkh(pubkey).address(network=NETWORKS[embit_network])

    elif script_type == SettingsConstants.TAPROOT:
        return embit.script.p2tr(pubkey).address(network=NETWORKS[embit_network])



def can_derive_multisig_address(descriptor: Descriptor) -> bool:
    """Whether `get_multisig_address()` can actually derive an address for this
    descriptor: p2wsh/p2sh-p2wsh (including any wsh() Miniscript, not just basic
    multisig), and legacy basic-multisig p2sh.

    NOTE: this returns True for taproot too, because embit's `is_segwit` is True
    for taproot descriptors -- which also makes the `elif descriptor.is_taproot:
    raise` branch in `get_multisig_address()` below unreachable dead code.
    Taproot addresses do in fact derive correctly through that path (verified by
    test_get_multisig_address's taproot vector), so this is intentionally left
    as-is rather than "fixed" to reject taproot; taproot *signing* is what's
    still gated, over in PSBTParser.
    """
    return bool(descriptor.is_segwit or (descriptor.is_legacy and descriptor.is_basic_multisig))



def get_multisig_address(descriptor: Descriptor, index: int = 0, is_change: bool = False, embit_network: str = "main"):
    if is_change:
        branch_index = 1
    else:
        branch_index = 0

    # Can derive p2wsh, p2sh-p2wsh, and legacy (non-segwit) p2sh
    if can_derive_multisig_address(descriptor):
        return descriptor.derive(index, branch_index=branch_index).script_pubkey().address(network=NETWORKS[embit_network])

    elif descriptor.is_taproot:
        # Unreachable: embit's `is_segwit` is True for taproot descriptors too,
        # so `can_derive_multisig_address()` above already returns True and
        # taproot addresses derive correctly through that branch (see its
        # docstring). Left in place rather than removed -- see the working
        # plan's explicit note not to touch this without cause; it's dead code,
        # not a bug, and touching it risks a behavior nobody's depending on.
        raise Exception("Taproot verification not yet implemented!")

    raise Exception(f"{descriptor.script_pubkey().script_type()} address verification not yet implemented!")



def get_multisig_policy(descriptor: Descriptor) -> tuple:
    """Extract (threshold, n) from a basic multisig descriptor."""
    if not descriptor.is_basic_multisig:
        raise ValueError(f"Expected a basic multisig descriptor, got: {descriptor.brief_policy}")
    return (str(descriptor.miniscript.args[0]), str(len(descriptor.keys)))



def is_supported_wallet_descriptor(descriptor: Descriptor) -> bool:
    """
    Whether `descriptor` is one we know how to register, display, and (where
    Address Explorer / Verify Addr are concerned) derive addresses for.

    Deliberately narrower than "any valid wsh()/tr() Miniscript". An earlier
    version of this accepted arbitrary Miniscript and rendered it through a
    generic recursive AST-to-English summary. Reviewers correctly flagged
    that as unsafe: a raw nested boolean expression forces the user to
    mentally track parenthesization to know which conditions actually apply
    together, and that gets unreadable fast on a 240x240 screen -- exactly
    the class of footgun SeedSigner's UI otherwise goes out of its way to
    avoid. See discussion on seedsigner#306 and PR #1026.

    So Miniscript support here is template-gated, not general: only the one
    specific shape recognized by `match_liana_recovery_policy()` --
    "spendable now by a primary key, or by a recovery key after a relative
    timelock" -- gets accepted, and it is displayed through curated,
    structured fields (see `LianaRecoveryDescriptorView`/`Screen`), never as
    raw or generically-rendered policy text. Anything else -- thresh(),
    multi() inside wsh() Miniscript, additional OR branches, a different
    wrapper shape -- is rejected here exactly like it always has been,
    falling through to `NotYetImplementedView`.

    Taproot is accepted only for a plain key-path-only spend (no hidden
    script-path leaves at all -- trivially just "one key", nothing to
    misread) or for the same curated recovery shape via its single hidden
    leaf. Any other taproot script-path structure is rejected for the same
    reason as above.

    Basic multisig is unaffected and unrelated to this gate; it is not
    Miniscript and was already curated (m-of-n, cosigner fingerprints) before
    any of this.

    A bare single-key descriptor (wpkh()/pkh(), no miniscript, no taproot
    script path) is intentionally excluded -- that's a plain single-sig import,
    a separate unimplemented case (see the TODO this replaces in ScanView).
    """
    if descriptor.is_basic_multisig:
        return True
    if descriptor.is_taproot:
        # Key-path-only (no hidden leaves at all) is just a single key --
        # nothing to misread, safe to accept generically.
        if not _flatten_taptree_leaves(descriptor.taptree):
            return True
        return match_liana_recovery_policy(descriptor) is not None
    if descriptor.is_segwit and descriptor.miniscript is not None:
        return match_liana_recovery_policy(descriptor) is not None
    return False



def _describe_key(key: Key) -> str:
    # TRANSLATOR_NOTE: identifies a signing key by its 4-byte master fingerprint, e.g. "key 73C5DA0A"
    return _("key {fingerprint}").format(fingerprint=key.fingerprint.hex().upper())



def _describe_miniscript_node(node) -> str:
    """
    Recursively render a parsed Miniscript fragment (or a bare Key/KeyHash leaf)
    as plain English. Driven by each fragment's own `NAME` (embit's
    `OPERATOR_NAMES`, i.e. the exact descriptor keyword: "older", "and_v",
    "thresh", etc.) rather than a fixed set of isinstance checks, so this stays
    correct if embit adds fragments we haven't special-cased below -- those
    fall through to the raw-text fallback at the end instead of being silently
    misdescribed or dropped.
    """
    if isinstance(node, (Key, KeyHash)):
        return _describe_key(node)

    if isinstance(node, Wrapper):
        # Wrappers (a: s: c: t: d: v: j: n: l: u:) change stack/verify mechanics,
        # not *who* can spend -- describe the wrapped fragment directly.
        return _describe_miniscript_node(node.arg)

    name = getattr(node, "NAME", None)

    if name == "older":
        # TRANSLATOR_NOTE: {n} is a number of blocks (relative timelock, OP_CHECKSEQUENCEVERIFY)
        return _("after {n} blocks").format(n=node.arg.num)

    if name == "after":
        # TRANSLATOR_NOTE: {n} is a block height (absolute timelock, OP_CHECKLOCKTIMEVERIFY)
        return _("after block height {n}").format(n=node.arg.num)

    if name in ("sha256", "hash256", "ripemd160", "hash160"):
        # TRANSLATOR_NOTE: {name} is a hash function name, e.g. "sha256"
        return _("a {name} preimage").format(name=name)

    if name == "andor":
        x, y, z = node.args
        # TRANSLATOR_NOTE: describes miniscript's andor(X,Y,Z): if X then Y, else Z
        return _("if ({x}) then ({y}) else ({z})").format(
            x=_describe_miniscript_node(x),
            y=_describe_miniscript_node(y),
            z=_describe_miniscript_node(z),
        )

    if name in ("and_v", "and_b", "and_n"):
        x, y = node.args[0], node.args[1]
        # TRANSLATOR_NOTE: describes an AND condition between two spending requirements
        return _("({x}) and ({y})").format(x=_describe_miniscript_node(x), y=_describe_miniscript_node(y))

    if name in ("or_b", "or_c", "or_d", "or_i"):
        x, y = node.args[0], node.args[1]
        # TRANSLATOR_NOTE: describes an OR condition between two spending requirements
        return _("({x}) or ({y})").format(x=_describe_miniscript_node(x), y=_describe_miniscript_node(y))

    if name == "thresh":
        k = node.args[0].num
        subs = [_describe_miniscript_node(a) for a in node.args[1:]]
        # TRANSLATOR_NOTE: {k} of the following {subs} conditions must be satisfied
        return _("{k} of: [{subs}]").format(k=k, subs="; ".join(subs))

    if name in ("multi", "sortedmulti", "multi_a", "sortedmulti_a"):
        k = node.args[0].num
        keys = [_describe_key(a) for a in node.args[1:]]
        # TRANSLATOR_NOTE: a k-of-n multisig; {keys} is a list of key descriptions
        return _("{k} of {n} keys: [{keys}]").format(k=k, n=len(keys), keys=", ".join(keys))

    if name in ("pk", "pk_k", "pkh", "pk_h"):
        # arg is already a Key or KeyHash; recurse to hit the isinstance branch above
        return _describe_miniscript_node(node.arg)

    if type(node).__name__ == "JustZero":
        # TRANSLATOR_NOTE: an unspendable/always-false miniscript fragment
        return _("(unspendable)")

    if type(node).__name__ == "JustOne":
        # TRANSLATOR_NOTE: an always-true/no-condition miniscript fragment
        return _("(no condition)")

    # Unknown/future fragment: never silently drop or misdescribe it -- show
    # its raw descriptor text so an unsupported case is visibly incomplete
    # rather than confidently wrong.
    return str(node)



def _flatten_taptree_leaves(taptree: TapTree) -> list:
    """Return every TapLeaf in a (possibly nested) TapTree, in no particular order.

    A TapTree's `.tree` is None, a single TapLeaf, or a 2-tuple of TapTree
    branches (see embit.descriptor.taptree.TapTree.read_from) -- this walks
    that structure regardless of depth/shape.
    """
    if taptree is None or taptree.tree is None:
        return []
    if isinstance(taptree.tree, TapLeaf):
        return [taptree.tree]
    left, right = taptree.tree
    return _flatten_taptree_leaves(left) + _flatten_taptree_leaves(right)



class LianaRecoveryPolicy:
    """
    Fields extracted from a descriptor matching the curated Miniscript shape
    this build supports. See `match_liana_recovery_policy()`.

    Both spending paths are represented uniformly as a threshold over a list
    of keys, so a single key is simply 1-of-1. Callers that want to know
    whether a path is single-key should test `len(keys) == 1` rather than
    branching on a separate flag.
    """
    __slots__ = (
        "primary_threshold", "primary_keys",
        "recovery_threshold", "recovery_keys",
        "timelock_blocks",
    )

    def __init__(self, primary_threshold: int, primary_keys: list,
                 recovery_threshold: int, recovery_keys: list,
                 timelock_blocks: int):
        self.primary_threshold = primary_threshold
        self.primary_keys = primary_keys        # list of Key
        self.recovery_threshold = recovery_threshold
        self.recovery_keys = recovery_keys      # list of Key / KeyHash
        self.timelock_blocks = timelock_blocks


    @property
    def primary_fingerprints(self) -> list:
        return [k.fingerprint.hex() for k in self.primary_keys]


    @property
    def recovery_fingerprints(self) -> list:
        return [k.fingerprint.hex() for k in self.recovery_keys]



def _unwrap(node):
    """Strip Miniscript wrapper layers (v:, s:, a:, ...) down to the fragment
    they wrap. Wrappers change stack/verify mechanics, not the underlying
    spending condition, so template matching should see through them."""
    while isinstance(node, Wrapper):
        node = node.arg
    return node



# Display-capacity limit for the curated policy screen, deliberately enforced
# at match time so a policy this device cannot show in full is refused rather
# than shown with half of it invisible.
#
# LianaRecoveryWalletScreen renders fingerprints two per line. Measured against
# that screen at 240x240: 3 primary lines + 1 recovery line ends at 178px
# against a button top of 200px, while one more line reaches 199-201px -- either
# already clipped, or within a single pixel of it, leaving nothing for a longer
# translated label. So four lines total across both paths is the honest ceiling.
#
# In practice this is not a real constraint on Liana wallets: it permits up to a
# 5-key primary path alongside a 2-key recovery path (or 4 and 4), well beyond
# the 2-of-3 and 3-of-5 setups that dominate actual use.
MAX_POLICY_FINGERPRINT_LINES = 4
_FINGERPRINTS_PER_LINE = 2



def _flatten_and_v_keys(node):
    """
    Flatten a chain of `and_v` whose leaves are all plain keys into that list
    of keys, or return None if any leaf is something else.

    An n-of-n path compiles to nested and_v rather than multi(n,...) because
    chaining is cheaper in script bytes, so
    `and_v(v:and_v(v:pk(A),pk(B)),pk(C))` is how "all three of A, B and C must
    sign" actually arrives. Confirmed against a real Liana 3-of-3 export.

    Only and_v nodes and key leaves are accepted. A timelock, hash preimage or
    any other condition inside the chain means this is not a pure key quorum,
    and the caller must not describe it as one.
    """
    node = _unwrap(node)
    name = getattr(node, "NAME", None)

    if name in ("pk", "pkh"):
        return [node.arg]

    if name == "and_v":
        keys = []
        for arg in node.args:
            sub = _flatten_and_v_keys(arg)
            if sub is None:
                return None
            keys.extend(sub)
        return keys

    return None



def _match_key_group(node):
    """
    Match a spending path that is "k of these n keys", returning
    (threshold, [keys]) or None.

    Accepts the shapes Liana emits, verified against descriptor vectors in
    Liana's own test suite (liana-gui/src/app/state/{receive,psbt}.rs) plus a
    real 3-of-3 export from the GUI:

      pk(K) / pkh(K)                       -> (1, [K])
      multi(k, A, B, ...)                  -> (k, [A, B, ...])
      thresh(k, pkh(A), a:pkh(B), ...)     -> (k, [A, B, ...])
      and_v(v:and_v(v:pk(A),pk(B)),pk(C))  -> (3, [A, B, C])   (n-of-n)

    Liana uses `multi()` for a multi-key primary path but `thresh()` with
    `a:` wrappers for a multi-key recovery path (the recovery branch sits
    under and_v and needs different miniscript type properties), so both have
    to be handled rather than assuming one form. An n-of-n path is different
    again: it compiles to a nested and_v chain, since that is cheaper than
    multi(n,...) when every key is required.

    Returns None for anything else -- including `thresh()` whose arguments are
    not all plain single keys, since a nested condition inside one leg is
    exactly the kind of structure this curated display cannot represent
    honestly.
    """
    node = _unwrap(node)
    name = getattr(node, "NAME", None)

    if name in ("pk", "pkh"):
        return (1, [node.arg])

    if name in ("multi", "sortedmulti"):
        return (node.args[0].num, list(node.args[1:]))

    if name == "thresh":
        keys = []
        for leg in node.args[1:]:
            leg = _unwrap(leg)
            if getattr(leg, "NAME", None) not in ("pk", "pkh"):
                return None
            keys.append(leg.arg)
        return (node.args[0].num, keys)

    if name == "and_v":
        # n-of-n: every key in the chain is required, so threshold == count.
        keys = _flatten_and_v_keys(node)
        if keys is None or len(keys) < 2:
            return None
        return (len(keys), keys)

    return None



def _match_timelocked_branch(node):
    """
    Match `and_v(v:<key group>, older(N))` -- a spending path gated behind a
    relative, block-based timelock. Returns ((threshold, keys), blocks), or
    None if this isn't that shape.

    The timelock is located by inspecting both arguments rather than assuming
    which side it sits on, and the other argument must be a pure key group.
    That last requirement is what rejects a multi-tier recovery policy: in
    `or_i(and_v(v:pkh(A),older(N)), and_v(v:pkh(B),older(M)))` each branch
    looks timelocked, but treating one as the "primary" path would require
    describing a timelocked branch as spendable now, so no match is returned.
    """
    node = _unwrap(node)
    if getattr(node, "NAME", None) != "and_v" or len(node.args) != 2:
        return None

    for key_side, lock_side in ((node.args[0], node.args[1]),
                                (node.args[1], node.args[0])):
        lock = _unwrap(lock_side)
        if getattr(lock, "NAME", None) != "older":
            continue

        raw = lock.arg.num
        if raw & 0x00400000:
            # BIP68 type-flag bit set: time-based (512-second units), not blocks.
            return None

        group = _match_key_group(key_side)
        if group is None:
            return None

        return (group, raw & 0x0000FFFF)

    return None



def match_liana_recovery_policy(descriptor: Descriptor):
    """
    Recognizes one curated Miniscript shape: spendable now by a key or
    key-quorum, or by a recovery key or key-quorum after a relative
    (block-based) timelock. This is Liana's inheritance wallet policy, and the
    only Miniscript shape this build displays with curated fields rather than
    generic policy text (see `is_supported_wallet_descriptor()`).

        wsh():  or_d(<primary>, and_v(v:<recovery>, older(N)))
                or_i(and_v(v:<recovery>, older(N)), <primary>)
        tr():   primary is the key-path (internal) key; the single hidden
                script-path leaf is and_v(v:<recovery>, older(N))

    Both `or_d` and `or_i` appear because the miniscript compiler's choice
    depends on the primary path. `or_d(X,Z)` requires X to be dissatisfiable,
    which an n-of-n `and_v` chain is not, so an all-keys-required primary
    compiles to `or_i` instead -- and with the branches in the opposite order.
    Confirmed against a real Liana 3-of-3 export. Rather than encode that as
    two positional cases, the branch carrying the timelock is identified by
    inspection and the other is taken as the primary.

    Either path may be a single key, a k-of-n quorum, or an n-of-n; see
    `_match_key_group()` for the accepted forms. A 2-of-3 primary with a
    single-key timelocked recovery is Liana's most common real-world
    configuration, so it is supported rather than treated as an edge case.

    Returns a `LianaRecoveryPolicy`, or `None` if the descriptor is anything
    else -- including this exact shape but with a BIP68 *time-based* (rather
    than block-based) timelock encoding. Liana has never been observed to
    produce that encoding (every real descriptor and confirmed on-chain spend
    used in this PR's own hardware testing used plain block counts), so it is
    deliberately left unrecognized rather than assumed equivalent to blocks.

    Structural match only -- this does not verify the keys are ours or derive
    anything. That happens downstream (PSBTParser, verify_multisig_output())
    exactly as it does for basic multisig.
    """
    if descriptor.is_basic_multisig:
        return None

    if descriptor.is_taproot:
        leaves = _flatten_taptree_leaves(descriptor.taptree)
        if len(leaves) != 1:
            return None
        if descriptor.key is None:
            return None
        # Taproot's key-path spend is inherently a single key.
        primary_group = (1, [descriptor.key])
        recovery = _match_timelocked_branch(leaves[0].miniscript)
        if recovery is None:
            return None
        recovery_group, timelock_blocks = recovery

    elif descriptor.is_segwit and descriptor.miniscript is not None:
        top = _unwrap(descriptor.miniscript)
        if getattr(top, "NAME", None) not in ("or_d", "or_i"):
            return None
        if len(top.args) != 2:
            return None

        # Which branch is which depends on the operator, so identify the
        # timelocked one instead of assuming a position.
        for primary_node, recovery_node in ((top.args[0], top.args[1]),
                                            (top.args[1], top.args[0])):
            recovery = _match_timelocked_branch(recovery_node)
            if recovery is None:
                continue
            primary_group = _match_key_group(primary_node)
            if primary_group is None:
                continue
            recovery_group, timelock_blocks = recovery
            break
        else:
            return None

    else:
        return None

    primary_threshold, primary_keys = primary_group
    recovery_threshold, recovery_keys = recovery_group

    # A threshold that cannot be satisfied, or one the display would describe
    # incorrectly, means this isn't a shape we can present honestly.
    if not 1 <= primary_threshold <= len(primary_keys):
        return None
    if not 1 <= recovery_threshold <= len(recovery_keys):
        return None

    # Too many keys to fit on the curated screen. Refusing here (which routes
    # to NotYetImplementedView) is the safe outcome: the alternative is a
    # screen whose recovery section is pushed under the buttons and silently
    # invisible, hiding the timelocked path entirely -- strictly worse than
    # declining to display the wallet at all.
    def _lines(keys):
        return -(-len(keys) // _FINGERPRINTS_PER_LINE)  # ceil division

    if _lines(primary_keys) + _lines(recovery_keys) > MAX_POLICY_FINGERPRINT_LINES:
        return None

    return LianaRecoveryPolicy(
        primary_threshold=primary_threshold,
        primary_keys=primary_keys,
        recovery_threshold=recovery_threshold,
        recovery_keys=recovery_keys,
        timelock_blocks=timelock_blocks,
    )



def get_descriptor_policy_summary(descriptor: Descriptor, max_length: int = 180) -> str:
    """
    Short plain-English summary of a descriptor's spending policy, for screens
    that label a wallet in one line (e.g. Address Explorer's "Wallet
    descriptor" field).

    A descriptor matching the curated recovery template gets a fixed short
    name rather than a rendering of its policy expression. That is the whole
    point: a nested "(key A) or ((key B) and (after N blocks))" string does
    not fit these one-line fields, and line-wrapping it would not help -- the
    user would still have to parse parenthesization to understand it, which
    is what makes it unsafe to show (seedsigner#306, PR #1026). Details of
    the policy belong on the curated review screen
    (LianaRecoveryWalletScreen), which presents them as labeled fields.

    Handled here rather than at the call sites so that no current or future
    caller can reintroduce the raw expression by accident.

    Correctness requirement: a taproot descriptor with a hidden script-path
    recovery leaf must never be summarized as plain single-key/single-signature.
    This is structural, not case-by-case -- the taproot branch below always
    enumerates every leaf found by `_flatten_taptree_leaves()` if any exist,
    regardless of whether each leaf's contents can be perfectly described (an
    unrecognized leaf fragment still shows up as raw text via
    `_describe_miniscript_node()`'s fallback, it's just never omitted).
    """
    if match_liana_recovery_policy(descriptor) is not None:
        # TRANSLATOR_NOTE: Short name for a wallet that can be spent now by one key, or by a recovery key after a timelock
        return _("Recovery wallet")

    if descriptor.is_basic_multisig:
        threshold, n = get_multisig_policy(descriptor)
        # TRANSLATOR_NOTE: Multisig policy. For a "2 of 3" policy, "threshold" = 2; "n" = 3
        summary = _("{threshold} of {n} multisig").format(threshold=threshold, n=n)

    elif descriptor.is_taproot:
        parts = [_describe_miniscript_node(descriptor.key)]
        leaves = _flatten_taptree_leaves(descriptor.taptree)
        if leaves:
            leaf_descriptions = [_describe_miniscript_node(leaf.miniscript) for leaf in leaves]
            # TRANSLATOR_NOTE: {key} is the taproot key-path spending key; {leaves} lists hidden alternate spending paths
            summary = _("Taproot: key-path ({key}); script-path: {leaves}").format(
                key=parts[0], leaves="; ".join(leaf_descriptions)
            )
        else:
            # TRANSLATOR_NOTE: a taproot descriptor with no hidden script paths at all -- key-path spend only
            summary = _("Taproot: key-path only ({key})").format(key=parts[0])

    elif descriptor.miniscript is not None:
        summary = _describe_miniscript_node(descriptor.miniscript)

    elif descriptor.key is not None:
        # Bare single key (e.g. wpkh()/pkh()); describe safely rather than
        # raising if a caller ever routes one here.
        summary = _describe_miniscript_node(descriptor.key)

    else:
        raise ValueError(f"Unable to summarize descriptor policy: {descriptor}")

    if len(summary) > max_length:
        summary = summary[: max_length - 1].rstrip() + "…"  # ellipsis
    return summary



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
