import pytest

from embit import bip39
from seedsigner.helpers import hybrid_entropy, mnemonic_generation


CAMERA_PIXELS = bytes(range(12))
ACCEPTED_ROLLS = ("123456" * 16) + "1234"


def test_canonical_camera_and_commitment_vector():
    canonical = hybrid_entropy.canonical_camera_bytes(2, 2, CAMERA_PIXELS)
    assert canonical.startswith(hybrid_entropy.CAMERA_DOMAIN)
    assert canonical.endswith(CAMERA_PIXELS)

    camera256 = hybrid_entropy.camera256_from_rgb(2, 2, CAMERA_PIXELS)
    commitment = hybrid_entropy.camera_commitment(camera256)

    assert camera256.hex() == "85e251941a9379b02578cff8a06e99707cf239c6f5f2aac9641a41aae280dd41"
    assert commitment.hex() == "1ad620d507d62a4148bef04889c2c7b2ecdf71868a9411fb4cf556145b64ffe0"
    assert hybrid_entropy.verify_camera_commitment(camera256, commitment)
    assert not hybrid_entropy.verify_camera_commitment(bytes(32), commitment)


def test_canonical_camera_rejects_ambiguous_inputs():
    with pytest.raises(ValueError, match="dimensions"):
        hybrid_entropy.canonical_camera_bytes(0, 2, CAMERA_PIXELS)
    with pytest.raises(TypeError, match="must be bytes"):
        hybrid_entropy.canonical_camera_bytes(2, 2, bytearray(CAMERA_PIXELS))
    with pytest.raises(ValueError, match="exactly 12 bytes"):
        hybrid_entropy.canonical_camera_bytes(2, 2, CAMERA_PIXELS[:-1])


def test_exact_uniform_dice_extractor_vector_and_boundaries():
    assert hybrid_entropy.DICE_PREIMAGES_PER_OUTPUT == 5
    assert hybrid_entropy.DICE_ACCEPTANCE_LIMIT == 5 * 2**256

    dice256 = hybrid_entropy.extract_uniform_dice256(ACCEPTED_ROLLS)
    assert dice256.hex() == "39bd194e3b989d612e6ed5bf485bae130d53f5f532f29585e98ecd298282a5c3"
    assert hybrid_entropy.extract_uniform_dice256("1" * 100) == bytes(32)

    with pytest.raises(hybrid_entropy.DiceExtractionRejected):
        hybrid_entropy.extract_uniform_dice256("6" * 100)


def test_dice_extractor_rejects_invalid_rolls():
    with pytest.raises(ValueError, match="exactly 100"):
        hybrid_entropy.extract_uniform_dice256("1" * 99)
    with pytest.raises(ValueError, match="invalid face"):
        hybrid_entropy.extract_uniform_dice256("1" * 99 + "7")


def test_xor_vector_and_uniform_input_identity():
    camera256 = hybrid_entropy.camera256_from_rgb(2, 2, CAMERA_PIXELS)
    final256 = hybrid_entropy.combine_camera_and_dice(camera256, ACCEPTED_ROLLS)
    assert final256.hex() == "bc5f48da210be4d10b161a47e835376371a1cc33c7003f4c8d948c8360027882"

    mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(final256)
    assert " ".join(mnemonic) == (
        "rough where custom dragon salad hammer clump select elevator double "
        "evidence shoulder borrow toward someone theme dismiss good gown boil "
        "current abuse tilt erupt"
    )
    assert bip39.mnemonic_is_valid(" ".join(mnemonic))

    uniform_value = bytes(range(32))
    arbitrary_value = bytes(reversed(range(32)))
    combined = hybrid_entropy.xor256(arbitrary_value, uniform_value)
    assert hybrid_entropy.xor256(arbitrary_value, combined) == uniform_value


def test_protocol_qr_records_are_versioned():
    camera256 = hybrid_entropy.camera256_from_rgb(2, 2, CAMERA_PIXELS)
    commitment = hybrid_entropy.camera_commitment(camera256)

    assert hybrid_entropy.commitment_record(commitment) == (
        "seedsigner-hybrid-v1:camera-commitment:" + commitment.hex()
    )
    assert hybrid_entropy.camera_reveal_record(camera256) == (
        "seedsigner-hybrid-v1:camera-reveal:" + camera256.hex()
    )
