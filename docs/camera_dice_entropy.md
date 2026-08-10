# Camera + dice entropy

The **Camera + dice** tool creates one BIP-39 mnemonic from two independently
collected inputs. It is intended as a hedge against accidental weakness in
either source: a poor camera capture still has the dice input, while imperfect
dice still have the camera input.

This mode does not replace or alter the existing camera-only and dice-only
flows. It is a separate, explicitly versioned derivation and therefore produces
a different mnemonic from either input used on its own.

## User flow

1. Select **Tools > Camera + dice**.
2. Capture camera entropy using the existing live-preview and final-image flow.
3. Select a 12- or 24-word mnemonic.
4. Enter 50 rolls for 12 words or 99 rolls for 24 words.
5. Back up the resulting mnemonic normally. The original image and rolls are
   not needed after the mnemonic has been recorded.

The full dice requirement is retained. Camera input is not treated as a reason
to reduce the number of rolls.

## Derivation

The camera stage first runs SeedSigner's existing image hash chain without
modification. In simplified notation:

```text
H0 = SHA256(device_serial)
H1 = SHA256(H0 || capture_time)
Hi = SHA256(Hi-1 || preview_frame_i)
C  = SHA256(Hlast || final_image)
```

`C` is the full 32-byte camera digest. `D` is the exact ASCII dice string, with
one byte per face (`1` through `6`). The combined digest is:

```text
combined = SHA256(
    "SeedSigner camera+dice v1"
    || uint16_be(len(C))
    || C
    || uint16_be(len(D))
    || D
)
```

`||` means byte concatenation and `uint16_be` is an unsigned two-byte
big-endian length. The fixed domain label prevents this construction from
overlapping with another SeedSigner derivation. Length framing makes the two
variable inputs unambiguous. If the framing ever changes, the version in the
domain label must also change.

For a 12-word mnemonic, the first 16 bytes (128 bits) of `combined` are passed
to BIP-39. For a 24-word mnemonic, all 32 bytes (256 bits) are used.

### Deterministic vectors

These vectors make the implementation independently reproducible. The camera
digest is the 32 bytes `00 01 02 ... 1f`.

12 words:

```text
dice:     12345612345612345612345612345612345612345612345612
combined: cad1b7156998271bd5c88127068cea9f5f162abb6ced04b61b3989429e774560
mnemonic: skull misery shed spring list mistake fire awake check crucial deny dirt
```

24 words:

```text
dice:     first 99 characters of "654321" repeated
mnemonic: popular identify bench letter figure crisp inquiry what donate help save entry endless miracle arrow exhibit trash virtual calm silver toe couple club gaze
```

## Security properties and limitations

- The hash conditions the combined inputs but cannot create entropy. A 12-word
  mnemonic remains limited to 128 bits and a 24-word mnemonic to 256 bits.
- The main benefit is robustness. If one independent input remains secret and
  unpredictable, it can protect the result when the other input is weak or
  known.
- Independence matters. Combining two sources affected by the same failure or
  controlled by the same attacker does not justify adding their entropy
  estimates.
- Camera entropy is difficult to quantify from a single capture. This feature
  makes no claim that a capture contains a specific number of entropy bits.
- The mnemonic is intentionally not compatible with either existing
  single-source derivation. Users must not expect camera-only or dice-only
  verification tools to reproduce it.

## Temporary data handling

After the camera hash chain completes, raw preview and final-image references
are cleared. Only the 32-byte camera digest is retained while dice are entered.
It is stored in a mutable buffer and overwritten on completion, cancellation,
or return to the main menu. This is best-effort memory hygiene within Python;
it is not a guarantee that no transient copy ever existed.
