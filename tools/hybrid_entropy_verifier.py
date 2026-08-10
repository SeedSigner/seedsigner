import argparse
from pathlib import Path

from PIL import Image

from seedsigner.helpers import hybrid_entropy, mnemonic_generation


parser = argparse.ArgumentParser(
    description="Independently verify SeedSigner Hybrid Entropy v1",
)
parser.add_argument(
    "--camera-png",
    required=True,
    type=Path,
    help="Lossless PNG containing the exact committed RGB pixels",
)
parser.add_argument(
    "--rolls-file",
    required=True,
    type=Path,
    help="Text file containing the recorded 100 die faces",
)
args = parser.parse_args()


with Image.open(args.camera_png) as image:
    image.load()
    if image.format != "PNG":
        raise ValueError("The verifier accepts only lossless PNG camera files")
    if image.mode != "RGB":
        raise ValueError("The camera PNG must decode directly to RGB mode")

    camera256 = hybrid_entropy.camera256_from_rgb(
        image.width,
        image.height,
        image.tobytes(),
    )

rolls = "".join(args.rolls_file.read_text().split())
dice256 = hybrid_entropy.extract_uniform_dice256(rolls)
commitment = hybrid_entropy.camera_commitment(camera256)
final256 = hybrid_entropy.xor256(camera256, dice256)
mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(final256)

print(f"Protocol:          {hybrid_entropy.PROTOCOL_NAME}")
print(f"Camera commitment: {commitment.hex()}")
print(f"Camera value:      {camera256.hex()}")
print(f"Dice value:        {dice256.hex()}")
print(f"Final entropy:     {final256.hex()}")
print(f"BIP-39 mnemonic:   {' '.join(mnemonic)}")
