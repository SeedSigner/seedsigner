# Entropy quality verification

SeedSigner's dice and camera seed-generation flows include quality checks on
the collected entropy, adapted from [Krux](https://github.com/selfcustody/krux)
with two additions (a Markov entropy estimator for dice and a
frame-differencing sensor-noise check for the camera).

**These checks never alter mnemonic derivation.** They are measurement-only:
the same rolls or the same capture produce exactly the same seed with or
without them. Their sole effect is to inform the user and to require an
explicit "Proceed anyway" confirmation before clearly degenerate input is
hashed into a seed. BIP-39's checksum validates transcription of a mnemonic,
not the quality of the entropy behind it; these checks address that gap.

## Dice rolls

After roll entry, a verdict screen reports **Good entropy** or
**Insufficient entropy**. The verdict is backed by:

1. **Frequency Shannon entropy** of the face counts — catches a heavily
   skewed die (e.g. one face coming up ~55% of the time).
2. **First-order Markov (conditional) entropy** of roll-to-roll transitions,
   with a Miller-Madow small-sample bias correction — catches patterned
   input. A cyclic keypad walk (`123456123456...`) uses every face equally
   often, so it looks perfect to a frequency count, but every roll is fully
   determined by the previous one; its conditional entropy is ~0.
3. **Pattern detection** (Krux's derivative-entropy check) as an independent
   flag for sequential/cyclic input.

The verdict uses the *more conservative* of the two estimates. The
"insufficient" floors (85 bits for 12-word / 205 bits for 24-word) were
calibrated over 20,000 fair-die simulations at the standard 50 / 99 roll
counts: honest rolls are flagged less than ~1 time in 20,000, while
patterned or heavily skewed input lands far below the floor.

On an insufficient verdict the user may **Re-roll** (discards the entry) or
explicitly **Proceed anyway**.

At the end of the flow a **roll distribution screen** shows a per-face bar
chart of the entered rolls, making a biased die visible at a glance.

## Camera captures

When the final full-resolution image is captured, a second frame is captured
immediately afterward (exposure and white balance are already locked, so the
pair differs only by sensor noise and hand micro-movement). The second frame
is used **only for measurement and is never hashed into the seed**; it is
cleared from memory on every exit path.

Every capture then gets an entropy report screen showing:

- **Scene** — Shannon entropy (bits/pixel) of the pixel-value distribution,
  measured on a downsampled copy (thresholds from Krux). Catches flat, dark,
  or uniform captures (lens cap, blank wall).
- **Deviation** — RMS of per-channel standard deviations (thresholds from
  Krux). Catches low-variance captures that still have some value spread.
- **Sensor noise** — Shannon entropy of the pixel-wise *difference* between
  the two back-to-back captures. Scene content is identical in both frames
  and cancels out of the difference; what remains approximates the temporal
  sensor noise that makes a capture unpredictable even to an observer who
  knows the scene. Two identical frames — a frozen or replayed sensor feed —
  score exactly 0.0 and fail, a fault that scene statistics alone cannot
  detect.

A capture that fails any check offers **Retake** or an explicit
**Proceed anyway**.

## Honest limitations

These are statistical *screens* against accidental or careless input, not
certifications of randomness:

- No test computed from ~100 samples can prove a source is random. A
  deterministic sequence with no short-range structure (e.g. memorized digits
  of an irrational number) will pass the dice checks.
- Camera captures are JPEG-compressed, which attenuates low-amplitude sensor
  noise; the sensor-noise figure is a lower bound.
- The security of camera-based seeds rests primarily on sensor noise across
  the full hash chain (preview frames + final image + device-unique data),
  not on scene content. The checks exist to catch the degenerate cases where
  that assumption breaks down.

## Tests

`tests/test_entropy_verification.py` covers the estimators, the verdict
calibration, and the frame-differencing math (including the
identical-frames-scores-zero regression case). The module has no hardware
dependencies beyond PIL, so the tests run anywhere.
