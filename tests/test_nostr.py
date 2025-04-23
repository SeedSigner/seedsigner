from seedsigner.helpers import nostr
from seedsigner.models.seed import Seed

from base import BaseTest



class TestNostr(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()


    def test__derive_nostr_key(self):
        """ Should follow the NIP-06 process to derive a nostr key from a BIP-39 mnemonic. """
        # Test vectors from NIP-06: https://github.com/nostr-protocol/nips/blob/master/06.md
        test_vectors = [
            dict(
                mnemonic="leader monkey parrot ring guide accident before fence cannon height naive bean".split(),
                privkey_hex="7f7ff03d123792d6ac594bfa67bf6d0c0ab55b6b1fdb6249303fe861f1ccba9a",
                nsec="nsec10allq0gjx7fddtzef0ax00mdps9t2kmtrldkyjfs8l5xruwvh2dq0lhhkp",
                pubkey_hex="17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917",
                npub="npub1zutzeysacnf9rru6zqwmxd54mud0k44tst6l70ja5mhv8jjumytsd2x7nu"
            ),
            dict(
                mnemonic="what bleak badge arrange retreat wolf trade produce cricket blur garlic valid proud rude strong choose busy staff weather area salt hollow arm fade".split(),
                privkey_hex="c15d739894c81a2fcfd3a2df85a0d2c0dbc47a280d092799f144d73d7ae78add",
                nsec="nsec1c9wh8xy5eqdzln7n5t0ctgxjcrdug73gp5yj0x03gntn67h83twssdfhel",
                pubkey_hex="d41b22899549e1f3d335a31002cfd382174006e166d3e658e3a5eecdb6463573",
                npub="npub16sdj9zv4f8sl85e45vgq9n7nsgt5qphpvmf7vk8r5hhvmdjxx4es8rq74h",
            )
        ]

        for test_vector in test_vectors:
            seed = Seed(test_vector["mnemonic"])
            assert nostr.get_privkey_hex(seed) == test_vector["privkey_hex"]
            assert nostr.get_nsec(seed) == test_vector["nsec"]
            assert nostr.get_pubkey_hex(seed) == test_vector["pubkey_hex"]
            assert nostr.get_npub(seed) == test_vector["npub"]

