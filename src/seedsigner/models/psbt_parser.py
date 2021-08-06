from embit import psbt, script, ec, bip32, bip39
from embit.networks import NETWORKS
from io import BytesIO

class PSBTParser():

    def __init__(self, p, seed_phrase=[], passphrase="", network="main"):
        self.seed_phrase = seed_phrase
        self.passphrase = passphrase
        self.network = network
        self.psbt = p

        self.policy = None
        self.spend_amount = 0
        self.change_amount = 0
        self.fee_amount = 0
        self.input_amount = 0
        self.destination_addresses = []
        self.self_addresses = []

        self.seed = None
        self.root = None

        if self.seed_phrase != None:
            self.parse(self.psbt,self.seed_phrase,self.passphrase,self.network)

    def __setSeedRoot(self, seed_phrase, passphrase, network):
        self.seed = bip39.mnemonic_to_seed(" ".join(seed_phrase).strip(), passphrase)
        self.root = bip32.HDKey.from_seed(self.seed, version=NETWORKS[network]["xprv"])

    def parse(self, p, seed_phrase=[], passphrase="", network="main"):
        is_psbt_empty = False
        try:
            if p == None:
                is_psbt_empty = True
        except:
            pass

        if is_psbt_empty:
            return False

        if len(seed_phrase) == 0:
            return False

        self.__setSeedRoot(seed_phrase,passphrase,network)

        rt = self.__parseInputs()
        if rt == False:
            return False

        rt = self.__parseOutputs()
        if rt == False:
            return False

        return True

    def __parseInputs(self):
        self.input_amount = 0
        for inp in self.psbt.inputs:
            self.input_amount += inp.witness_utxo.value
            inp_policy = PSBTParser.__get_policy(inp, inp.witness_utxo.script_pubkey, self.psbt.xpubs)
            if self.policy == None:
                self.policy = inp_policy
            else:
                if self.policy != inp_policy:
                    raise RuntimeError("Mixed inputs in the transaction")

    def __parseOutputs(self):
        self.spend_amount = 0
        self.change_amount = 0
        self.fee_amount = 0
        self.destination_addresses = []
        self.self_addresses = []
        for i, out in enumerate(self.psbt.outputs):
            out_policy = PSBTParser.__get_policy(out, self.psbt.tx.vout[i].script_pubkey, self.psbt.xpubs)
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

                # single-sig
                elif "pkh" in self.policy["type"]:
                    my_pubkey = None
                    # should be one or zero for single-key addresses
                    if len(out.bip32_derivations.values()) > 0:
                        der = list(out.bip32_derivations.values())[0].derivation
                        my_pubkey = self.root.derive(der)
                    if self.policy["type"] == "p2wpkh" and my_pubkey is not None:
                        sc = script.p2wpkh(my_pubkey)
                    elif self.policy["type"] == "p2sh-p2wpkh" and my_pubkey is not None:
                        sc = script.p2sh(script.p2wpkh(my_pubkey))

                    if sc.data == self.psbt.tx.vout[i].script_pubkey.data:
                        is_change = True

                if sc.data == self.psbt.tx.vout[i].script_pubkey.data:
                    is_change = True
            if is_change:
                self.change_amount += self.psbt.tx.vout[i].value
                self.self_addresses.append(self.psbt.tx.vout[i].script_pubkey.address(NETWORKS[self.network]))
            else:
                self.spend_amount += self.psbt.tx.vout[i].value
                self.destination_addresses.append(self.psbt.tx.vout[i].script_pubkey.address(NETWORKS[self.network]))

        self.fee_amount = self.psbt.fee()
        return True

    @staticmethod
    def trim(tx):
        trimmed_psbt = psbt.PSBT(tx.tx)
        sigsEnd = 0
        for i, inp in enumerate(tx.inputs):
            sigsEnd += len(list(inp.partial_sigs.keys()))
            trimmed_psbt.inputs[i].partial_sigs = inp.partial_sigs

        return trimmed_psbt

    @staticmethod
    def sigCount(tx):
        cnt = 0
        for i, inp in enumerate(tx.inputs):
            cnt += len(list(inp.partial_sigs.keys()))

        return cnt

    # checks that all inputs are from the same wallet
    @staticmethod
    def __get_policy(scope, scriptpubkey, xpubs):
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
        if "p2wsh" in script_type and scope.witness_script is not None:
            m, n, pubkeys = PSBTParser.__parse_multisig(scope.witness_script)
            # check pubkeys are derived from cosigners
            try:
                cosigners = PSBTParser.__get_cosigners(pubkeys, scope.bip32_derivations, xpubs)
                policy.update({"m": m, "n": n, "cosigners": cosigners})
            except:
                policy.update({"m": m, "n": n})
        return policy

    # returns m, n, and pubkeys from multisig script
    @staticmethod
    def __parse_multisig(sc):
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
    def __get_cosigners(pubkeys, derivations, xpubs):
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
