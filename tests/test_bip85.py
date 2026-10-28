from seedsigner.models.seed import Seed


def test_derive_child_mnemonic():
    mnemonic = "resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split()
    seed = Seed(mnemonic=mnemonic)

    # Index 0, 12 words
    expected_12 = "unusual topic foot figure pulp target glimpse core electric spot neglect fame"
    assert seed.get_bip85_child_mnemonic(0, 12) == expected_12

    # Index 0, 24 words
    expected_24 = "imitate post very mandate retreat prevent tiny snow fetch canvas town shrug fix food summer library symptom occur slam style cruise wolf phone key"
    assert seed.get_bip85_child_mnemonic(0, 24) == expected_24


def test_derive_child_mnemonic_multiple_indices():
    mnemonic = "resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split()
    seed = Seed(mnemonic=mnemonic)

    # Index 1, 12 words
    expected_12_idx1 = "angry ribbon stage draw flock charge poverty caution impact behind across wide"
    assert seed.get_bip85_child_mnemonic(1, 12) == expected_12_idx1

    # Index 1, 24 words
    expected_24_idx1 = "cruel float race cool aerobic excess ripple mesh cousin amazing afford typical mean stomach eye tube salute hidden world wasp tortoise robot mom turn"
    assert seed.get_bip85_child_mnemonic(1, 24) == expected_24_idx1
