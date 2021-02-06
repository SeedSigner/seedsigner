import resources

runstate = [0, "", ["", "", ""]]
seedsignerrunning = True

while seedsignerrunning == True:
    if runstate[0] == 0:
        resources.main_menu(runstate)
    if runstate[0] == 1:
        resources.seedgen_menu(runstate)
    if runstate[0] == 2:
        resources.signing_menu(runstate)
    if runstate[0] == 3:
        resources.settings_menu(runstate)
    if runstate[0] == 50:
        resources.iotestscreen(runstate)
    if runstate[0] == 51:
        resources.get_pre_calc_words(runstate)
    if runstate[0] == 52:
        resources.get_final_word(runstate)
    if runstate[0] == 53:
        resources.getseedfromdice(runstate)
    if runstate[0] == 54:
        resources.make_xpub(runstate)
    if runstate[0] == 55:
        resources.sign_psbt(runstate)
    if runstate[0] == 56:
        resources.donate(runstate)
    if runstate[0] == 57:
        resources.version_info(runstate)
    if runstate[0] == 58:
        resources.powering_down_notifier(runstate)
    if runstate[0] == 59:
        resources.gather_23_words(runstate)
    if runstate[0] == 60:
        resources.gather_11_words(runstate)
    if runstate[0] == 61:
        resources.network_menu(runstate)
    if runstate[0] == 62:
        resources.seedselect_menu(runstate)
    if runstate[0] == 63:
        resources.tempsaveseed(runstate)
    print("Back at main and runstate is:")
    print(runstate)
