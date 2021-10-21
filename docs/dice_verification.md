## Verifying dice seed generation 

It is possible to do a 'dry run' to verify that seed generation has not been tempered.
This will ensure that the derivation algorithm has not been tempered and is still same as well known algorithm used bu coldcard and ian coleman bip39 webpage.

### Verifying with Ian coleman webpage

Go to https://iancoleman.io/bip39 and check show entropy detail:
<img src="img/dice_entr.png">

And then make sure to check 'Hex' or 'base 10' (1) and 24 words as mnemonic length (2).
Do not use 'dice' format because dice 6 will be replaced by 0.
And then enter the 99 dices numbers in (3) :
<img src="img/dice_type.png">


