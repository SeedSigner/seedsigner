import menus
import iotest
import getwords
import getword24
import dice
import xpubmake
import psbtsign

runstate = [0, ""]
seedsignerrunning = True

while seedsignerrunning == True:
    if runstate[0] == 0:
        menus.main_menu(runstate)
    if runstate[0] == 1:
        menus.seedgen_menu(runstate)
    if runstate[0] == 2:
        menus.signing_menu(runstate)
    if runstate[0] == 3:
        menus.settings_menu(runstate)
    if runstate[0] == 50:
        iotest.iotestscreen(runstate)
    if runstate[0] == 51:
        getwords.gather_23_words(runstate)
    if runstate[0] == 52:
        getword24.get_word_24(runstate)
    if runstate[0] == 53:
        dice.getseedfromdice(runstate)
    if runstate[0] == 54:
        xpubmake.make_xpub(runstate)
    if runstate[0] == 55:
        psbtsign.sign_psbt(runstate)
    if runstate[0] == 56:
        menus.donate(runstate)
    if runstate[0] == 57:
        menus.version_info(runstate)