## Verifying dice seed generation 

It is possible to do a 'dry run' to verify that seed generation has not been tempered.
This will ensure that the derivation algorithm has not been tempered and is still the same as the well known algorithm used by coldcard and Ian Coleman bip39 webpage.
For example an 'evil maid' attack would be someone accesing your sdcard and change the code to only take in account 5 or 6 dice, so the 24 words would still feel random but the attacker will need to brute force only 5 or 6 dice (very easy).
This is part of the "do not trust, verify" crypto mottos.<br><br>
**Do NOT use this with any seed you want to use later. This is just for checking that the algorithms get to the same results!!**
**Or you can download the tools to an airgapped Computer or using tails-OS to check there. Do not use any online computer/tool to do this with real seed phrases!!**
<br><br>

### Dice Rolls / Seed Words example

The following 99 dice roll results are used here as an example for a 24 words seed:<br>
> 655152231316521321611331544441236164664431121534415633526456254462245546236542364246312613322234612

The corresponding 24 seed words are:<br>
> eyebrow obvious such suggest poet seven breeze blame virtual frown dynamic donor harsh pigeon express broccoli easy apology scatter force recipe shadow claim radio

<br>

### Creating seed via Dice rolls in Seedsigner (here v0.6.0)

Power up and boot Seedsigner, go to the 'Tools' menu and select 'New Seed' (with the dice symbols):<br>
<img src="img/dicedoc/sesi_tools_dice_seed.png" width="600">

Enter the dice numbers one after another on the next screen:<br>
<img src="img/dicedoc/sesi_dice_1.png" width="600">

Go on until the end (99 dice roll numbers):<br>
<img src="img/dicedoc/sesi_dice_2.png" width="600">

After that the 24 seed words are shown (in 6 screens of 4 words each):<br>
<img src="img/dicedoc/sesi_seed_1.png" width="600">
<br>**.....**<br>
<img src="img/dicedoc/sesi_seed_2.png" width="600">

The fingerprint for this seed is:<br>
<img src="img/dicedoc/sesi_finger_print.png" width="600">
<br><br>

### Create new wallet from seed in Sparrow Wallet to see xpub/zpub and addresses

Open Sparrow Wallet, go to 'File' menu and select 'New Wallet'. Enter a name (e.g. test), and click 'Create Wallet'.
Click 'Airgapped Hardware Wallet' (1) and click on the 'Scan' button in the Seedsigner entry (2) which will open the camera scan screen:<br>
<kbd><img src="img/dicedoc/sparrow_wallet_1.png"></kbd>

On Seedsigner go to the seed just created and click 'Export Xpub':<br>
<img src="img/dicedoc/sesi_export_xpub_1.png" width="600">

Follow these menu entries in Seedsigner:<br>
> Export Xpub --> Single Sig --> Native Segwit --> Sparrow<br>
<img src="img/dicedoc/sesi_export_xpub_2.png" width="600">

Click 'Export Xpub' and Seedsigner will show an animated QR code to be scanned in Sparrow Wallet (where we are still in the wallet creation).<br>
Scan the QR code Seedsigner is showing in Sparrow Wallet.<br>
The wallet has now been created in Sparrow. Click 'Apply' button to finalize. The wallets settings screen now look like this:<br>
<kbd><img src="img/dicedoc/sparrow_wallet_2.png"></kbd>

We will later use this to verify: (1) fingerprint, (2) zpub (click this button to switch between xpub and zpub!) and (3) addresses on the 'Addresses' tab.
<br><br>

### Verifying with Ian Coleman BIP39 website

Go to https://iancoleman.io/bip39 and check 'Show entropy details' (1):<br>
<kbd><img src="img/dicedoc/coleman_entropy.png"></kbd>

And then make sure to check (1) 'Hex' and (2) '24 Words' as 'Mnemonic Length'.
(Do not use 'dice' format because dice 6 will be replaced by 0.)
Then enter the 99 dices numbers in (3). The corresponding seed words are shown in (4):<br>
<kbd><img src="img/dicedoc/coleman_verify.png"></kbd>

The 24 seed words are the same in Seedsigner and the Ian Coleman tool.
<br>

#### Verification of (1) fingerprint, (2) zpub and (3) generated addresses
1. Fingerprint:<br>
Fingerprint is not shown in the Ian Coleman tool (so cannot be verified here)
1. Zpub:<br>
Scroll down to the 'Derivation Path' section, click on the 'BIP84' tab (1) and find the zpub in (2):
<kbd><img src="img/dicedoc/coleman_zpub.png"></kbd><br>
Compare to zpub in Sparrow:<br>
<kbd><img src="img/dicedoc/sparrow_zpub.png"></kbd>
1. Addresses:<br>
Scroll down to the 'Derived Addresses' section and compare the receive addresses to the ones generated in Sparrow (Addresses tab of the wallet):
<kbd><img src="img/dicedoc/coleman_addresses.png"></kbd>
Check that the receive addresses match.<br>
To verify the change addresses change 'External / Internal' to 1 (1):
<kbd><img src="img/dicedoc/coleman_change_addresses_1.png"></kbd><br>
Compare the change addresses to the ones generated in Sparrow (Addresses tab of the wallet):
<kbd><img src="img/dicedoc/coleman_change_addresses_2.png"></kbd>
Check that the change addresses match.

<br><br>

### Verifying with Seed Tool website

Go to https://bitcoiner.guide/seed/ and click on 'Seed Generation Input' (1):<br>
<kbd><img src="img/dicedoc/seedtool_1.png"></kbd>

Then click on the 'Show the Entropy Section' tab (1):<br>
<kbd><img src="img/dicedoc/seedtool_2.png"></kbd>

Enter the 99 dice numbers in (1), in (2) change back to 'Hex', check that (3) is still '24 Words' and the calculated seed words are shown in (4):
<kbd><img src="img/dicedoc/seedtool_3.png"></kbd>

Seed words shown are the same as in Seedsigner and the Ian Coleman web tool seen before.
<br>

#### Verification of (1) fingerprint, (2) zpub and (3) generated addresses

1. Fingerprint can be seen here (1): <br>
<kbd><img src="img/dicedoc/seedtool_fingerprint.png"></kbd>
1. Zpub:<br>
Scroll down to the 'Derived Addresses' section (1), click on it, make sure that '84' is selected for 'Purpose' (2) and check the zpub at (3):<br>
<kbd><img src="img/dicedoc/seedtool_zpub.png"></kbd><br>
Compare to zpub in Sparrow:<br>
<kbd><img src="img/dicedoc/sparrow_zpub.png"></kbd>
Zpub is the same as shown in Seedsigner, Sparrow and Ian Colemand tool.
1. Addresses:<br>
Scroll down a little bit where the receive addresses are shown and compare to the ones generated in Sparrow:<br>
<kbd><img src="img/dicedoc/seedtool_addresses.png"></kbd>
Check that the receive addresses match.<br>
To verify the change addresses change the 'Receive/Change' dropdown box to '1 (Change)' (1):
<kbd><img src="img/dicedoc/seedtool_change_addresses_1.png"></kbd><br>
Compare the change addresses to the ones generated in Sparrow (Addresses tab of the wallet):
<kbd><img src="img/dicedoc/seedtool_change_addresses_2.png"></kbd>
Check that the change addresses match.
<br><br>

### Verifying with Coldcard

There is nothing specific, the algorithm are completely the same. Coldcard has a verification script in python and all explanations here:
https://coldcard.com/docs/verifying-dice-roll-math
<br><br>

### Epilogue
You can use these methods to do dry runs from time to time to verify that no one has changed the micro sdcard. But do not use the generated 24 words as a valid wallet, they need to be generated alone, only on the seedsigner!
