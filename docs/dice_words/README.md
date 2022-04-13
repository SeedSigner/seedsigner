# Dice Words

[SeedSigner](https://github.com/SeedSigner/seedsigner/) is an open source,
DIY, fully-airgapped Bitcoin hardware wallet that wipes all private data from
memory each time it's turned off. That makes it a great device to assist in
generating BIP39 mnemonics in alternate ways, even if they are to be later
used in other schemes or devices.

There have been many ways proposed to generate high quality random seeds,
including cutting out each word and drawing (with replacement) from a hat.

Here we provide templates for generating seed words directly from the rolls of
dice, where each die has a power of 2 number of faces.

The idea here is to generate the exact bit stream that would be encoded into a
[Compact SeedQR](../seed_qr#compactseedqr-specification). To do that, you
pick 12, 24, 11, or 23 words using your dice and these templates, and then use
the Calculate Last Word functionality of your seed signer to make a valid
mnemonic. If using 11 or 23 words, the last 7 or 3 bits (respectively) of your
seed will be 0s. If using 12 or 24 words, the last 4 or 8 bits (respectively)
of your last rolled word will be replaced with a corrected checksum in the
resulting mnemonic.

## Dice and randomness

We'd all like to think that whatever dice we're playing D&D with are
completely fair. In reality most dice have bias. Before using any of the
templates provided here, you _should_ analyze your own dice to your own
satisfaction for fairness.

See [chisq.py](./chisq.py)[^1] for a program that takes a file of die rolls (1 or
more whitespace separate rolls per line) and calculates whether the
probability that the die is fair is greater than a user specified threshold
(default 0.99). When using this method, at least `n-faces * 10` rolls should
be used.

## Printable Templates

### [3d16 or 1d8 + 2d16](./Dice%20Seed%20Words%20-%203d16.pdf)

This template allows selecting 1 word for every 3 dice rolled, which is quite
labor efficient. It does, however, require the use of d16s, which are not
common. When used with 3 d16, the highest bit of the first d16 in each word is
dropped. 3d16 produce 12 bits of entropy, and only 11 are used in each word.

### [4d8 or 3d8 + 1d4](./Dice%20Seed%20Words%20-%204d8.pdf)

This template allows selecting 1 word for every 4 dice rolled, using only
common RPG dice. When used with 4d8, the highest bit of the last d8 is
dropped. 4d8 produce 12 bits of entropy, and only 11 are used in each word.

### [6d4 or 1d8 + 4d4 or 1coin + 5d4](./Dice%20Seed%20Words%20-%206d4.pdf)

This template allws selecting 1 word for every 5-6 dice rolled, using only
common RPG dice. When used with 6d4, the highest bit of the first d4 is
dropped. 6d4 produce 12 bits of entropy, and only 11 are used in each word.

[^1]: `pip install scipy` then `python chisq.py -h`
