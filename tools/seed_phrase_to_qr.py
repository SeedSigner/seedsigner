from seedsigner.models.encode_qr import CompactSeedQrEncoder, SeedQrEncoder
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants

"""
This is a utility for testing / dev purposes only. 
"""

if __name__ == "__main__":
    import qrcode
    import sys

    print("""
*******************************************************************************

    This is a utility for testing / dev purposes ONLY.

    A SeedQR for a real seed holding actual value should never be created
    this way.

*******************************************************************************
""")

    COMPACT = 1
    STANDARD = 2
    format = int(input("1. Compact SeedQR\n2. Standard SeedQR\nEnter 1 or 2: ").strip())
    if format not in [COMPACT, STANDARD]:
        print("Invalid option")
        sys.exit(1)

    seed_phrase = input("\nEnter 12- or 24-word test seed phrase: ").strip().split(" ")

    if format == COMPACT:
        encoder = CompactSeedQrEncoder(seed_phrase=seed_phrase, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
    else:
        encoder = SeedQrEncoder(seed_phrase=seed_phrase, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

    qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=3)
    qr.add_data(encoder.next_part())
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB').show()

    seed = Seed(seed_phrase)
    print(f"\nfingerprint: {seed.get_fingerprint()}\n")
