# SeedSigner Hybrid Entropy v1 (experimental)

This document specifies an experimental, auditable 24-word seed ceremony that
combines one canonical camera frame with an exactly uniform value extracted
from physical dice. It is a prototype for review and testing, not yet a stable
SeedSigner derivation standard.

The construction is designed around this conditional claim:

> If either 256-bit input is uniformly distributed and remains independent of
> the other input, their XOR is uniformly distributed.

The protocol uses a camera commitment before dice entry so the camera input is
frozen first. The camera value itself remains hidden until an acceptable dice
block has been recorded; displaying the camera value earlier would allow a
later malicious dice chooser to cancel it algebraically.

## Scope and threat model

This ceremony helps with independent source failures and enables an external
implementation to reproduce the derivation. It cannot force compromised
firmware to execute honestly: code running on the same SeedSigner can observe
all internal values. A user relying on adversarial-firmware detection must
record the transcript and verify the final mnemonic on an independent device
before using it.

The camera PNG, dice transcript, camera reveal, and final mnemonic are
seed-equivalent secrets when combined. They must not be published and should
be securely destroyed or protected after verification.

## Protocol

Only 24-word BIP-39 mnemonics are supported. The existing camera-only and
dice-only derivations are unchanged.

### 1. Canonical camera value

SeedSigner captures two full-resolution frames back-to-back after exposure and
white balance are locked. Before committing, it reports scene Shannon entropy,
pixel deviation, and temporal sensor noise calculated from the pixel-wise
difference between the frames. An identical pair detects a frozen or replayed
feed and is reported as insufficient. The user can retake the capture or make
an explicit **Proceed anyway** choice.

This is the same frame-differencing construction used by PR #993: the second
frame is measurement-only and is cleared on every exit path. It is not hashed,
committed, revealed, or XORed. Consequently the canonical camera value and the
deterministic verifier remain based on the first frame alone.

The accepted first camera frame must be RGB with exactly three bytes per pixel.
Pixels are serialized row-major, top-to-bottom, in R, G, B channel order.

```text
canonical_camera =
    "SeedSigner Hybrid Camera RGB v1" || 0x00
    || uint32_be(width)
    || uint32_be(height)
    || uint64_be(width * height * 3)
    || rgb_pixel_bytes

camera256 = SHA256(canonical_camera)
```

File metadata and compression are excluded. An external verifier should use a
lossless RGB PNG containing the exact committed pixels.

### 2. Commit without revealing

Before any dice entry, SeedSigner calculates:

```text
camera_commitment = SHA256(
    "SeedSigner Hybrid Camera Commitment v1" || 0x00 || camera256
)
```

The full commitment is displayed as a QR record:

```text
seedsigner-hybrid-v1:camera-commitment:<64 lowercase hex characters>
```

The user records this QR. `camera256` remains hidden in memory.

### 3. Exact 256-bit dice extraction

One candidate block contains 100 six-sided die rolls. Faces map to base-6
digits as follows:

```text
face:   1 2 3 4 5 6
digit:  0 1 2 3 4 5
```

The first roll is the most-significant digit:

```text
x = 0
for digit in roll_order:
    x = x * 6 + digit
```

Define:

```text
N     = 6^100
Q     = floor(N / 2^256) = 5
LIMIT = Q * 2^256
```

If `x >= LIMIT`, the entire block is rejected and a fresh 100-roll block is
required. If `x < LIMIT`:

```text
dice256 = uint256_be(x mod 2^256)
```

Every possible 256-bit output has exactly five accepted preimages. The
acceptance probability is approximately 88.6184%; rejection is approximately
11.3816%. The rejection rule is essential—reducing every one of the `6^100`
values modulo `2^256` would bias some outputs.

Only protocol-mandated rejections should be discarded. Voluntarily abandoning
accepted blocks allows the operator to grind through outputs and invalidates a
claim that the first accepted result was sampled uniformly.

### 4. Reveal and verify

After an acceptable dice block has been frozen, SeedSigner reveals:

```text
seedsigner-hybrid-v1:camera-reveal:<camera256 as 64 lowercase hex characters>
```

The verifier hashes the reveal with the commitment domain and confirms that it
matches the previously recorded commitment.

### 5. XOR and BIP-39

```text
final256 = camera256 XOR dice256
mnemonic = BIP39_24_WORDS(final256)
```

The XOR is byte-for-byte across the two 32-byte values. BIP-39 appends its
eight checksum bits and maps the resulting 264 bits to 24 words.

## Deterministic vector

The canonical camera is a 2×2 RGB frame whose 12 pixel bytes are:

```text
00 01 02 03 04 05 06 07 08 09 0a 0b
```

The dice block is the first 100 characters of `123456` repeated:

```text
12345612345612345612345612345612345612345612345612
34561234561234561234561234561234561234561234561234
```

Expected values:

```text
camera256:
85e251941a9379b02578cff8a06e99707cf239c6f5f2aac9641a41aae280dd41

camera commitment:
1ad620d507d62a4148bef04889c2c7b2ecdf71868a9411fb4cf556145b64ffe0

dice256:
39bd194e3b989d612e6ed5bf485bae130d53f5f532f29585e98ecd298282a5c3

final256:
bc5f48da210be4d10b161a47e835376371a1cc33c7003f4c8d948c8360027882

mnemonic:
rough where custom dragon salad hammer clump select elevator double evidence
shoulder borrow toward someone theme dismiss good gown boil current abuse tilt
erupt
```

## Independent verifier

After installing the project dependencies, verify a ceremony with:

```bash
python tools/hybrid_entropy_verifier.py \
    --camera-png exact-camera.png \
    --rolls-file private-rolls.txt
```

The rolls file may contain whitespace, but must contain exactly 100 faces after
whitespace is removed. The verifier prints secret material, including the
mnemonic; use it only in an appropriately private offline environment.

The current on-device prototype exports the commitment and camera reveal as
QRs, but does **not** yet export the full canonical camera frame. Consequently,
the verifier can test the complete protocol with a supplied PNG, while a live
SeedSigner ceremony can independently verify the combiner and commitment but
cannot yet prove that the revealed camera value corresponds to the displayed
physical capture. A deliberately warned, temporary microSD export or another
lossless transport would be required to close that gap.

## Memory handling

Raw camera frame references are cleared after the commitment is created. The
hidden camera and accepted dice values are held in mutable 32-byte buffers and
overwritten on successful completion, cancellation, or return to the main
menu. This is best-effort memory hygiene in Python, not proof that no transient
copy ever existed.
