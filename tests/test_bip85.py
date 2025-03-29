from seedsigner.models.seed import Seed
from seedsigner.controller import Controller

def test_derive_child_mnemonic():

    expected = "unusual topic foot figure pulp target glimpse core electric spot neglect fame"
    seed = Seed(mnemonic="resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split())

    actual = seed.get_bip85_child_mnemonic(0, 12)
    assert actual == expected


    expected = "imitate post very mandate retreat prevent tiny snow fetch canvas town shrug fix food summer library symptom occur slam style cruise wolf phone key"
    seed = Seed(mnemonic="resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split())

    actual = seed.get_bip85_child_mnemonic(0, 24)
    assert actual == expected

def test_derive_and_load_child_seed():
    controller = Controller.get_instance()
    master_seed = Seed(mnemonic=["word"] * 12)
    controller.storage.seeds.append(master_seed)
    seed_num = 0
    bip85_data = {"child_index": 0, "num_words": 12}
    
    #simulate BIP-85 derivation and loading
    derived_mnemonic = master_seed.get_bip85_child_mnemonic(0, 12)
    derived_seed = Seed(
        mnemonic=derived_mnemonic.split(),
        passphrase="",
        bip85_parent=seed_num,
        bip85_index=0
    )
    controller.storage.seeds.append(derived_seed)
    
    assert len(controller.storage.seeds) == 2
    assert controller.storage.seeds[1].get_fingerprint() != master_seed.get_fingerprint()
    assert controller.storage.seeds[1].display_name.endswith("(Child #0)")