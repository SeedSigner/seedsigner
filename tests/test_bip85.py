import pytest
from unittest.mock import MagicMock
from seedsigner.models.seed import Seed
from embit import bip39

from seedsigner.models.settings import SettingsConstants



def test_derive_child_mnemonic():

    expected = "unusual topic foot figure pulp target glimpse core electric spot neglect fame"
    seed = Seed(mnemonic="resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split())

    actual = seed.get_bip85_child_mnemonic(0, 12)
    assert actual == expected


    expected = "imitate post very mandate retreat prevent tiny snow fetch canvas town shrug fix food summer library symptom occur slam style cruise wolf phone key"
    seed = Seed(mnemonic="resource timber firm banner horror pupil frozen main pear direct pioneer broken grid core insane begin sister pony end debate task silk empty curious".split())

    actual = seed.get_bip85_child_mnemonic(0, 24)
    assert actual == expected
